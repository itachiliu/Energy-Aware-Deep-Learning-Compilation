# -*- coding: utf-8 -*-
"""ORT CUDA EP measurement with batch, intra-op threads and graph-opt levels.

Keeps the mini-experiment power protocol (cold idle baseline, warm-up, N steady
windows, nvidia-smi power sampling) and extends the result schema with
batch / graph_opt_level / intra_op_threads. One "inference unit" is one batch
call; the aggregated summary can rescale to per-image numbers when needed.
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
    "model", "backend", "precision", "tag", "batch", "graph_opt_level",
    "intra_op_threads", "rep", "flops_approx_g",
    "mean_lat_ms", "p95_lat_ms", "throughput_qps", "mean_power_w",
    "idle_power_w", "energy_j_per_inf", "energy_net_j_per_inf", "edp",
    "static_share_pct", "samples", "run_wall_s", "gpu_index", "gpu_name",
    "driver_version", "sm_clock_mhz", "max_sm_clock_mhz", "power_limit_w",
    "temp_gpu_c", "util_gpu_pct",
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


def make_session(model_path, gpu_index, graph_opt_level, intra_op):
    import onnxruntime as ort
    # Pull in the CUDA/cuDNN shared libraries that shipped as nvidia-* wheels
    # next to torch. Without this ORT cannot initialise the CUDA EP and, worse,
    # does it silently: the session quietly runs on the CPU provider instead.
    if hasattr(ort, "preload_dlls"):
        try:
            ort.preload_dlls()
        except Exception as exc:
            print(f"[ort] preload_dlls warning: {exc}")
    so = ort.SessionOptions()
    so.log_severity_level = 3
    levels = {
        0: ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
        1: ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
        2: ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
        99: ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
    }
    so.graph_optimization_level = levels.get(graph_opt_level, ort.GraphOptimizationLevel.ORT_ENABLE_ALL)
    if intra_op and intra_op > 0:
        so.intra_op_num_threads = intra_op
    providers = [
        ("CUDAExecutionProvider", {"device_id": int(gpu_index) if gpu_index is not None else 0}),
        "CPUExecutionProvider",
    ]
    return ort.InferenceSession(str(model_path), sess_options=so, providers=providers)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--graph-opt-level", type=int, default=99,
                    help="0=disable 1=basic 2=extended 99=all")
    ap.add_argument("--intra-op", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--dtype", choices=["fp32"], default="fp32")
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--flops", type=float, default=None)
    ap.add_argument("--duration-s", type=float, default=20.0)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--warmup-max-s", type=float, default=90.0,
                    help="cap the warm-up phase by wall time (0 disables the cap)")
    ap.add_argument("--out", default="results_scan.csv")
    ap.add_argument("--gpu-index", type=int, default=None)
    args = ap.parse_args()

    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    gpu_index = args.gpu_index
    if gpu_index is None and vis and vis.lower() != "no_device" and vis.split(",")[0].isdigit():
        gpu_index = int(vis.split(",")[0])
    if gpu_index is None:
        gpu_index = 0

    import numpy as np
    sess = make_session(args.model, gpu_index, args.graph_opt_level, args.intra_op)
    active = sess.get_providers()
    print(f"[ort] providers in use: {active}", flush=True)
    if "CUDAExecutionProvider" not in active:
        print("ERROR: ONNX Runtime fell back to the CPU provider; the CUDA EP did not",
              file=sys.stderr)
        print("       initialise. Fix the runtime before measuring -- CPU rows look",
              file=sys.stderr)
        print("       like valid data (idle-level power, huge latency) but are useless.",
              file=sys.stderr)
        print("       Check cuDNN/CUDA versions and LD_LIBRARY_PATH, then rerun.",
              file=sys.stderr)
        # Retry once at verbose log level: the loader error it prints names the
        # library that could not be resolved.
        try:
            import onnxruntime as _ort
            so = _ort.SessionOptions()
            so.log_severity_level = 1
            _ort.InferenceSession(str(args.model), sess_options=so,
                                  providers=["CUDAExecutionProvider"])
        except Exception as exc:
            print(f"[ort] verbose loader attempt: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
        return 3
    inp = sess.get_inputs()[0]
    shape = [args.batch if d in (None, "batch", "dynamic_axes") else int(d)
             for d in inp.shape]
    feed = {inp.name: np.zeros(shape, dtype=np.float32)}
    stem = Path(args.model).stem
    tag = args.tag or f"{stem}-ort-fp32-opt{args.graph_opt_level}-b{args.batch}"

    time.sleep(2.0)
    idle_s = PowerSampler("nvidia-smi", interval_s=0.1, gpu_index=gpu_index)
    idle_s.start(); time.sleep(1.5); idle_s.stop()
    idle = idle_s.average_w()

    # Warm-up is capped by wall time: if the backend is unexpectedly slow, do not
    # let the warm-up phase eat the job's whole time budget.
    t_warm = time.perf_counter()
    done = 0
    for _ in range(args.warmup):
        sess.run(None, feed)
        done += 1
        if args.warmup_max_s > 0 and (time.perf_counter() - t_warm) > args.warmup_max_s:
            break
    if done < args.warmup:
        print(f"[warn] warm-up capped at {done}/{args.warmup} iterations "
              f"({time.perf_counter() - t_warm:.1f}s)")

    for rep in range(1, args.reps + 1):
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
        static_pct = (idle / mean_power * 100.0) if (idle and mean_power) else ""

        row = {
            "model": stem,
            "backend": "ort-cuda",
            "precision": args.dtype,
            "tag": tag,
            "batch": args.batch,
            "graph_opt_level": args.graph_opt_level,
            "intra_op_threads": args.intra_op,
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
            "static_share_pct": "" if static_pct == "" else round(static_pct, 1),
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
        print(f"[ok] {tag} rep{rep}: lat={mean_ms:.3f}ms p95={p95_ms:.3f} "
              f"power={mean_power} J/inf={energy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
