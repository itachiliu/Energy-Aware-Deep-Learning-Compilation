# -*- coding: utf-8 -*-
"""Aggregate a scan results CSV and sanity-check it before it goes into the paper.

Usage:
    python job/analyze_x86_batch.py scan_x86_out_*/results_scan.csv [--batch1 old.csv]

Checks that matter after the first x86 run:
  * every ORT row must actually have run on the GPU (ORT falls back to CPU
    silently when the CUDA EP cannot load, which shows up as idle-level power
    and 100x+ latency);
  * latency-optimal vs energy-optimal config per (model, batch) -- the H2 claim;
  * optional side-by-side against the batch-1 CSV.
"""
import argparse
import csv
import statistics
import sys
from pathlib import Path

# Login nodes often map `python` to Python 2. Keep this file parseable there so
# it can say something useful instead of dying on a SyntaxError.
if sys.version_info < (3, 6):
    sys.stderr.write(
        "This script needs Python 3.6+.\n"
        "On many login nodes `python` is Python 2; use the env interpreter:\n"
        "  ~/dlxvenv/bin/python job/analyze_x86_batch.py <results.csv>\n")
    sys.exit(2)


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
    # Accept both the raw per-repetition schema (results_scan.csv) and the
    # aggregated one (results_scan_agg.csv / results_scan_agg_v2.csv), so the same
    # tool can compare two batches even when only the aggregate survived.
    aliases = {
        "lat_ms_mean": "mean_lat_ms",
        "lat_ms": "mean_lat_ms",
        "power_w": "mean_power_w",
        "idle_w": "idle_power_w",
        "p95_ms": "p95_lat_ms",
        "j_inf_gross": "energy_j_per_inf",
        "j_inf_net": "energy_net_j_per_inf",
    }
    for row in rows:
        for src, dst in aliases.items():
            if src in row and not row.get(dst):
                row[dst] = row[src]
    return rows


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def group(rows):
    out = {}
    for r in rows:
        key = (r.get("model", "?"), r.get("backend", "?"), r.get("precision", "?"),
               r.get("batch", "?"), r.get("graph_opt_level", "?"))
        out.setdefault(key, []).append(r)
    return out


