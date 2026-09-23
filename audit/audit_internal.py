# -*- coding: utf-8 -*-
"""Internal consistency audit: heuristic codes (with S overrides) vs the
default (category, subtype) rule. Highlights every row where the explicit
S-override changed the default; the reviewer can inspect those decisions.

This is NOT a substitute for a human independent coder; it is a reproducibility
and transparency check to be run before asking a human to fill the 30-row
sample.
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
CSV = ROOT / "appendix-matrix-code.csv"


def default_code(cat, sub):
    sub = sub or ""
    if cat == "图层":
        g = "Graph"
        m = ("Learned" if ("学习" in sub or "硬件反馈" in sub)
             else ("AutoSearch" if ("ILP" in sub or "搜索" in sub) else "Other"))
    elif cat == "循环层":
        g = "Loop/Op"
        m = ("AutoSearch" if ("自动调度" in sub or "自适应搜索" in sub or "搜索" in sub)
             else ("Analytical" if ("解析" in sub or "dataflow" in sub) else "Other"))
    elif cat == "异构":
        g = "Placement"
        m = ("Learned" if ("学习" in sub or "预测" in sub)
             else ("AutoSearch" if ("多目标" in sub or "搜索" in sub) else "Other"))
    elif cat == "功耗":
        g = "Power"
        m = ("Analytical" if ("建模" in sub or "仿射" in sub)
             else ("AutoSearch" if ("优化" in sub or "编排" in sub) else "Other"))
    else:
        g, m = "Other", "Other"
    return g, m


def main():
    rows = []
    with open(CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    diffs = []
    for r in rows:
        dg, dm = default_code(r["Category"], r["Subtype"])
        if dg != r["Granularity"] or dm != r["Mechanism"]:
            diffs.append((r["S"], r["BibKey"], r["Category"], r["Subtype"],
                          f"{dg} x {dm}", f"{r['Granularity']} x {r['Mechanism']}"))
    print(f"rows={len(rows)} override-changed={len(diffs)}")
    for d in diffs:
        print(f"{d[0]} {d[1]} | {d[2]} | {d[3]} | default={d[4]} -> final={d[5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
