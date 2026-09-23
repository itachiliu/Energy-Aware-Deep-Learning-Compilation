# -*- coding: utf-8 -*-
"""Check and apply the round-3 adjudication of the 65 still-split cells.

Inputs (filled by the two coders, independently):
  supplements/adjudication-round3-rules.csv    rule ballot (write 1 or 2)
  supplements/adjudication-round3-coder-A.csv  cell sheet (write into round3)
  supplements/adjudication-round3-coder-B.csv

The script reports, in this order:
  1. rules where the two coders picked different options (needs discussion);
  2. cells whose round-3 choice contradicts the rule the coders agreed on;
  3. cells the two coders still judge differently;
  4. cells it can write into supplements/coding-121-final.csv (both agree).

    python repro/apply_adjudication3.py            # report only
    python repro/apply_adjudication3.py --write    # update the final coding
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
FIELDS = ["category", "granularity", "mechanism", "object_type"]


def load(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def cell_map(rows):
    return {(r["sample_id"], r["field"]): (r["round3"] or "").strip()
            for r in rows}


def rule_choice(raw, value_1, value_2):
    """Accept '1'/'2', the option label, or the coded value itself."""
    v = (raw or "").strip()
    if v in ("1", "2"):
        return value_1 if v == "1" else value_2
    if v in (value_1, value_2):
        return v
    return ""


def main():
    write = "--write" in sys.argv
    rules = load(SUP / "adjudication-round3-rules.csv")
    a = cell_map(load(SUP / "adjudication-round3-coder-A.csv"))
    b = cell_map(load(SUP / "adjudication-round3-coder-B.csv"))
    if set(a) != set(b):
        print("the two cell sheets list different cells")
        return 1

    rule_value = {}
    rule_disagree = []
    for r in rules:
        x = rule_choice(r["coder_A_rule"], r["value_1"], r["value_2"])
        y = rule_choice(r["coder_B_rule"], r["value_1"], r["value_2"])
        cells = r["cells"].split()
        if not x or not y:
            continue
        if x != y:
            rule_disagree.append((r["rule_id"], x, y, " ".join(cells)))
            continue
        for sid in cells:
            rule_value[(sid, r["field"])] = x

    contradict, split, agree, blank = [], [], [], []
    for key in sorted(a):
        x, y = a[key], b[key]
        if not x or not y:
            blank.append(key)
            continue
        if x != y:
            split.append((key, x, y))
            continue
        implied = rule_value.get(key)
        if implied and implied != x:
            contradict.append((key, x, implied))
        agree.append((key, x))

    print("rules still disputed          : {}".format(len(rule_disagree)))
    for rid, x, y, cells in rule_disagree:
        print("   {} {} vs {}  ({})".format(rid, x, y, cells))
    print("cells filled by both coders   : {}".format(len(agree) + len(split)))
    print("  agreed                     : {}".format(len(agree)))
    print("  still split                : {}".format(len(split)))
    for key, x, y in split:
        print("   {} {}  {} vs {}".format(key[0], key[1], x, y))
    print("cells left blank              : {}".format(len(blank)))
    print("cells contradicting the agreed rule : {}".format(len(contradict)))
    for key, chosen, implied in contradict:
        print("   {} {}  chose {} but its rule implies {}".format(
            key[0], key[1], chosen, implied))

    if not write:
        print("\n(report only; pass --write to update coding-121-final.csv)")
        return 0

    with (SUP / "coding-121-final.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    by_sid = {r["sample_id"]: r for r in rows}
    applied = 0
    for (sid, field), value in agree:
        by_sid[sid][field] = value
        applied += 1
    with (SUP / "coding-121-final.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id"] + FIELDS)
        w.writeheader()
        for sid in sorted(by_sid):
            w.writerow({k: by_sid[sid].get(k, "")
                        for k in ["sample_id"] + FIELDS})
    print("\napplied {} agreed cells to supplements/coding-121-final.csv".format(
        applied))
    print("now run: sync_appendix_from_final.py --write ; count_matrix.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