def agg(reps, field):
    vals = [fnum(r.get(field)) for r in reps]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return m, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--batch1", default=None,
                    help="older results CSV to compare against")
    args = ap.parse_args()

    rows = load(args.csv)
    if not rows:
        print("empty csv")
        return 1
    groups = group(rows)

    print("file: {}".format(args.csv))
    print("rows: {}   configs: {}".format(len(rows), len(groups)))
    backends = sorted({k[1] for k in groups})
    print("backends present: {}".format(", ".join(backends)))
    print()

    hdr = ("{:<13}{:<14}{:<6}{:>3}{:>5}{:>11}{:>11}{:>8}{:>8}{:>12}{:>14}".format(
        "model", "backend", "prec", "b", "opt",
        "lat_ms", "p95", "P_W", "idle_W", "J/inf", "EDP"))
    print(hdr)
    print("-" * len(hdr))

    suspects = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[3] == "16", str(k[4]))):
        model, backend, prec, batch, opt = key
        reps = groups[key]
        lat, lat_s = agg(reps, "mean_lat_ms")
        p95, _ = agg(reps, "p95_lat_ms")
        pw, _ = agg(reps, "mean_power_w")
        idle, _ = agg(reps, "idle_power_w")
        j, _ = agg(reps, "energy_j_per_inf")
        edp, _ = agg(reps, "edp")
        print("{:<13}{:<14}{:<6}{:>3}{:>5}{:>11.3f}{:>11.3f}{:>8.2f}{:>8.2f}"
              "{:>12.5f}{:>14.6f}".format(
                  model, backend, prec, batch, str(opt),
                  lat, p95, pw, idle, j, edp))

        # A CPU fallback sits *at* idle (ratio ~1.0). Small GPU workloads such as
        # MobileNetV2 at batch 1 legitimately draw only ~1.2x idle, so the bar has
        # to be tight or the report cries wolf.
        if pw is not None and idle is not None and idle > 0:
            if pw < idle * 1.15:
                suspects.append((key, pw, idle, lat))

    print()
    if suspects:
        print("!! SUSPECT ROWS -- power is at idle level, the backend probably fell")
        print("   back to CPU (check the ORT provider list):")
        for key, pw, idle, lat in suspects:
            print("   {}: power={:.2f} W vs idle={:.2f} W, lat={:.1f} ms".format(
                key, pw, idle, lat))
    else:
        print("power sanity: all configs draw above idle, no CPU-fallback signature")

    print()
    print("H2 check -- latency-optimal vs energy-optimal within each (model, batch, backend):")
    picked = 0
    for model in sorted({k[0] for k in groups}):
        for backend in sorted({k[1] for k in groups if k[0] == model}):
            for batch in sorted({k[3] for k in groups if k[0] == model and k[1] == backend}):
                items = []
                for key, reps in groups.items():
                    if (key[0], key[1], key[3]) != (model, backend, batch):
                        continue
                    lat, _ = agg(reps, "mean_lat_ms")
                    j, _ = agg(reps, "energy_j_per_inf")
                    if lat is not None and j is not None:
                        items.append((key[4], lat, j))
                if len(items) < 2:
                    continue
                best_lat = min(items, key=lambda x: x[1])
                best_j = min(items, key=lambda x: x[2])
                verdict = "supports H2" if best_lat[0] != best_j[0] else "same config"
                print("  {:<13}{:<14}b{}: lat-best=opt{} J-best=opt{}  -> {}".format(
                    model, backend, batch, best_lat[0], best_j[0], verdict))
                picked += 1
    if picked == 0:
        print("  (no group had two comparable configs yet)")

    print()
    print("cross-backend energy per batch call (J), lowest wins; spread = (max-min)/min:")
    print("{:<13}{:>3}{:>12}{:>12}{:>12}{:>13}{:>13}{:>16}{:>9}".format(
        "model", "b", "ort-cuda", "eager-fp32", "eager-fp16",
        "comp-fp32", "comp-fp16", "best", "spread%"))
    for model in sorted({k[0] for k in groups}):
        batches = sorted({k[3] for k in groups if k[0] == model},
                         key=lambda x: int(x) if str(x).isdigit() else 0)
        for batch in batches:
            cells = {}
            for key, reps in groups.items():
                if key[0] != model or key[3] != batch:
                    continue
                backend, prec = key[1], key[2]
                if backend == "ort-cuda":
                    label = "ort-cuda"
                elif backend == "torch-eager":
                    label = "eager-" + prec
                elif backend == "torch-compile":
                    label = "comp-" + prec
                else:
                    label = backend
                value, _ = agg(reps, "energy_j_per_inf")
                if value is None:
                    continue
                if label not in cells or value < cells[label]:
                    cells[label] = value
            if not cells:
                continue
            best = min(cells, key=lambda k: cells[k])
            spread = ((max(cells.values()) - min(cells.values()))
                      / min(cells.values()) * 100.0)

            def cell(name):
                return "{:.5f}".format(cells[name]) if name in cells else "-"

            print("{:<13}{:>3}{:>12}{:>12}{:>12}{:>13}{:>13}{:>16}{:>9.1f}".format(
                model, batch, cell("ort-cuda"), cell("eager-fp32"),
                cell("eager-fp16"), cell("comp-fp32"), cell("comp-fp16"),
                best, spread))

    if args.batch1 and Path(args.batch1).exists():
        old = load(args.batch1)
        og = group(old)
        print()
        print("batch-1 vs batch-2, same (model, backend, precision, batch), fp32 ORT:")
        print("{:<13}{:>3}{:>12}{:>12}{:>12}{:>12}{:>8}{:>8}".format(
            "model", "b", "batch1 lat", "batch2 lat",
            "batch1 J", "batch2 J", "lat x", "J x"))
        for model in sorted({k[0] for k in og} & {k[0] for k in groups}):
            for batch in sorted({k[3] for k in og} & {k[3] for k in groups}):
                a = [k for k in og if k[0] == model and k[3] == batch
                     and k[1] == "ort-cuda" and k[2] == "fp32"]
                b = [k for k in groups if k[0] == model and k[3] == batch
                     and k[1] == "ort-cuda" and k[2] == "fp32"]
                if not a or not b:
                    continue
                la, _ = agg(og[a[0]], "mean_lat_ms")
                lb, _ = agg(groups[b[0]], "mean_lat_ms")
                ja, _ = agg(og[a[0]], "energy_j_per_inf")
                jb, _ = agg(groups[b[0]], "energy_j_per_inf")
                if None in (la, lb, ja, jb):
                    continue
                print("{:<13}{:>3}{:>12.3f}{:>12.3f}{:>12.5f}{:>12.5f}"
                      "{:>8.2f}{:>8.2f}".format(
                          model, batch, la, lb, ja, jb, lb / la, jb / ja))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
