# -*- coding: utf-8 -*-
"""Generate the two independent coding sheets for the v2 round.

Both sheets are identical (context columns + four empty label columns). The
12 cells that the codebook already decides (codebook-v2-worked-examples.csv)
are marked in a `prefilled` column so the coders can skip them and the kappa
script can exclude them.

    python repro/make_v2_sheets.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
SRC = SUP / "appendix-matrix-code.csv"
EX = SUP / "codebook-v2-worked-examples.csv"
COLS = ["category", "boundary", "granularity", "mechanism"]


def main():
    rows = []
    with SRC.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "sample_id": r["S"],
                "bibkey": r["BibKey"].replace("\\_", "_"),
                "name": r["Name"],
                "year": r["Year"],
                "venue": r["Venue"],
                "category": "", "boundary": "", "granularity": "",
                "mechanism": "",
                "prefilled": "",
            })
    by_id = {r["sample_id"]: r for r in rows}

    ex = list(csv.DictReader(EX.open(encoding="utf-8-sig")))
    for e in ex:
        r = by_id.get(e["sample_id"])
        assert r is not None, e
        assert e["field"] in COLS, e
        r[e["field"]] = e["label"]
        r["prefilled"] = (r["prefilled"] + "," + e["field"]).strip(",")

    fields = ["sample_id", "bibkey", "name", "year", "venue"] + COLS + ["prefilled"]
    for name in ("coding-sheet-A-v2.csv", "coding-sheet-B-v2.csv"):
        with (SUP / name).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            # both sheets are identical: labels stay blank, the `prefilled`
            # column only marks which cells the codebook already decides
            w.writerows([{c: ("" if c in COLS else r.get(c, ""))
                          for c in fields} for r in rows])
        print("wrote {} ({} rows)".format(name, len(rows)))
    print("worked-example cells excluded from kappa: {}".format(len(ex)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
