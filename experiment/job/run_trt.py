# -*- coding: utf-8 -*-
"""Path B benchmark driver: TensorRT engines + trtexec + nvidia-smi power sampling.

For every ONNX model and every requested precision the script
  1) builds an engine once:
       trtexec --onnx=<m>.onnx --saveEngine=<m>-<p>.engine --buildOnly [precision flags]
  2) benchmarks it ``--reps`` times:
       trtexec --loadEngine=<engine> --duration=<ms> --warmup=<ms>
     while an nvidia-smi sampler records GPU power (sampling starts a few seconds
     after process launch to skip engine load and warm-up ramp).

Each repetition becomes one CSV row. Latency/p95/throughput come from the trtexec
summary; J/inference = mean power / throughput; EDP = J/inference * mean latency.
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from power import PowerSampler

APPROX_GFLOPS = {
    "mobilenetv2": 0.31,
    "resnet50": 4.1,
    "vit_b_16": 17.6,
}

# name -> (short description, extra trtexec build flags)
PRECISIONS = {
    "tf32": ("FP32 build, TF32 enabled (TensorRT default on A100)", []),
    "fp32": ("FP32 build, TF32 disabled", ["--noTF32"]),
    "fp16": ("FP16 build", ["--fp16"]),
    "int8": ("INT8 build (best effort, random-input calibration)", ["--fp16", "--int8"]),
}

CSV_FIELDS = [
    "model", "backend", "precision", "tag", "rep",
    "flops_approx_g", "mean_lat_ms", "p95_lat_ms", "throughput_qps",
    "mean_power_w", "idle_power_w", "energy_j_per_inf", "energy_net_j_per_inf", "edp",
    "samples", "run_wall_s", "gpu_index", "gpu_name", "driver_version",
    "sm_clock_mhz", "max_sm_clock_mhz", "power_limit_w", "temp_gpu_c", "util_gpu_pct",
]


def run_cmd(cmd, log_path, timeout_s):
    """Run a command, append its output to log_path, return (rc, text) or None on timeout."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace", timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"\n[[TIMEOUT after {timeout_s}s]]\n")
        return None
    text = (proc.stdout or "") + (proc.stderr or "")
    with log_path.open("a", encoding="utf-8") as f:
        f.write("$ " + " ".join(map(str, cmd)) + "\n" + text + "\n")
    return proc.returncode, text


def gpu_env(gpu_index):
    q = ["--query-gpu=name,driver_version,clocks.sm,clocks.max.sm,power.limit,"
         "temperature.gpu,utilization.gpu",
         "--format=csv,noheader,nounits"]
    out = None
    for extra in (["-i", str(gpu_index)] if gpu_index is not None else [], []):
        try:
            r = subprocess.run(["nvidia-smi"] + extra + q,
                               capture_output=True, text=True, timeout=5.0)
            if r.returncode == 0 and r.stdout.strip():
                out = r.stdout.strip().splitlines()[0]
                break
        except Exception:
            continue
    if not out:
        return {"gpu_index": gpu_index, "gpu_name": "", "driver_version": "",
                "sm_clock_mhz": "", "max_sm_clock_mhz": "", "power_limit_w": "",
                "temp_gpu_c": "", "util_gpu_pct": ""}
    p = [x.strip() for x in out.split(",")]
    keys = ["gpu_name", "driver_version", "sm_clock_mhz", "max_sm_clock_mhz",
            "power_limit_w", "temp_gpu_c", "util_gpu_pct"]
    return {"gpu_index": gpu_index,
            **{k: (p[i] if i < len(p) else "") for i, k in enumerate(keys)}}


