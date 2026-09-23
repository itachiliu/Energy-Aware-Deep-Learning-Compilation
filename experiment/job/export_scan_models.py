# -*- coding: utf-8 -*-
"""Export dynamic-batch ONNX models for the compiler-decision scan.

Unlike the batch-1 static exports used by the TensorRT path, these models keep
the batch axis dynamic so the same .onnx can be benchmarked at batch 1/16 by
ONNX Runtime. Weights are random (fixed seed): the experiment compares kernel
selection / memory behaviour, not accuracy.
"""
import argparse
from pathlib import Path


TORCHVISION_SPECS = {
    "mobilenetv2": "mobilenet_v2",
    "resnet50": "resnet50",
    "vit_b_16": "vit_b_16",
    "resnet18": "resnet18",
    "mobilenetv3_large": "mobilenet_v3_large",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="models_scan")
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--extra", action="store_true",
                    help="also export resnet18 and mobilenetv3_large")
    ap.add_argument("--only", default=None,
                    choices=sorted(TORCHVISION_SPECS),
                    help="export only one model (useful for re-running a missing one)")
    ap.add_argument("--force-mha-replace", action="store_true",
                    help="always use the hand-written attention replacement for ViT "
                         "(the old workaround for torch 2.0.x; keep as a fallback path)")
    args = ap.parse_args()

    try:
        import torch
        import torch.nn as nn
        import torchvision.models as M
    except Exception as exc:
        print("need torch/torchvision:", exc)
        return 1

    torch.manual_seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    names = ["mobilenetv2", "resnet50", "vit_b_16"]
    if args.only:
        names = [args.only]
    elif args.extra:
        names += ["resnet18", "mobilenetv3_large"]

    class SimpleAttention(nn.Module):
        """Drop-in replacement for nn.MultiheadAttention used by ViT export.

        torch 2.0.1's ONNX exporter cannot trace aten::unflatten inside
        nn.MultiheadAttention at opset 17. The replacement keeps the exact
        q/k/v + softmax + projection data flow using reshape/permute only, so
        the exported graph has the same kernel mix and memory behaviour.
        Weights are random (fixed seed); accuracy is irrelevant here.
        """

        def __init__(self, embed_dim, num_heads):
            super().__init__()
            self.num_heads = num_heads
            self.head_dim = embed_dim // num_heads
            self.qkv = nn.Linear(embed_dim, 3 * embed_dim)
            self.proj = nn.Linear(embed_dim, embed_dim)

        def forward(self, x, *args, **kwargs):
            B, N, E = x.shape
            qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim)
            qkv = qkv.permute(2, 0, 3, 1, 4)
            q, k, v = qkv[0], qkv[1], qkv[2]
            att = (q @ k.transpose(-2, -1)) * (self.head_dim ** -0.5)
            att = torch.softmax(att, dim=-1)
            out = (att @ v).transpose(1, 2).reshape(B, N, E)
            return self.proj(out), None

    def replace_mha(model):
        """Replace every nn.MultiheadAttention in-place (any attribute name)."""
        for name, module in list(model.named_modules()):
            if isinstance(module, nn.MultiheadAttention):
                parent = model
                parts = name.split(".")
                for p in parts[:-1]:
                    parent = getattr(parent, p)
                setattr(parent, parts[-1],
                        SimpleAttention(module.embed_dim, module.num_heads))
                print(f"  replaced MHA at {name}")
        return model

    def export_onnx(model, path, size):
        """Export one model; returns True on success."""
        dummy = torch.zeros(1, 3, size, size)
        try:
            torch.onnx.export(
                model, dummy, str(path),
                input_names=["input"], output_names=["output"],
                dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
                opset_version=args.opset, do_constant_folding=True,
                dynamo=False,
            )
            return True
        except TypeError:
            # `dynamo` kwarg unavailable in this torch build.
            pass
        except Exception as exc:
            print(f"  legacy exporter failed: {type(exc).__name__}: {str(exc)[:160]}")
            return False
        try:
            torch.onnx.export(
                model, dummy, str(path),
                input_names=["input"], output_names=["output"],
                dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
                opset_version=args.opset, do_constant_folding=True,
            )
            return True
        except Exception as exc:
            print(f"  default exporter failed: {type(exc).__name__}: {str(exc)[:160]}")
            return False

    for name in names:
        fn = getattr(M, TORCHVISION_SPECS[name])
        path = out / f"{name}.onnx"
        print(f"exporting {name} -> {path} (opset {args.opset}, dynamic batch)")

        if name == "vit_b_16" and not args.force_mha_replace:
            # Preferred: the real torchvision ViT. Newer torch (>=2.1) traces
            # aten::unflatten fine, so the hand-written attention no longer has
            # to stand in for it.
            model = fn(weights=None).eval()
            if export_onnx(model, path, args.size):
                print(f"  saved {path} ({path.stat().st_size / 1e6:.1f} MB) "
                      f"[real ViT-B/16]")
                continue
            print("  real ViT export failed; falling back to attention replacement "
                  "(note this in the write-up)")
            model = replace_mha(fn(weights=None).eval())
        else:
            model = fn(weights=None).eval()
            if name == "vit_b_16":
                model = replace_mha(model)

        if not export_onnx(model, path, args.size):
            raise SystemExit(f"ERROR: export failed for {name}")
        tag = " [attention replacement]" if name == "vit_b_16" else ""
        print(f"  saved {path} ({path.stat().st_size / 1e6:.1f} MB){tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
