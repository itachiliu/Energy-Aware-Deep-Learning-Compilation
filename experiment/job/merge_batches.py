# -*- coding: utf-8 -*-
"""Concatenate several scan runs into one raw CSV for joint analysis.

The two x86 runs used the same protocol and the same environment, so the rows
are directly comparable; each run keeps its own GPU/clock columns, which is what
lets us show cross-node consistency afterwards.

    python job/merge_batches.py --out merged.csv runA/results_scan.csv runB/results_scan.csv
"""
import argparse
import csv
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("inputs", nargs="+")
    args = ap.parse_args()

    rows = []
    header = None
    for path in args.inputs:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if header is None:
                header = reader.fieldnames
            elif reader.fieldnames != header:
                sys.stderr.write("schema mismatch in {}\n".format(path))
                return 2
            rows.extend(list(reader))

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    configs = {(r["model"], r["backend"], r["precision"], r["batch"],
                str(r.get("graph_opt_level", "")).strip()) for r in rows}
    print("wrote {} rows, {} configs from {} files".format(
        len(rows), len(configs), len(args.inputs)))
    models = sorted({r["model"] for r in rows})
    print("models: {}".format(", ".join(models)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