def parse_trtexec(text):
    """Extract latency/throughput from a trtexec performance summary."""
    res = {}
    m = re.search(r"Throughput:\s*([0-9.eE+]+)\s*qps", text)
    if m:
        res["throughput_qps"] = float(m.group(1))
    # The end-to-end summary line looks like:
    #   Latency: min = 1.23 ms, max = 2.50 ms, mean = 1.40 ms, median = ...,
    #            percentile(90%) = ..., percentile(95%) = ...
    # Prefer the standalone "Latency:" line over "H2D/D2H Latency:" lines.
    lat_line = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("Latency:") and "min =" in s and "mean =" in s:
            lat_line = s
            break
    if lat_line is None:
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("Host Latency:") and "mean =" in s:
                lat_line = s
                break
    if lat_line:
        m = re.search(r"min\s*=\s*([0-9.eE+]+)\s*ms,.*?mean\s*=\s*([0-9.eE+]+)\s*ms",
                      lat_line, flags=re.DOTALL)
        if m:
            res["mean_lat_ms"] = float(m.group(2))
    m = re.search(r"percentile\(95%\)\s*=\s*([0-9.eE+]+)\s*ms", text)
    if m:
        res["p95_lat_ms"] = float(m.group(1))
    m = re.search(r"Total Host Walltime:\s*([0-9.eE+]+)\s*s", text)
    if m:
        res["wall_s"] = float(m.group(1))
    return res


def build_engine(trtexec, onnx_path, engine_path, precision, log_path, timeout_s=2400):
    flags = PRECISIONS[precision][1]
    cmd = [trtexec, f"--onnx={onnx_path}", f"--saveEngine={engine_path}",
           "--buildOnly"] + flags
    ret = run_cmd(cmd, log_path, timeout_s)
    if ret is None:
        return False
    rc, _ = ret
    ok = rc == 0 and engine_path.exists() and engine_path.stat().st_size > 0
    if ok:
        print(f"  [build] {engine_path.name}: OK ({engine_path.stat().st_size/1e6:.1f} MB)")
    else:
        print(f"  [build] {engine_path.name}: FAILED rc={rc} (see {log_path.name})")
    return ok


