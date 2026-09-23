# -*- coding: utf-8 -*-
"""Agreement and Cohen's kappa for the 30-row independent audit.

  --audit      audit/coding-audit-sample30-blank.csv  (filled by auditor)
  --reference  audit/coding-121-coderA.csv            (author labels)

Compares the auditor's granularity / mechanism labels with the author coding for
the same sample ids. Writes audit/audit30-report.txt (UTF-8).

    python audit/compute_audit30.py
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None, None
    po = sum(1 for x, y in zip(a, b) if x == y) / float(n)
    pe = 0.0
    for c in set(a) | set(b):
        pe += (a.count(c) / float(n)) * (b.count(c) / float(n))
    k = (po - pe) / (1.0 - pe) if pe < 1.0 else 1.0
    return po, k


def load(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default=str(HERE /
                                          "coding-audit-sample30-blank.csv"))
    ap.add_argument("--reference", default=str(HERE /
                                              "coding-121-coderA.csv"))
    args = ap.parse_args()

    audit = load(Path(args.audit))
    ref = load(Path(args.reference))

    pairs = {"granularity": [], "mechanism": []}
    for sid, ra in sorted(audit.items()):
        rr = ref.get(sid)
        if not rr:
            continue
        for col in pairs:
            va = (ra.get(col) or "").strip()
            vb = (rr.get(col) or "").strip()
            if va and vb:
                pairs[col].append((va, vb))

    if not any(pairs.values()):
        print("audit sheet is empty; fill audit/coding-audit-sample30-blank.csv")
        return 1

    report = ["audit: {}  reference: {}".format(Path(args.audit).name,
                                                Path(args.reference).name), ""]
    report.append("{:<14}{:>6}{:>14}{:>10}".format(
        "field", "N", "agreement", "kappa"))
    for col in ("granularity", "mechanism"):
        pl = pairs[col]
        if not pl:
            report.append("{:<14}{:>6}{:>14}{:>10}".format(col, 0, "-", "-"))
            continue
        po, k = kappa([x for x, _ in pl], [y for _, y in pl])
        report.append("{:<14}{:>6}{:>13.3f}{:>10.3f}".format(
            col, len(pl), po, k))

    text = "\n".join(report)
    (HERE / "audit30-report.txt").write_text(text + "\n",
                                                       encoding="utf-8")
    print("wrote audit/audit30-report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
