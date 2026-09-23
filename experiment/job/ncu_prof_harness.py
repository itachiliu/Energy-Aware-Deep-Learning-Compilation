# -*- coding: utf-8 -*-
"""Minimal inference harness to be profiled by Nsight Compute.

Usage (profiled): ncu --metrics ... --csv python ncu_prof_harness.py --mode ...
The harness warms up, then runs --runs inferences and prints NCU_DONE.
"""
import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["onnx", "torch"], required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--torch-name", default="vit_b_16")
    ap.add_argument("--dtype", default="fp32", choices=["fp32", "fp16"])
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    if args.mode == "onnx":
        import numpy as np
        import onnxruntime as ort
        sess = ort.InferenceSession(
            args.model,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        shape = [1 if d in (None, "batch", "dynamic_axes") else int(d)
                 for d in inp.shape]
        feed = {inp.name: np.zeros(shape, dtype=np.float32)}
        for _ in range(args.warmup):
            sess.run(None, feed)
        for _ in range(args.runs):
            sess.run(None, feed)
    else:
        import torch
        import torchvision.models as M
        torch.manual_seed(0)
        specs = {"mobilenetv2": M.mobilenet_v2, "resnet50": M.resnet50,
                 "vit_b_16": M.vit_b_16}
        model = specs[args.torch_name](weights=None).eval().cuda()
        if args.dtype == "fp16":
            model = model.half()
        x = torch.zeros(1, 3, 224, 224).cuda()
        if args.dtype == "fp16":
            x = x.half()
        with torch.no_grad():
            for _ in range(args.warmup):
                model(x)
            torch.cuda.synchronize()
            for _ in range(args.runs):
                model(x)
            torch.cuda.synchronize()
    print("NCU_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
