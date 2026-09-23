# -*- coding: utf-8 -*-
"""Cohen's kappa for the v3 round (mechanism + object type).

    supplement inputs:
      coding-sheet-A-v3.csv / coding-sheet-B-v3.csv
      codebook-v3-worked-examples.csv
    rewrites supplements/coding-121-final.csv with the merged result

    python repro/compute_kappa_v3.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
FIELDS = ["mechanism", "object_type"]
SYNONYM = {"放置": "异构", "边缘": "TinyML"}      # category synonyms from v2


def norm(v):
    v = (v or "").strip()
    return SYNONYM.get(v, v)


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None, None
    po = sum(1 for x, y in zip(a, b) if x == y) / float(n)
    pe = 0.0
    for c in set(a) | set(b):
        pe += (a.count(c) / float(n)) * (b.count(c) / float(n))
    return po, ((po - pe) / (1.0 - pe) if pe < 1.0 else 1.0)


def load(p):
    with p.open(newline="", encoding="utf-8-sig") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def main():
    a = load(SUP / "coding-sheet-A-v3.csv")
    b = load(SUP / "coding-sheet-B-v3.csv")
    ex = {}
    with (SUP / "codebook-v3-worked-examples.csv").open(
            encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            ex.setdefault(e["sample_id"], set()).add(e["field"])

    # start the merged coding from the v2 result (category / granularity agreed)
    merged = {}
    with (SUP / "coding-121-final.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            merged[r["sample_id"]] = {k: (v or "").strip()
                                      for k, v in r.items() if k != "sample_id"}

    report = ["field              N   agreement      kappa"]
    for col in FIELDS:
        va, vb = [], []
        for sid in sorted(a):
            if col in ex.get(sid, ()):
                continue
            x, y = norm(a[sid].get(col)), norm(b[sid].get(col))
            if not x or not y:
                continue
            va.append(x)
            vb.append(y)
            merged.setdefault(sid, {})[col] = x if x == y else ""
        po, k = kappa(va, vb)
        report.append("{:<14}{:>6}{:>13.3f}{:>10.3f}".format(
            col, len(va), po, k) if po is not None
            else "{:<14}{:>6}{:>13}{:>10}".format(col, 0, "-", "-"))

    # codebook cells are decided; write them in
    with (SUP / "codebook-v3-worked-examples.csv").open(
            encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            merged.setdefault(e["sample_id"], {})[e["field"]] = e["label"]

    cols = ["category", "object_type", "granularity", "mechanism"]
    out = SUP / "coding-121-final.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id"] + cols)
        w.writeheader()
        for sid in sorted(merged):
            row = {"sample_id": sid}
            row.update({c: merged[sid].get(c, "") for c in cols})
            w.writerow(row)

    text = "\n".join(report)
    (OUT / "kappa-v3-report.txt").write_text(text + "\n",
                                                        encoding="utf-8")
    print(text)
    print("")
    print("updated supplements/coding-121-final.csv "
          "(object_type replaces boundary)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
