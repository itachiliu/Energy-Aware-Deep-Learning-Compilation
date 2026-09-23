# -*- coding: utf-8 -*-
"""Push the merged two-coder coding into Appendix A and its machine copy.

The authoritative record is supplements/coding-121-final.csv (round-1 agreed
cells + codebook cells + reconciled cells, see merge_reconciliation.py). This
script mirrors it into supplements/appendix-matrix-code.csv (machine copy,
where ObjectType replaces the retired boundary label) and into the published
Appendix A longtable appendix-included-studies.tex (类别 / 节 / 对象类型).

    python repro/sync_appendix_from_final.py            # report only
    python repro/sync_appendix_from_final.py --write    # rewrite both
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
CSV = ROOT / "audit" / "appendix-matrix-code.csv"
TEX = ROOT / "manuscript" / "appendix-included-studies.tex"  # manuscript sources are not shipped in this repository
ROW = re.compile(r"^(S\d+)\s*&(.+?)\\\\\s*$", re.M)
SECTION = {
    "建模": r"\S\ref{sec:modeling}",
    "图层": r"\S\ref{sec:graph}",
    "循环层": r"\S\ref{sec:loop}",
    "稀疏": r"\S\ref{sec:loop}",
    "异构": r"\S\ref{sec:hetero}",
    "TinyML": r"\S\ref{sec:open}",
    "功耗": r"\S\ref{sec:power}",
    "AI4C": r"\S\ref{sec:ai4c}",
    "测量": r"\S\ref{sec:measurement}",
    "Pareto": r"\S\ref{sec:pareto}",
}
SYNONYM = {"放置": "异构", "边缘": "TinyML"}
# Appendix A is set in a landscape longtable; the coded vocabulary is spelled
# out in the caption and abbreviated in the cells so the column stays narrow.
TEX_OBJECT = {
    "通用编译栈": "编译栈",
    "专用加速器与体系结构": "加速器",
    "测量与基准设施": "测量设施",
    "负载与模型层": "模型层",
}


def main():
    write = "--write" in sys.argv
    with (SUP / "coding-121-final.csv").open(newline="", encoding="utf-8-sig") as f:
        final = {r["sample_id"]: r for r in csv.DictReader(f)}
    cols = ["category", "object_type", "granularity", "mechanism"]
    missing = [sid for sid, v in final.items()
               if not all((v[c] or "").strip() for c in cols)]
    if missing:
        print("final coding incomplete for: {}".format(", ".join(sorted(missing))))
        return 1

    with CSV.open(newline="", encoding="utf-8-sig") as f:
        csv_rows = list(csv.DictReader(f))
    with TEX.open(encoding="utf-8") as f:
        tex = f.read()

    cat_delta, tex_rows = [], dict(ROW.findall(tex))
    if set(tex_rows) != {r["S"] for r in csv_rows}:
        print("appendix rows and CSV disagree on which samples exist")
        return 1

    for r in csv_rows:
        f = final[r["S"]]
        old_cat = SYNONYM.get(r["Category"], r["Category"])
        if old_cat != f["category"]:
            cat_delta.append((r["S"], old_cat, f["category"]))
        r["Category"] = f["category"]
        r["NearestSection"] = SECTION[f["category"]]
        r["Mechanism"] = f["mechanism"]
        r["Granularity"] = f["granularity"]
        r.pop("Boundary", None)
        r["ObjectType"] = f["object_type"]

    def fix(match):
        sid, body = match.group(1), match.group(2)
        parts = [p.strip() for p in body.split(" & ")]
        if len(parts) != 12:
            raise SystemExit("row {} has {} fields".format(sid, len(parts) + 1))
        f = final[sid]
        parts[5] = f["category"]
        parts[6] = SECTION[f["category"]]
        parts[10] = TEX_OBJECT[f["object_type"]]
        return "{} & {} \\\\".format(sid, " & ".join(parts))

    new_tex = ROW.sub(fix, tex)

    print("category cells changed in Appendix A : {}".format(len(cat_delta)))
    for sid, old, new in cat_delta:
        print("   {} {} -> {}".format(sid, old, new))
    print("object type column rewritten        : 121 rows")
    if not write:
        print("\n(dry run; pass --write to update both files)")
        return 0

    fields = ["S", "BibKey", "Name", "Year", "Venue", "Category",
              "NearestSection", "Subtype", "Open", "ObjectType",
              "Mechanism", "Granularity"]
    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in csv_rows:
            w.writerow({k: r.get(k, "") for k in fields})
    TEX.write_text(new_tex, encoding="utf-8")
    print("\nupdated supplements/appendix-matrix-code.csv and "
          "appendix-included-studies.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
