# -*- coding: utf-8 -*-
"""FLOPs-versus-energy audit across the whole measured model set.

For each model this reports energy per inference under a fixed stack
(ORT-CUDA FP32, graph-opt "extended") and the implied energy per GFLOP, plus
the batch-16 per-image figure. Then it ranks models by FLOPs and by energy so
the inversion is explicit.

    python job/flops_vs_energy.py merged_results.csv
"""
import argparse
import csv
import statistics
import sys

GFLOPS = {
    "mobilenetv2": 0.31, "mobilenetv3_large": 0.44, "resnet18": 1.8,
    "resnet50": 4.1, "vit_b_16": 17.6,
}


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mean_j(rows, model, batch, backend="ort-cuda", prec="fp32", opt="2"):
    vals = []
    for r in rows:
        if (r["model"] == model and r["backend"] == backend
                and r["precision"] == prec and r["batch"] == str(batch)
                and str(r.get("graph_opt_level", "")).strip() == opt):
            v = fnum(r.get("energy_j_per_inf"))
            if v is not None:
                vals.append(v)
    return statistics.mean(vals) if vals else None


def spearman(xs, ys):
    def rank(vs):
        order = sorted(range(len(vs)), key=lambda i: vs[i])
        rk = [0.0] * len(vs)
        for pos, i in enumerate(order):
            rk[i] = pos + 1
        return rk
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    rows = load(args.csv)
    models = sorted({r["model"] for r in rows if r["model"] in GFLOPS},
                    key=lambda m: GFLOPS[m])
    print("file: {}".format(args.csv))
    print("models: {}".format(len(models)))
    print()
    print("{:<20}{:>8}{:>12}{:>14}{:>14}{:>10}{:>10}".format(
        "model", "GFLOPs", "b1 J/inf", "b1 J/GFLOP", "b16 J/image",
        "rk FLOPs", "rk J"))
    data = []
    for m in models:
        g = GFLOPS[m]
        j1 = mean_j(rows, m, 1)
        j16 = mean_j(rows, m, 16)
        if j1 is None:
            continue
        per_img = (j16 / 16.0) if j16 is not None else None
        data.append((m, g, j1, per_img))
    flops_sorted = sorted(data, key=lambda d: d[1])
    j_sorted = sorted(data, key=lambda d: d[2])
    for m, g, j1, per_img in data:
        print("{:<20}{:>8.2f}{:>12.5f}{:>14.4f}{:>14.5f}{:>10}{:>10}".format(
            m, g, j1, j1 / g,
            per_img if per_img is not None else float("nan"),
            flops_sorted.index(next(d for d in data if d[0] == m)) + 1,
            j_sorted.index(next(d for d in data if d[0] == m)) + 1))
    print()
    spread = max(d[2] / d[1] for d in data) / min(d[2] / d[1] for d in data)
    print("J/GFLOP spread across models: {:.1f}x".format(spread))
    rho = spearman([d[1] for d in data], [d[2] for d in data])
    n = len(data)
    crit = {5: 0.9, 6: 0.829, 7: 0.714, 8: 0.643}.get(n)
    print("Spearman(FLOPs, J/inf) = {:.3f}  (n={}, p=0.05 critical value {})".format(
        rho, n, crit))
    if rho < (crit or 1.0):
        print("  -> rank correlation does NOT reach significance at n={}".format(n))
    print()
    print("pairwise checks (same stack, batch 1):")
    for i in range(len(data)):
        for k in range(i + 1, len(data)):
            a, b = data[i], data[k]
            fl = b[1] / a[1]
            en = b[2] / a[2]
            if (fl > 1.2 and en < 1.05) or (fl < 0.83 and en > 0.95):
                print("  {} vs {}: FLOPs x{:.2f} but energy x{:.2f}".format(
                    a[0], b[0], fl, en))
    return 0


if __name__ == "__main__":
    sys.exit(main())
