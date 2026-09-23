# -*- coding: utf-8 -*-
"""Run Nsight Compute on selected configs and print DRAM-bytes attribution."""
import argparse
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

METRICS = "dram__bytes_read.sum,dram__bytes_write.sum"


def parse_ncu_csv(text):
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return None
    # find header line containing the metric columns
    hdr_idx = None
    for i, row in enumerate(rows):
        if row and "dram__bytes_read.sum" in row:
            hdr_idx = i
            break
    if hdr_idx is None:
        return None
    header = rows[hdr_idx]
    ri = header.index("dram__bytes_read.sum")
    wi = header.index("dram__bytes_write.sum")
    total_r = total_w = 0.0
    kernels = 0
    for row in rows[hdr_idx + 1:]:
        if len(row) <= max(ri, wi) or not row[ri].strip():
            continue
        try:
            total_r += float(row[ri])
            total_w += float(row[wi])
            kernels += 1
        except ValueError:
            continue
    return total_r, total_w, kernels


def run_one(ncu, py, spec, log_dir):
    cmd = [ncu, "--metrics", METRICS, "--csv", "--target-processes", "all",
           py, str(Path(__file__).parent / "ncu_prof_harness.py")]
    if spec["mode"] == "onnx":
        cmd += ["--mode", "onnx", "--model", spec["model"]]
    else:
        cmd += ["--mode", "torch", "--torch-name", spec["torch_name"],
                "--dtype", spec["dtype"]]
    log_path = Path(log_dir) / f"ncu_{spec['tag']}.log"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=5400, errors="replace")
    except subprocess.TimeoutExpired:
        print(f"{spec['tag']}: TIMEOUT")
        return None
    text = (r.stdout or "") + (r.stderr or "")
    log_path.write_text(text, encoding="utf-8")
    if r.returncode != 0:
        print(f"{spec['tag']}: ncu rc={r.returncode} (see {log_path.name})")
        return None
    parsed = parse_ncu_csv(text)
    return parsed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", required=True)
    ap.add_argument("--models-dir", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--ncu", default="ncu")
    args = ap.parse_args()

    specs = []
    for name in ("mobilenetv2", "resnet50", "vit_b_16"):
        specs.append({"mode": "onnx", "tag": f"{name}-ort-fp32",
                      "model": str(Path(args.models_dir) / f"{name}.onnx")})
    specs += [
        {"mode": "torch", "tag": "vit_b_16-torch-fp32",
         "torch_name": "vit_b_16", "dtype": "fp32"},
        {"mode": "torch", "tag": "vit_b_16-torch-fp16",
         "torch_name": "vit_b_16", "dtype": "fp16"},
    ]

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    print("tag,read_bytes_per_inf,write_bytes_per_inf,bytes_per_inf,"
          "kernels_profiled")
    for spec in specs:
        parsed = run_one(args.ncu, args.python, spec, args.log_dir)
        if parsed is None:
            print(f"{spec['tag']},FAILED")
            continue
        total_r, total_w, kernels = parsed
        per_r = total_r / 3.0
        per_w = total_w / 3.0
        print(f"{spec['tag']},{per_r:.0f},{per_w:.0f},"
              f"{per_r + per_w:.0f},{kernels}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
