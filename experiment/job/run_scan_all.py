# -*- coding: utf-8 -*-
"""Compiler-decision scan orchestrator.

Matrix (defaults; override via env or CLI):
  - ORT CUDA EP fp32: model x graph-opt-level{0,1,2,99} x batch{1,16}
  - PyTorch eager:    model x precision{fp32,fp16} x batch{1,16}

Every config is measured in --reps steady windows; each repetition is one CSV
row in results_scan.csv (superset of the mini-experiment schema).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

APPROX_GFLOPS = {
    "mobilenetv2": 0.31, "resnet50": 4.1, "vit_b_16": 17.6,
    "resnet18": 1.8, "mobilenetv3_large": 0.44,
}


def has_ort_cuda():
    try:
        import onnxruntime as ort
        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


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
        print(f"  FAILED rc={r.returncode}: {cmd[-8:]}")
        return False
    return True


def parse_csv_list(raw):
    return [x.strip() for x in raw.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--models-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--duration-s", type=float, default=20.0)
    ap.add_argument("--batches", default="1,16")
    ap.add_argument("--graph-opts", default="0,1,2,99")
    ap.add_argument("--extra-models", action="store_true")
    ap.add_argument("--models", default=None,
                    help="comma-separated subset of models to measure, e.g. "
                         "resnet18,mobilenetv3_large; overrides --extra-models. "
                         "Use it to extend an existing matrix without redoing it.")
    ap.add_argument("--with-compile", action="store_true",
                    help="also benchmark torch.compile (Inductor); needs a "
                         "torch build with Inductor support")
    ap.add_argument("--skip-ort", action="store_true",
                    help="skip the ONNX Runtime stage (e.g. while its CUDA EP "
                         "is not yet working) and measure the torch backends only")
    ap.add_argument("--compile-mode", default="default",
                    choices=["default", "reduce-overhead", "max-autotune"])
    args = ap.parse_args()

    py = args.python
    script_dir = Path(__file__).resolve().parent
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    failures = []

    if args.models:
        base_models = [m.strip() for m in args.models.split(",") if m.strip()]
        print("model subset: {}".format(", ".join(base_models)))
    else:
        base_models = ["mobilenetv2", "resnet50", "vit_b_16"]
        if args.extra_models:
            base_models += ["resnet18", "mobilenetv3_large"]

    onnx_models = {}
    models_dir = Path(args.models_dir)
    for name in base_models:
        p = models_dir / f"{name}.onnx"
        if p.exists():
            onnx_models[name] = p

    for name in base_models:
        if name not in onnx_models:
            failures.append(("onnx-missing", name, "no .onnx file in models dir"))

    batches = [int(x) for x in parse_csv_list(args.batches)]
    graph_opts = [int(x) for x in parse_csv_list(args.graph_opts)]

    # 1) ORT CUDA EP fp32: graph optimization level x batch
    if args.skip_ort:
        print("skip-ort set; not running the ONNX Runtime stage")
    elif has_ort_cuda():
        print("== backend: onnxruntime (CUDA EP, fp32) ==")
        for name, path in onnx_models.items():
            for level in graph_opts:
                for batch in batches:
                    tag = f"{name}-ort-fp32-opt{level}-b{batch}"
                    log = log_dir / f"ort_{tag}.log"
                    print(f"[run] {tag} reps={args.reps}")
                    cmd = [py, str(script_dir / "measure_ort_scan.py"),
                           "--model", str(path), "--batch", str(batch),
                           "--graph-opt-level", str(level), "--tag", tag,
                           "--reps", str(args.reps),
                           "--duration-s", str(args.duration_s),
                           "--out", args.out]
                    fl = APPROX_GFLOPS.get(name)
                    if fl:
                        cmd += ["--flops", str(fl)]
                    if not run(cmd, log, timeout_s=3600):
                        failures.append(("ort-cuda", name, f"opt{level}-b{batch}"))
    else:
        print("WARN: ORT CUDA EP unavailable; skipping ORT scan")

    # 2) PyTorch eager fp32/fp16 x batch
    if has_torch_cuda():
        print("== backend: pytorch eager ==")
        for name in base_models:
            for dtype in ("fp32", "fp16"):
                for batch in batches:
                    tag = f"{name}-torch-eager-{dtype}-b{batch}"
                    log = log_dir / f"torch_{tag}.log"
                    print(f"[run] {tag} reps={args.reps}")
                    cmd = [py, str(script_dir / "measure_torch_scan.py"),
                           "--torch-name", name, "--dtype", dtype,
                           "--batch", str(batch), "--tag", tag,
                           "--reps", str(args.reps),
                           "--duration-s", str(args.duration_s),
                           "--out", args.out]
                    if not run(cmd, log, timeout_s=3600):
                        failures.append(("torch-eager", name, f"{dtype}-b{batch}"))
    else:
        print("WARN: torch CUDA unavailable; skipping torch scan")

    # 3) PyTorch 2.x torch.compile (Inductor) fp32/fp16 x batch
    if args.with_compile:
        if has_torch_cuda():
            print("== backend: torch.compile (Inductor) ==")
            for name in base_models:
                for dtype in ("fp32", "fp16"):
                    for batch in batches:
                        tag = f"{name}-torch-compile-{dtype}-b{batch}"
                        log = log_dir / f"torch_{tag}.log"
                        print(f"[run] {tag} reps={args.reps}")
                        cmd = [py, str(script_dir / "measure_torch_compile.py"),
                               "--torch-name", name, "--dtype", dtype,
                               "--batch", str(batch), "--tag", tag,
                               "--compile-mode", args.compile_mode,
                               "--reps", str(args.reps),
                               "--duration-s", str(args.duration_s),
                               "--out", args.out]
                        if not run(cmd, log, timeout_s=3600):
                            failures.append(("torch-compile", name, f"{dtype}-b{batch}"))
        else:
            print("WARN: torch CUDA unavailable; skipping torch.compile scan")

    if failures:
        with (log_dir / "failures.txt").open("w", encoding="utf-8") as f:
            for item in failures:
                f.write(" | ".join(map(str, item)) + "\n")
    if not os.path.exists(args.out) or os.path.getsize(args.out) == 0:
        print("ERROR: no results produced")
        return 3
    print(f"run_scan_all done; failures: {len(failures)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
