# -*- coding: utf-8 -*-
"""Cohen's kappa between coder A and coder B on the 121-study coding table.

Inputs (defaults):
  supplements/coding-121-coderA.csv        author labels
  supplements/coding-121-coderB-blank.csv  the sheet handed to coder B

Coder B fills category / boundary / granularity / mechanism. Rows B left blank
are ignored, so a partial return still yields a usable figure (report N).
Writes repro/kappa-report.txt in UTF-8 and prints an ASCII summary.

    python repro/compute_kappa_two_coder.py
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLS = ["category", "boundary", "granularity", "mechanism"]


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None, None
    po = sum(1 for x, y in zip(a, b) if x == y) / float(n)
    classes = set(a) | set(b)
    pe = 0.0
    for c in classes:
        pe += (a.count(c) / float(n)) * (b.count(c) / float(n))
    k = (po - pe) / (1.0 - pe) if pe < 1.0 else 1.0
    return po, k


def load(path, prefix):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {r["sample_id"]: r for r in rows}, list(rows[0].keys()) if rows else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coder-a", default=str(SUP /
                                            "coding-121-coderA.csv"))
    ap.add_argument("--coder-b", default=str(SUP /
                                            "coding-121-coderB-blank.csv"))
    args = ap.parse_args()

    a, _ = load(Path(args.coder_a), "a")
    b, _ = load(Path(args.coder_b), "b")

    report = []
    pairs = {}
    for sid, ra in sorted(a.items()):
        rb = b.get(sid)
        if not rb:
            continue
        for col in COLS:
            va = (ra.get(col) or "").strip()
            vb = (rb.get(col) or "").strip()
            if va and vb:
                pairs.setdefault(col, []).append((va, vb))

    if not pairs:
        print("coder B sheet is empty; nothing to compute")
        print("fill supplements/coding-121-coderB-blank.csv first")
        return 1

    report.append("coder A: {}".format(Path(args.coder_a).name))
    report.append("coder B: {}".format(Path(args.coder_b).name))
    report.append("")
    report.append("{:<14}{:>6}{:>14}{:>10}".format(
        "field", "N", "agreement", "kappa"))
    for col in COLS:
        pl = pairs.get(col)
        if not pl:
            report.append("{:<14}{:>6}{:>14}{:>10}".format(col, 0, "-", "-"))
            continue
        va = [x for x, _ in pl]
        vb = [y for _, y in pl]
        po, k = kappa(va, vb)
        report.append("{:<14}{:>6}{:>13.3f}{:>10.3f}".format(
            col, len(pl), po, k))

    text = "\n".join(report)
    (OUT / "kappa-report.txt").write_text(text + "\n",
                                                     encoding="utf-8")
    print("wrote repro/kappa-report.txt")
    print("fields computed: {}".format(", ".join(sorted(pairs))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
