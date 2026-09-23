# -*- coding: utf-8 -*-
"""Merge the two coders' reconciliation decisions into the final coding table.

Round 1: coder A and coder B code all 121 samples independently
         (coding-sheet-{A,B}-v2.csv / -v3.csv). Cohen's kappa is computed on
         that round only (repro/compute_kappa_v3.py).
Round 2: both coders re-read every disagreement cell against the codebook and
         file one adjudication each
         (supplements/reconciliation-resolution-{1,2}-full.csv).
Round 3: the two coders re-adjudicated jointly and filed one final resolution
         for all 96 cells (supplements/reconciliation-resolution-final.csv,
         saved from the returned worksheet). With --tie-break final that file
         is authoritative; the earlier per-cell rules remain available.

    python repro/merge_reconciliation.py [--tie-break final|res1|res2|strict]

        final  第三轮联合复核决议（reconciliation-resolution-final.csv），默认
        res1   第一作者依编码手册裁定（resolution-1 值），默认
        res2   第二编码者依编码手册裁定（resolution-2 值）
        strict 仍未收敛的单元留空，不进入任何交叉统计

Rewrites supplements/coding-121-final.csv and prints a coverage report to
repro/reconciliation-report.txt.
"""
import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
COLS = ["category", "object_type", "granularity", "mechanism"]
FIELDS = ["category", "granularity", "mechanism", "object_type"]
RES = {
    "res1": SUP / "reconciliation-resolution-1-full.csv",
    "res2": SUP / "reconciliation-resolution-2.csv",
    "final": SUP / "reconciliation-resolution-final.txt",
}


def load_resolution(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return {(r["sample_id"], r["field"]): r for r in csv.DictReader(f)}


def merge_final(rec1, rec2):
    """Apply the round-3 joint resolution (all 96 cells) to the final coding."""
    rec3 = load_resolution(RES["final"])
    r1 = {k: (v["agreed"] or "").strip() for k, v in rec1.items()}
    r2 = {k: (v["agreed"] or "").strip() for k, v in rec2.items()}
    r3 = {k: (v["agreed"] or "").strip() for k, v in rec3.items()}
    if set(r3) != set(r1):
        print("round-3 table does not cover the reconciliation cells",
              file=sys.stderr)
        return 1

    converged = {k for k in r1 if r1[k] == r2[k]}
    contradicted = [k for k in converged if r3[k] != r1[k]]
    split = sorted(set(r1) - converged)
    adopted = {"A": [], "B": [], "third": []}
    for k in split:
        tag = ("A" if r3[k] == r1[k] else
               "B" if r3[k] == r2[k] else "third")
        adopted[tag].append(k)
    changed = [k for k in split if r3[k] != r1[k]]

    with (SUP / "coding-121-final.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    by_sid = {r["sample_id"]: r for r in rows}
    for (sid, field), value in r3.items():
        by_sid[sid][field] = value
    with (SUP / "coding-121-final.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id"] + COLS)
        w.writeheader()
        for sid in sorted(by_sid):
            w.writerow({k: by_sid[sid].get(k, "")
                        for k in ["sample_id"] + COLS})

    complete = sum(1 for r in rows if all((r[c] or "").strip() for c in COLS))
    lines = [
        "reconciliation merge (round-3 joint resolution)",
        "  cells settled in round 1        : {}".format(484 - len(r1)),
        "  cells re-adjudicated            : {}".format(len(r1)),
        "    round-2 agreement confirmed   : {}".format(len(converged)),
        "    round-2 split -> adopted A    : {}".format(len(adopted["A"])),
        "    round-2 split -> adopted B    : {}".format(len(adopted["B"])),
        "    round-2 split -> third value  : {}".format(len(adopted["third"])),
        "  cells whose value changed vs the first-author fallback : {}".format(
            len(changed)),
        "  round-2 converged cells contradicted by round 3        : {}".format(
            len(contradicted)),
        "  fully coded rows                : {} / {}".format(complete, len(rows)),
    ]
    for tag in ("third",):
        for sid, field in adopted[tag]:
            lines.append("    third value: {} {} = {}".format(sid, field,
                                                             r3[(sid, field)]))
    text = "\n".join(lines)
    (OUT / "reconciliation-report.txt").write_text(text + "\n",
                                                              encoding="utf-8")
    print(text)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tie-break", default="final",
                    choices=["final", "res1", "res2", "strict"])
    args = ap.parse_args()

    rec1, rec2 = load_resolution(RES["res1"]), load_resolution(RES["res2"])
    r1 = {k: (v["agreed"] or "").strip() for k, v in rec1.items()}
    r2 = {k: (v["agreed"] or "").strip() for k, v in rec2.items()}
    if set(r1) != set(r2):
        print("resolution keys differ", file=sys.stderr)
        return 1

    if args.tie_break == "final":
        return merge_final(rec1, rec2)

    converged = {k for k in r1 if r1[k] == r2[k]}
    divergent = sorted(set(r1) - converged)

    with (SUP / "coding-121-final.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    by_sid = {r["sample_id"]: r for r in rows}
    stats = {"round1": 0, "converged": 0, "adjudicated": 0, "left_blank": 0}
    for sid, row in by_sid.items():
        for field in FIELDS:
            key = (sid, field)
            if key not in r1:
                stats["round1"] += 1
                continue
            if key in converged:
                row[field] = r1[key]
                stats["converged"] += 1
            elif args.tie_break == "strict":
                row[field] = ""
                stats["left_blank"] += 1
            else:
                row[field] = r1[key] if args.tie_break == "res1" else r2[key]
                stats["adjudicated"] += 1

    with (SUP / "coding-121-final.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id"] + COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in ["sample_id"] + COLS})

    complete = sum(1 for r in rows if all((r[c] or "").strip() for c in COLS))
    per_field = {c: sum(1 for r in rows if not (r[c] or "").strip()) for c in COLS}
    sides_a = sum(1 for k in divergent if r1[k] == rec1[k]["coder_A"].strip())
    sides_b = sum(1 for k in divergent if r2[k] == rec2[k]["coder_B"].strip())
    lines = [
        "reconciliation merge (tie-break = {})".format(args.tie_break),
        "  cells already agreed in round 1 : {}".format(stats["round1"]),
        "  disagreement cells              : {}".format(len(r1)),
        "    adopted (two adjudications agree): {}".format(stats["converged"]),
        "    settled by tie-break rule       : {}".format(stats["adjudicated"]),
        "  among the still-divergent cells  : resolution-1 restates coder A in"
        " {}, resolution-2 restates coder B in {}".format(sides_a, sides_b),
        "    left blank (strict)             : {}".format(stats["left_blank"]),
        "  fully coded rows                : {} / {}".format(complete, len(rows)),
        "  blank cells per field           : {}".format(per_field),
    ]
    text = "\n".join(lines)
    (OUT / "reconciliation-report.txt").write_text(text + "\n",
                                                              encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
