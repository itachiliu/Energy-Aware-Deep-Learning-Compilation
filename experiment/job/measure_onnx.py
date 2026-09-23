# -*- coding: utf-8 -*-
"""Single-config ONNX Runtime measurer (CUDA EP / TensorRT EP) with nvidia-smi power.

Writes one row into results.csv using the shared schema of the mini-experiment:
  model, backend, precision, tag, rep, flops_approx_g, mean_lat_ms, p95_lat_ms,
  throughput_qps, mean_power_w, idle_power_w, energy_j_per_inf,
  energy_net_j_per_inf, edp, samples, run_wall_s, gpu_*
"""
import argparse
import csv
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

from power import PowerSampler

CSV_FIELDS = [
    "model", "backend", "precision", "tag", "rep", "flops_approx_g",
    "mean_lat_ms", "p95_lat_ms", "throughput_qps", "mean_power_w",
    "idle_power_w", "energy_j_per_inf", "energy_net_j_per_inf", "edp",
    "samples", "run_wall_s", "gpu_index", "gpu_name", "driver_version",
    "sm_clock_mhz", "max_sm_clock_mhz", "power_limit_w", "temp_gpu_c",
    "util_gpu_pct",
]


def gpu_env(gpu_index):
    q = ["--query-gpu=name,driver_version,clocks.sm,clocks.max.sm,power.limit,"
         "temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"]
    for extra in (["-i", str(gpu_index)] if gpu_index is not None else [], []):
        try:
            r = subprocess.run(["nvidia-smi"] + extra + q,
                               capture_output=True, text=True, timeout=5.0)
            if r.returncode == 0 and r.stdout.strip():
                p = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
                keys = ["gpu_name", "driver_version", "sm_clock_mhz",
                        "max_sm_clock_mhz", "power_limit_w", "temp_gpu_c",
                        "util_gpu_pct"]
                return {"gpu_index": gpu_index,
                        **{k: (p[i] if i < len(p) else "") for i, k in enumerate(keys)}}
        except Exception:
            continue
    return {"gpu_index": gpu_index, "gpu_name": "", "driver_version": "",
            "sm_clock_mhz": "", "max_sm_clock_mhz": "", "power_limit_w": "",
            "temp_gpu_c": "", "util_gpu_pct": ""}


def make_session(model_path, ep, dtype, gpu_index):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.log_severity_level = 3
    providers = []
    if ep == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif ep == "tensorrt":
        providers = [
            ("TensorrtExecutionProvider", {
                "trt_fp16_enable": dtype == "fp16",
                "device_id": int(gpu_index) if gpu_index is not None else 0,
            }),
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
    else:
        sys.exit(f"unknown ep: {ep}")
    return ort.InferenceSession(str(model_path), sess_options=so, providers=providers)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--ep", choices=["cuda", "tensorrt"], required=True)
    ap.add_argument("--dtype", choices=["fp32", "fp16"], required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--backend", default="ort")
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--flops", type=float, default=None)
    ap.add_argument("--duration-s", type=float, default=20.0)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--gpu-index", type=int, default=None)
    args = ap.parse_args()

    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    gpu_index = args.gpu_index
    if gpu_index is None and vis and vis.lower() != "no_device" and vis.split(",")[0].isdigit():
        gpu_index = int(vis.split(",")[0])
    if gpu_index is None:
        gpu_index = 0

    import numpy as np
    sess = make_session(args.model, args.ep, args.dtype, gpu_index)
    inp = sess.get_inputs()[0]
    shape = [1 if d in (None, "batch", "dynamic_axes") else int(d) for d in inp.shape]
    feed = {inp.name: np.zeros(shape, dtype=np.float32)}

    # cold idle baseline BEFORE any measured work (let clocks decay first)
    time.sleep(2.0)
    idle_s = PowerSampler("nvidia-smi", interval_s=0.1, gpu_index=gpu_index)
    idle_s.start(); time.sleep(1.5); idle_s.stop()
    idle = idle_s.average_w()

    # warm up once; each repetition runs a fresh timed window
    for _ in range(args.warmup):
        sess.run(None, feed)

    reps = args.reps if args.reps else 1
    for rep in range(1, reps + 1):
        sampler = PowerSampler("nvidia-smi", interval_s=0.1, gpu_index=gpu_index)
        sampler.start()
        t0 = time.perf_counter()
        lat = []
        while time.perf_counter() - t0 < args.duration_s:
            s = time.perf_counter()
            sess.run(None, feed)
            lat.append((time.perf_counter() - s) * 1000.0)
        wall = time.perf_counter() - t0
        sampler.stop()

        mean_power = sampler.average_w()
        mean_ms = statistics.mean(lat)
        p95_ms = sorted(lat)[max(0, int(0.95 * len(lat)) - 1)]
        qps = len(lat) / wall if wall > 0 else None
        energy = (mean_power * mean_ms / 1000.0) if mean_power is not None else None
        energy_net = ((mean_power - idle) * mean_ms / 1000.0) if (mean_power is not None and idle is not None) else None
        edp = (energy * mean_ms / 1000.0) if energy is not None else None

        row = {
            "model": Path(args.model).stem,
            "backend": args.backend,
            "precision": args.dtype,
            "tag": args.tag,
            "rep": rep,
            "flops_approx_g": args.flops if args.flops is not None else "",
            "mean_lat_ms": round(mean_ms, 4),
            "p95_lat_ms": round(p95_ms, 4),
            "throughput_qps": "" if qps is None else round(qps, 2),
            "mean_power_w": "" if mean_power is None else round(mean_power, 4),
            "idle_power_w": "" if idle is None else round(idle, 4),
            "energy_j_per_inf": "" if energy is None else round(energy, 6),
            "energy_net_j_per_inf": "" if energy_net is None else round(energy_net, 6),
            "edp": "" if edp is None else round(edp, 9),
            "samples": len(sampler.samples),
            "run_wall_s": round(wall, 1),
            **gpu_env(gpu_index),
        }
        new_file = (not os.path.exists(args.out)) or os.path.getsize(args.out) == 0
        with open(args.out, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if new_file:
                w.writeheader()
            w.writerow({k: row.get(k, "") for k in CSV_FIELDS})
        print(f"[ok] {args.tag} rep{rep}: lat={mean_ms:.3f}ms p95={p95_ms:.3f} "
              f"power={mean_power} J/inf={energy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
