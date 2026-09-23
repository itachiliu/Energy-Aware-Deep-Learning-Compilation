# -*- coding: utf-8 -*-
"""Build the reconciliation worksheet from the v2+v3 disagreements.

Every cell where the two coders differ (and that the codebook does not already
decide) is listed once, with the rubric clause that governs it, so the two
coders can settle it in one sitting. Writes supplements/reconciliation-sheet.csv.

    python repro/make_reconciliation_sheet.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
PAIRS = [("coding-sheet-A-v2.csv", "coding-sheet-B-v2.csv",
          ["category", "granularity"]),
         ("coding-sheet-A-v3.csv", "coding-sheet-B-v3.csv",
          ["mechanism", "object_type"])]
RULE = {
    "category": "coding-rubric-v2 §3 类别裁决表",
    "granularity": "coding-rubric-v2 §2 粒度定义 / §1 粒度 Other 判据",
    "mechanism": "coding-rubric-v2 §1-§2 + v3 M1/M2",
    "object_type": "coding-rubric-v3 一、对象类型",
}
SYNONYM = {"放置": "异构", "边缘": "TinyML"}


def norm(v):
    v = (v or "").strip()
    return SYNONYM.get(v, v)


def load(name):
    with (SUP / name).open(newline="", encoding="utf-8-sig") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def main():
    rows = []
    for a_name, b_name, cols in PAIRS:
        a, b = load(a_name), load(b_name)
        for col in cols:
            for sid in sorted(a):
                x, y = norm(a[sid].get(col)), norm(b[sid].get(col))
                if not x or not y or x == y:
                    continue
                rows.append({"sample_id": sid, "field": col,
                             "coder_A": x, "coder_B": y, "agreed": "",
                             "rule": RULE[col], "note": ""})
    out = SUP / "reconciliation-sheet.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "field", "coder_A",
                                          "coder_B", "agreed", "rule", "note"])
        w.writeheader()
        w.writerows(rows)
    per = {}
    for r in rows:
        per[r["field"]] = per.get(r["field"], 0) + 1
    print("wrote {} ({} rows)".format(out.name, len(rows)))
    for k in sorted(per):
        print("   {:<14} {}".format(k, per[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
