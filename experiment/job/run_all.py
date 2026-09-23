# -*- coding: utf-8 -*-
"""Multi-backend benchmark orchestrator (Level 1 + Level 2).

Runs whatever is available on the node, in this order:
  1) TensorRT standalone (trtexec):        tf32 / fp32(noTF32) / fp16 / int8
  2) ONNX Runtime CUDA EP:                 fp32
  3) ONNX Runtime TensorRT EP:             fp32 / fp16
  4) PyTorch eager:                        fp32 / fp16
  5) PyTorch torch.compile (Inductor):     fp32 / fp16

Each config is measured in --reps independent timed windows and every
repetition becomes one CSV row (shared schema).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

MODELS_DIR = None
APPROX_GFLOPS = {"mobilenetv2": 0.31, "resnet50": 4.1, "vit_b_16": 17.6}


def has_ort():
    try:
        import onnxruntime  # noqa
        return True
    except Exception:
        return False


def ort_providers():
    try:
        import onnxruntime as ort
        return set(ort.get_available_providers())
    except Exception:
        return set()


def has_torch_cuda():
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def run(cmd, log_path, timeout_s):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"\n[[TIMEOUT after {timeout_s}s]]\n")
        return False
    with log_path.open("a", encoding="utf-8") as f:
        f.write("$ " + " ".join(map(str, cmd)) + "\n")
        f.write((r.stdout or "") + (r.stderr or "") + "\n")
    if r.returncode != 0:
        print(f"  FAILED rc={r.returncode}: {cmd[-6:]}")
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--trtexec", default="")
    ap.add_argument("--models-dir", required=True)
    ap.add_argument("--engines-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--duration-ms", type=int, default=20000)
    ap.add_argument("--duration-s", type=float, default=20.0)
    args = ap.parse_args()

    py = args.python
    script_dir = Path(__file__).resolve().parent
    models = sorted(Path(args.models_dir).glob("*.onnx"))
    failures = []

    # 1) TensorRT standalone
    if args.trtexec and Path(args.trtexec).exists() and models:
        print("== backend: tensorrt (trtexec) ==")
        cmd = [py, str(script_dir / "run_trt.py"),
               "--trtexec", args.trtexec,
               "--models-dir", args.models_dir,
               "--engines-dir", args.engines_dir,
               "--out", args.out,
               "--log-dir", args.log_dir,
               "--precisions", "tf32,fp32,fp16,int8",
               "--reps", str(args.reps),
               "--duration-ms", str(args.duration_ms)]
        if not run(cmd, Path(args.log_dir) / "run_trt.log", timeout_s=7200):
            failures.append(("tensorrt", "matrix", ""))

    # 2-3) ONNX Runtime
    if has_ort() and models:
        provs = ort_providers()
        print("== backend: onnxruntime ==")
        print("   providers:", sorted(provs))
        configs = []
        if "CUDAExecutionProvider" in provs:
            configs.append(("cuda", "fp32", "ort-cuda"))
        if "TensorrtExecutionProvider" in provs:
            configs += [("tensorrt", "fp32", "ort-trt"),
                        ("tensorrt", "fp16", "ort-trt")]
        for m in models:
            for ep, dtype, backend in configs:
                tag = f"{m.stem}-{backend}-{dtype}"
                log = Path(args.log_dir) / f"ort_{m.stem}_{ep}_{dtype}.log"
                print(f"[run] {tag} reps={args.reps}")
                cmd = [py, str(script_dir / "measure_onnx.py"),
                       "--model", str(m), "--ep", ep, "--dtype", dtype,
                       "--tag", tag, "--backend", backend,
                       "--reps", str(args.reps), "--duration-s", str(args.duration_s),
                       "--out", args.out]
                fl = APPROX_GFLOPS.get(m.stem)
                if fl:
                    cmd += ["--flops", str(fl)]
                if not run(cmd, log, timeout_s=3600):
                    failures.append((backend, m.stem, dtype))

    # 4-5) PyTorch eager / torch.compile
    if has_torch_cuda():
        print("== backend: pytorch ==")
        torch_models = ["mobilenetv2", "resnet50", "vit_b_16"]
        for name in torch_models:
            for mode, dtype in (("eager", "fp32"), ("eager", "fp16"),
                                ("compile", "fp32"), ("compile", "fp16")):
                backend = "torch-eager" if mode == "eager" else "torch-compile"
                tag = f"{name}-{backend}-{dtype}"
                log = Path(args.log_dir) / f"torch_{name}_{mode}_{dtype}.log"
                print(f"[run] {tag} reps={args.reps}")
                cmd = [py, str(script_dir / "measure_torch.py"),
                       "--torch-name", name, "--mode", mode, "--dtype", dtype,
                       "--tag", tag, "--reps", str(args.reps),
                       "--duration-s", str(args.duration_s), "--out", args.out]
                if not run(cmd, log, timeout_s=7200):
                    failures.append((backend, name, dtype))

    if failures:
        with (Path(args.log_dir) / "failures.txt").open("w", encoding="utf-8") as f:
            for item in failures:
                f.write(" | ".join(map(str, item)) + "\n")
    if not os.path.exists(args.out) or os.path.getsize(args.out) == 0:
        print("ERROR: no results produced")
        return 3
    print(f"run_all done; failures: {len(failures)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
