# -*- coding: utf-8 -*-
"""Export MobileNetV2 / ResNet-50 / ViT-B/16 to ONNX for the TensorRT mini-experiment.

Design notes for the ARM64 A100 platform (Path B):
- opset 13/17 targets TensorRT 8.5 ONNX-parser compatibility; torch >= 2.14's new
  dynamo exporter cannot go below 18, so we prefer the legacy exporter (dynamo=False)
  when available and verify the resulting opset afterwards.
- Batch is fixed to 1 (static shape), so trtexec can build engines without --shapes.
- Weights are random by default (fixed seed): the experiment measures energy/latency of
  compiled kernels, which depend on op mix, tensor shapes and memory footprint, not on
  numeric accuracy. ImageNet-pretrained weights can be enabled with --pretrained
  (requires network access for the weight download).
"""
import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="models")
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--opset", type=int, default=13)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pretrained", action="store_true",
                    help="use ImageNet weights (downloads); default is random init")
    args = ap.parse_args()

    try:
        import torch
        import torchvision.models as M
    except Exception as exc:  # pragma: no cover
        print("need torch/torchvision (CPU wheels are enough):", exc)
        return 1

    torch.manual_seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        import onnx  # only used for the opset check below
    except Exception:
        onnx = None

    specs = [
        ("mobilenetv2", M.mobilenet_v2, M.MobileNet_V2_Weights.IMAGENET1K_V1),
        ("resnet50", M.resnet50, M.ResNet50_Weights.IMAGENET1K_V1),
        ("vit_b_16", M.vit_b_16, M.ViT_B_16_Weights.IMAGENET1K_V1),
    ]
    for name, ctor, wcls in specs:
        weights = wcls.IMAGENET1K_V1 if args.pretrained else None
        model = ctor(weights=weights).eval()
        dummy = torch.zeros(1, 3, args.size, args.size)
        path = out / f"{name}.onnx"
        print(f"exporting {name} -> {path} (opset {args.opset}, size {args.size})")
        try:
            # Legacy (TorchScript) exporter: honors the requested opset directly.
            torch.onnx.export(
                model, dummy, str(path),
                input_names=["input"], output_names=["output"],
                opset_version=args.opset, do_constant_folding=True,
                dynamo=False,
            )
        except TypeError:
            # dynamo kwarg unavailable in this torch build -> default exporter.
            torch.onnx.export(
                model, dummy, str(path),
                input_names=["input"], output_names=["output"],
                opset_version=args.opset, do_constant_folding=True,
            )
        actual_opset = None
        if onnx is not None:
            try:
                m = onnx.load(str(path))
                actual_opset = m.opset_import[0].version if m.opset_import else None
            except Exception:
                pass
        if actual_opset and actual_opset > 17:
            print(f"  WARN: exported opset={actual_opset} > 17; "
                  "TensorRT 8.5 may reject it (see cluster build log)")
        data_size = sum(
            p.stat().st_size for p in out.glob(f"{name}.onnx*")
            if p.is_file()
        )
        print(f"  saved {path} (total {data_size / 1e6:.1f} MB incl. external data, "
              f"opset={actual_opset})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
