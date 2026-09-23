# -*- coding: utf-8 -*-
"""Post-run integrity checks for the compiler-decision scan.

Verifies that every expected config has aggregated rows and that key numeric
fields are present, then prints a compact per-(model,batch) latency/energy
optimum table that feeds the paper's H2 statement.
"""
import argparse
import csv
import statistics
from pathlib import Path


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="results_scan.csv")
    ap.add_argument("--models", default="mobilenetv2,resnet50,vit_b_16")
    ap.add_argument("--batches", default="1,16")
    ap.add_argument("--graph-opts", default="0,1,2,99")
    ap.add_argument("--reps", type=int, default=8)
    args = ap.parse_args()

    rows = load(args.raw)
    if not rows:
        print("ERROR: empty raw csv")
        return 1

    models = [x.strip() for x in args.models.split(",") if x.strip()]
    batches = [x.strip() for x in args.batches.split(",") if x.strip()]
    opts = [x.strip() for x in args.graph_opts.split(",") if x.strip()]

    expected = {}
    for m in models:
        for b in batches:
            for o in opts:
                expected[(m, "ort-cuda", "fp32", b, o)] = args.reps
            for p in ("fp32", "fp16"):
                expected[(m, "torch-eager", p, b, "")] = args.reps

    got = {}
    for r in rows:
        key = (r.get("model"), r.get("backend"), r.get("precision"),
               r.get("batch"), r.get("graph_opt_level") or "")
        got.setdefault(key, []).append(r)

    problems = []
    for key, want_reps in sorted(expected.items()):
        reps = got.get(key, [])
        if len(reps) != want_reps:
            problems.append(f"{key}: expected {want_reps} reps, got {len(reps)}")
            continue
        for r in reps:
            if fnum(r.get("energy_j_per_inf")) is None:
                problems.append(f"{key}: missing energy_j_per_inf")
                break
            if fnum(r.get("mean_lat_ms")) is None:
                problems.append(f"{key}: missing mean_lat_ms")
                break

    print(f"rows={len(rows)} expected-configs={len(expected)} problems={len(problems)}")
    for p in problems[:30]:
        print("  PROBLEM:", p)

    print("\n== latency/energy optima per (model, batch) ==")
    for m in models:
        for b in batches:
            items = []
            for key, reps in got.items():
                if key[0] != m or key[3] != b:
                    continue
                lat = mean([fnum(r.get("mean_lat_ms")) for r in reps])
                eng = mean([fnum(r.get("energy_j_per_inf")) for r in reps])
                if lat is not None and eng is not None:
                    tag = f"{key[1]}/{key[2]}/opt{key[4] or '-'}/b{key[3]}"
                    items.append((tag, lat, eng))
            if len(items) >= 2:
                bl = min(items, key=lambda x: x[1])
                be = min(items, key=lambda x: x[2])
                print(f"  {m} b{b}: latency-opt={bl[0]} ({bl[1]:.4f} ms) | "
                      f"energy-opt={be[0]} ({be[2]:.6f} J) | "
                      f"divergent={'YES' if bl[0] != be[0] else 'no'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
