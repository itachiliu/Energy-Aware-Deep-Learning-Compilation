# -*- coding: utf-8 -*-
"""Standard two-coder Cohen's kappa for the v2 coding round.

Inputs:
  supplements/coding-sheet-A-v2.csv   filled by coder A
  supplements/coding-sheet-B-v2.csv   filled by coder B (independently)
  supplements/codebook-v2-worked-examples.csv

Cells fixed by the codebook are excluded, so kappa is computed on the items the
two coders actually judged independently. Writes repro/kappa-v2-report.txt and
repro/coding-121-final.csv (agreed cells + codebook cells).

    python repro/compute_kappa_v2.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
COLS = ["category", "boundary", "granularity", "mechanism"]

# The controlled vocabulary is fixed, but both coders used a synonym for two
# categories: 放置 for 异构 and 边缘 for TinyML. Counted after normalisation;
# the sheets keep what the coders actually wrote.
SYNONYM = {"放置": "异构", "边缘": "TinyML"}


def norm(v):
    v = (v or "").strip()
    return SYNONYM.get(v, v)


def load(p):
    with p.open(newline="", encoding="utf-8-sig") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None, None
    po = sum(1 for x, y in zip(a, b) if x == y) / float(n)
    pe = 0.0
    for c in set(a) | set(b):
        pe += (a.count(c) / float(n)) * (b.count(c) / float(n))
    return po, ((po - pe) / (1.0 - pe) if pe < 1.0 else 1.0)


def main():
    a = load(SUP / "coding-sheet-A-v2.csv")
    b = load(SUP / "coding-sheet-B-v2.csv")
    ex = {}
    with (SUP / "codebook-v2-worked-examples.csv").open(encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            ex.setdefault(e["sample_id"], set()).add(e["field"])

    report = ["field              N   agreement      kappa"]
    final = {}
    for col in COLS:
        va, vb = [], []
        for sid in sorted(a):
            if col in ex.get(sid, ()):          # decided by the codebook
                continue
            x = (a[sid].get(col) or "").strip()
            y = (b[sid].get(col) or "").strip()
            if x and y:
                x, y = norm(x), norm(y)
                va.append(x)
                vb.append(y)
                final.setdefault(sid, {})[col] = x if x == y else ""
        po, k = kappa(va, vb)
        if po is None:
            report.append("{:<14}{:>6}{:>13}{:>10}".format(col, 0, "-", "-"))
        else:
            report.append("{:<14}{:>6}{:>13.3f}{:>10.3f}".format(
                col, len(va), po, k))

    # add the codebook cells to the final coding
    with (SUP / "codebook-v2-worked-examples.csv").open(encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            final.setdefault(e["sample_id"], {})[e["field"]] = e["label"]

    out = SUP / "coding-121-final.csv"
    fields = ["sample_id"] + COLS
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in sorted(final):
            row = {"sample_id": sid}
            row.update({c: final[sid].get(c, "") for c in COLS})
            w.writerow(row)

    text = "\n".join(report)
    (OUT / "kappa-v2-report.txt").write_text(text + "\n",
                                                        encoding="utf-8")
    print(text)
    print("")
    print("wrote repro/kappa-v2-report.txt and supplements/coding-121-final.csv")
    print("(blank cells in the final coding mark disagreements to reconcile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
