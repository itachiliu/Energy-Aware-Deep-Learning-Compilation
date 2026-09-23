# -*- coding: utf-8 -*-
"""Generate the independent-coding sheets from the author coding table.

Outputs (under supplements/):
  coding-121-coderA.csv          author labels, kept as the internal record
  coding-121-coderB-blank.csv    same rows, labels withheld -> for coder B
  coding-audit-sample30-blank.csv  30-row stratified sample, labels withheld
  coding-audit-sample30-selection.txt  the sampled S-ids and the seed

Run:  python repro/make_coding_sheets.py
"""
import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CODING = HERE.parent
AUDIT = ROOT / "audit"
SRC = AUDIT / "appendix-matrix-code.csv"
OUT = CODING

LABEL_COLS = ["category", "boundary", "granularity", "mechanism"]
CONTEXT_COLS = ["sample_id", "bibkey", "name", "year", "venue"]
SEED = 20260909
N_AUDIT = 30


def load():
    rows = []
    with SRC.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "sample_id": r["S"],
                "bibkey": r["BibKey"].replace("\\_", "_"),
                "name": r["Name"],
                "year": r["Year"],
                "venue": r["Venue"],
                "category": r["Category"],
                "boundary": r["Boundary"],
                "granularity": r["Granularity"],
                "mechanism": r["Mechanism"],
            })
    return rows


def write(path, rows, cols):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print("wrote {} ({} rows)".format(path.name, len(rows)))


def main():
    rows = load()
    assert len(rows) == 121, len(rows)

    # 1) author record
    a_cols = CONTEXT_COLS + LABEL_COLS
    write(OUT / "coding-121-coderA.csv", rows, a_cols)

    # 2) blank sheet for coder B: context only, labels withheld
    blank = [{k: r[k] for k in CONTEXT_COLS} for r in rows]
    write(OUT / "coding-121-coderB-blank.csv", blank, CONTEXT_COLS + LABEL_COLS)

    # 3) stratified 30-row audit sample (fixed seed), labels withheld
    rng = random.Random(SEED)
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    picked = []
    cats = sorted(by_cat)
    per = N_AUDIT / float(len(cats))
    for cat in cats:
        pool = sorted(by_cat[cat], key=lambda r: r["sample_id"])
        take = max(1, int(round(per)))
        picked += rng.sample(pool, min(take, len(pool)))
    if len(picked) > N_AUDIT:
        picked = rng.sample(picked, N_AUDIT)
    while len(picked) < N_AUDIT:
        extra = rng.choice([r for r in rows if r not in picked])
        picked.append(extra)
    picked.sort(key=lambda r: r["sample_id"])

    audit_cols = CONTEXT_COLS + ["granularity", "mechanism", "notes"]
    audit = [{k: r[k] for k in CONTEXT_COLS} for r in picked]
    write(OUT / "coding-audit-sample30-blank.csv", audit, audit_cols)
    (OUT / "coding-audit-sample30-selection.txt").write_text(
        "seed = {}\nN = {}\nstratified by the ten categories\nids: {}\n".format(
            SEED, len(picked), ", ".join(r["sample_id"] for r in picked)),
        encoding="utf-8")
    print("wrote coding-audit-sample30-selection.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
