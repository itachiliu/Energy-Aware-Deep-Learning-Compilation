# -*- coding: utf-8 -*-
"""Recount the 4x4 granularity x mechanism matrix from the final coding.

Reads coding/coding-121-final.csv, prints the counts and rewrites
matrix/matrix-counts-4x4.md.

    python matrix/count_matrix.py
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CODING = ROOT / "coding"
GRAN = ["Graph", "Loop/Op", "Placement", "Power"]
MECH = ["Analytical", "Learned", "AutoSearch", "Agentic"]
LABEL = {"Graph": "计算图（Graph）", "Loop/Op": "循环/算子（Loop/Op）",
         "Placement": "异构放置（Placement）", "Power": "功耗状态（Power）"}


def main():
    with (CODING / "coding-121-final.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    grid = {(g, m): 0 for g in GRAN for m in MECH}
    for r in rows:
        if r["granularity"] in GRAN and r["mechanism"] in MECH:
            grid[(r["granularity"], r["mechanism"])] += 1
    n = sum(grid.values())

    lines = [
        "# 附录 A 的 4×4 矩阵计数（可入正文附录）",
        "",
        "> 计数口径：仅统计粒度与机制均落在四类中的附录 A 样本（$n={}$）。编码取自"
        .format(n),
        "> `coding-121-final.csv`，即两位编码者独立编码、经复议归并后的最终版本；",
        "> 计数脚本见 `matrix/count_matrix.py`。版本：2026-09-21。",
        "",
        "| 粒度单元 | " + " | ".join(MECH) + " |",
        "|---|" + "---:|" * len(MECH),
    ]
    for g in GRAN:
        cells = []
        for m in MECH:
            v = grid[(g, m)]
            if v == 0:
                cells.append("**0**" if (g, m) != ("Graph", "Agentic")
                             else "0$^{\\dagger}$")
            else:
                cells.append(str(v))
        lines.append("| {} | {} |".format(LABEL[g], " | ".join(cells)))
    lines += [
        "",
        "行合计：" + "、".join(
            "{} {}".format(g, sum(grid[(g, m)] for m in MECH)) for g in GRAN) + "。",
        "",
        "空格（计数为 0 且正文无代表）：Placement × Agentic、Power × Agentic。",
        "$^{\\dagger}$ Graph × Agentic 计数为 0，但正文有非统计代表（agentic MLIR），",
        "故不计为空格。",
        "",
    ]
    (HERE / "matrix-counts-4x4.md").write_text("\n".join(lines), encoding="utf-8")

    print("n =", n)
    print("      " + " ".join("{:>11}".format(m) for m in MECH))
    for g in GRAN:
        print("{:>10}".format(g),
              " ".join("{:>11}".format(grid[(g, m)]) for m in MECH))
    print("wrote matrix/matrix-counts-4x4.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
