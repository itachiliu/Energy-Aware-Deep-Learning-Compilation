# -*- coding: utf-8 -*-
"""Generate the v3 re-code sheets (mechanism + object type only).

Both sheets are identical: context columns plus two empty label columns. Cells
the codebook already decides are marked in `prefilled` so they can be skipped
and excluded from kappa.

    python repro/make_v3_sheets.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
V3COLS = ["mechanism", "object_type"]


def main():
    rows = []
    with (SUP / "appendix-matrix-code.csv").open(newline="",
                                                 encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "sample_id": r["S"],
                "bibkey": r["BibKey"].replace("\\_", "_"),
                "name": r["Name"],
                "year": r["Year"],
                "venue": r["Venue"],
                "mechanism": "",
                "object_type": "",
                "prefilled": "",
            })
    by_id = {r["sample_id"]: r for r in rows}

    ex = list(csv.DictReader(
        (SUP / "codebook-v3-worked-examples.csv").open(encoding="utf-8-sig")))
    n_ex = 0
    for e in ex:
        if e["field"] not in V3COLS:
            continue
        r = by_id.get(e["sample_id"])
        assert r is not None, e
        r["prefilled"] = (r["prefilled"] + "," + e["field"]).strip(",")
        n_ex += 1

    fields = ["sample_id", "bibkey", "name", "year", "venue"] + V3COLS + ["prefilled"]
    for name in ("coding-sheet-A-v3.csv", "coding-sheet-B-v3.csv"):
        with (SUP / name).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows([{c: ("" if c in V3COLS else r.get(c, ""))
                          for c in fields} for r in rows])
        print("wrote {} ({} rows)".format(name, len(rows)))
    per = {c: sum(1 for e in ex if e["field"] == c) for c in V3COLS}
    print("codebook cells to skip: {} ({} cells)".format(per, n_ex))
    return 0


if __name__ == "__main__":
    sys.exit(main())