def measure_once(trtexec, engine_path, log_path, duration_ms, warmup_ms,
                 power_backend, gpu_index, skip_s=3.0):
    cmd = [trtexec, f"--loadEngine={engine_path}",
           f"--duration={duration_ms}", f"--warmup={warmup_ms}"]
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
    time.sleep(skip_s)  # skip engine load + warm-up ramp
    sampler = PowerSampler(power_backend, interval_s=0.1, gpu_index=gpu_index)
    sampler.start()
    t0 = time.time()
    try:
        rc = proc.wait(timeout=(duration_ms / 1000.0) + 180.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        rc = None
    sampler.stop()
    wall_s = time.time() - t0
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    parsed = parse_trtexec(text)
    parsed["rc"] = rc
    parsed["wall_s"] = wall_s
    return parsed, sampler


def write_row(out_csv, row):
    new_file = (not out_csv.exists()) or out_csv.stat().st_size == 0
    with out_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trtexec", required=True)
    ap.add_argument("--models-dir", required=True)
    ap.add_argument("--engines-dir", required=True)
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--log-dir", default="logs")
    ap.add_argument("--precisions", default="tf32,fp32,fp16,int8")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--duration-ms", type=int, default=20000)
    ap.add_argument("--warmup-ms", type=int, default=2000)
    ap.add_argument("--power", default="nvidia-smi")
    ap.add_argument("--gpu-index", type=int, default=None)
    ap.add_argument("--skip-s", type=float, default=3.0)
    args = ap.parse_args()

    trtexec = str(Path(args.trtexec).resolve())
    models_dir = Path(args.models_dir)
    engines_dir = Path(args.engines_dir)
    log_dir = Path(args.log_dir)
    out_csv = Path(args.out)
    engines_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    gpu_index = args.gpu_index
    if gpu_index is None:
        vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
        if vis and vis.lower() != "no_device":
            first = vis.split(",")[0].strip()
            if first.isdigit():
                gpu_index = int(first)
    if gpu_index is None:
        gpu_index = 0

    models = sorted(models_dir.glob("*.onnx"))
    if not models:
        print(f"ERROR: no *.onnx found in {models_dir}")
        return 2

    precs = [p.strip() for p in args.precisions.split(",") if p.strip()]
    precs = [p for p in precs if p in PRECISIONS]
    if not precs:
        print("ERROR: no valid precision in --precisions (use tf32,fp32,fp16,int8)")
        return 2

    env = gpu_env(gpu_index)
    print("gpu:", env.get("gpu_name"), "| index", gpu_index,
          "| driver", env.get("driver_version"),
          "| max sm", env.get("max_sm_clock_mhz"), "MHz",
          "| power limit", env.get("power_limit_w"), "W")

    failures = []
    total = 0
    started = time.time()
    for model_path in models:
        stem = model_path.stem
        flops = APPROX_GFLOPS.get(stem, "")
        for prec in precs:
            desc, flags = PRECISIONS[prec]
            engine_path = engines_dir / f"{stem}-{prec}.engine"
            build_log = log_dir / f"build_{stem}_{prec}.log"
            print(f"== {stem} / {prec}  ({desc}) ==")
            if not build_engine(trtexec, model_path, engine_path, prec, build_log):
                failures.append((stem, prec, "engine build failed", str(build_log)))
                continue
            for rep in range(1, args.reps + 1):
                total += 1
                bench_log = log_dir / f"bench_{stem}_{prec}_rep{rep}.log"
                parsed, sampler = measure_once(
                    trtexec, engine_path, bench_log,
                    args.duration_ms, args.warmup_ms, args.power, gpu_index,
                    skip_s=args.skip_s)
                mean_power = sampler.average_w()
                idle = None
                if mean_power is not None:
                    idle_sampler = PowerSampler(args.power, interval_s=0.1, gpu_index=gpu_index)
                    idle_sampler.start()
                    time.sleep(1.0)
                    idle_sampler.stop()
                    idle = idle_sampler.average_w()
                qps = parsed.get("throughput_qps")
                mean_ms = parsed.get("mean_lat_ms")
                p95_ms = parsed.get("p95_lat_ms")
                energy = (mean_power / qps) if (mean_power and qps) else None
                energy_net = ((mean_power - idle) / qps) if (mean_power and idle is not None and qps) else None
                edp = (energy * mean_ms / 1000.0) if (energy is not None and mean_ms is not None) else None

                row = {
                    "model": stem,
                    "backend": "tensorrt",
                    "precision": prec,
                    "build_flags": " ".join(flags),
                    "tag": f"{stem}-trt-{prec}",
                    "rep": rep,
                    "flops_approx_g": flops,
                    "mean_lat_ms": "" if mean_ms is None else round(mean_ms, 4),
                    "p95_lat_ms": "" if p95_ms is None else round(p95_ms, 4),
                    "throughput_qps": "" if qps is None else round(qps, 2),
                    "mean_power_w": "" if mean_power is None else round(mean_power, 4),
                    "idle_power_w": "" if idle is None else round(idle, 4),
                    "energy_j_per_inf": "" if energy is None else round(energy, 6),
                    "energy_net_j_per_inf": "" if energy_net is None else round(energy_net, 6),
                    "edp": "" if edp is None else round(edp, 9),
                    "samples": len(sampler.samples),
                    "run_wall_s": round(parsed.get("wall_s") or 0.0, 1),
                    **env,
                }
                write_row(out_csv, row)
                ok_lat = mean_ms is not None
                print(f"  rep{rep}: rc={parsed.get('rc')} lat_mean={mean_ms} p95={p95_ms} "
                      f"qps={qps} power={mean_power} J/inf={energy} "
                      f"[{'OK' if ok_lat else 'no latency parsed'}]")
                if not ok_lat:
                    failures.append((stem, prec, f"rep{rep} no latency in summary", str(bench_log)))
                time.sleep(0.5)

    if failures:
        with (log_dir / "failures.txt").open("w", encoding="utf-8") as f:
            for item in failures:
                f.write(" | ".join(map(str, item)) + "\n")
    print(f"\ncompleted {total} measurements in {time.time()-started:.0f}s; "
          f"failures: {len(failures)}")
    for item in failures:
        print("  FAIL:", item)
    return 0 if out_csv.exists() and out_csv.stat().st_size > 0 else 3


if __name__ == "__main__":
    sys.exit(main())
