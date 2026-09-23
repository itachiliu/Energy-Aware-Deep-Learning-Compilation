# -*- coding: utf-8 -*-
"""Effect-size audit for the mini-experiment.

For each group (model, backend, precision, batch, graph-opt) the raw CSV has
8 steady-state windows. This script reports mean, relative std, and, for the
comparisons the manuscript leans on, the gap in units of the pooled std -- so
it is clear which claims sit well above measurement noise and which do not.

    ~/dlxvenv/bin/python job/effect_size_check.py <results_scan.csv>
"""
import argparse
import csv
import math
import statistics
import sys


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def groups(rows):
    out = {}
    for r in rows:
        key = (r["model"], r["backend"], r["precision"], r["batch"],
               str(r.get("graph_opt_level", "")).strip())
        out.setdefault(key, []).append(fnum(r.get("energy_j_per_inf")))
    return out


def stats(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    m = statistics.mean(vals)
    s = statistics.stdev(vals)
    return m, s, (s / m * 100.0 if m else float("nan")), len(vals)


def compare(label, a, b, ga, gb):
    sa, sb = stats(ga), stats(gb)
    if not sa or not sb:
        print("{:<44} insufficient data".format(label))
        return
    ma, sda, rsda, na = sa
    mb, sdb, rsdb, nb = sb
    diff = mb - ma
    rel = diff / ma * 100.0
    pooled = math.sqrt((sda ** 2 + sdb ** 2) / 2.0)
    snr = abs(diff) / pooled if pooled else float("inf")
    verdict = "well above noise" if snr >= 5 else (
        "above noise" if snr >= 3 else (
            "marginal" if snr >= 2 else "at noise level"))
    print("{:<44} {:.5f} -> {:.5f}  {:+.1f}%  SNR={:5.1f}  {}".format(
        label, ma, mb, rel, snr, verdict))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    rows = load(args.csv)
    g = groups(rows)
    print("file: {}".format(args.csv))
    print("rows: {}  configs: {}".format(len(rows), len(g)))
    print()
    print("within-config relative std (8 windows):")
    worst = []
    for key, vals in sorted(g.items()):
        st = stats(vals)
        if st:
            worst.append((st[2], key, st[0], st[1]))
    worst.sort(reverse=True)
    print("  median RSD {:.2f}%   max {:.2f}%   (config {})".format(
        statistics.median([w[0] for w in worst]), worst[0][0], worst[0][1]))
    for rsd, key, m, s in worst[:3]:
        print("    {:.1f}%  {}  mean={:.5f} sd={:.5f}".format(rsd, key, m, s))
    print()
    print("key comparisons (A -> B), energy per batch call:")
    for model in sorted({k[0] for k in g}):
        for batch in sorted({k[3] for k in g if k[0] == model}, key=int):
            def get(backend, prec, opt):
                return g.get((model, backend, prec, batch, opt), [])
            compare("{} b{} ORT opt0 -> opt99".format(model, batch),
                    None, None, get("ort-cuda", "fp32", "0"),
                    get("ort-cuda", "fp32", "99"))
            compare("{} b{} eager FP32 -> compile FP32".format(model, batch),
                    None, None, get("torch-eager", "fp32", ""),
                    get("torch-compile", "fp32", ""))
            compare("{} b{} eager FP32 -> eager FP16".format(model, batch),
                    None, None, get("torch-eager", "fp32", ""),
                    get("torch-eager", "fp16", ""))
            compare("{} b{} compile FP32 -> compile FP16".format(model, batch),
                    None, None, get("torch-compile", "fp32", ""),
                    get("torch-compile", "fp16", ""))

    # H2 robustness: the manuscript's claim is that the latency-optimal config
    # is not the energy-optimal one. Ask how big that energy gap is relative to
    # the measurement scatter -- a 0.5% gap between two ORT levels is not a
    # finding, it is noise.
    print()
    print("H2 robustness -- latency-best vs energy-best within (model, batch):")
    print("{:<30}{:<26}{:<26}{:>9}{:>9}{:>9}".format(
        "group", "latency-best", "energy-best", "gap%", "SNR", "verdict"))
    keep = 0
    total = 0
    for model in sorted({k[0] for k in g}):
        for batch in sorted({k[3] for k in g if k[0] == model}, key=int):
            items = []
            for key, vals in g.items():
                if key[0] == model and key[3] == batch:
                    st = stats(vals)
                    lat_vals = None
                    items.append((key, st))
            if len(items) < 2:
                continue
            # latency lookup from the raw rows
            lat = {}
            for r in rows:
                if r["model"] != model or r["batch"] != batch:
                    continue
                k = (r["model"], r["backend"], r["precision"], r["batch"],
                     str(r.get("graph_opt_level", "")).strip())
                lat.setdefault(k, []).append(fnum(r.get("mean_lat_ms")))
            latm = {k: statistics.mean([v for v in vs if v is not None])
                    for k, vs in lat.items() if any(v is not None for v in vs)}
            if len(latm) < 2:
                continue
            best_lat = min(latm, key=lambda k: latm[k])
            best_j = min((k for k, st in items if st), key=lambda k: stats(g[k])[0])
            if best_lat == best_j:
                total += 1
                print("{:<30}{:<26}{:<26}{:>9}{:>9}{:>9}".format(
                    "{} b{}".format(model, batch),
                    "/".join(best_lat[1:4]), "/".join(best_j[1:4]),
                    "0.0", "-", "same config"))
                continue
            total += 1
            ma, sda, _, _ = stats(g[best_lat])
            mb, sdb, _, _ = stats(g[best_j])
            gap = (ma - mb) / mb * 100.0
            pooled = math.sqrt((sda ** 2 + sdb ** 2) / 2.0)
            snr = abs(ma - mb) / pooled if pooled else float("inf")
            ok = snr >= 3
            keep += 1 if ok else 0
            print("{:<30}{:<26}{:<26}{:>9.1f}{:>9.1f}{:>9}".format(
                "{} b{}".format(model, batch),
                "/".join(best_lat[1:4]), "/".join(best_j[1:4]),
                gap, snr, "holds" if ok else "noise"))
            if ok:
                va = [v for v in g[best_lat] if v is not None]
                vb = [v for v in g[best_j] if v is not None]
                sep = min(va) > max(vb)
                aj = statistics.mean(va) - statistics.mean(vb)
                print("      abs gap {:.4f} J   rep separation: {} "
                      "(min A {:.5f} vs max B {:.5f})".format(
                          aj, "complete" if sep else "overlapping",
                          min(va), max(vb)))
    print("  disagreements surviving SNR>=3: {} of {}".format(keep, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
