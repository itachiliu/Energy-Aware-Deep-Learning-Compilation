# -*- coding: utf-8 -*-
"""Executable form of the v2 coding rules (see coding-rubric-v2.md).

The rules map a row (Category + Subtype) to its (Granularity, Mechanism) pair.
The v1 script returned Other/Other for the six categories it had no branch for,
which is what produced 82/121 "Other" mechanisms and the low inter-coder
agreement; v2 gives every one of the ten categories an explicit branch.

Safety: since the 2026-09-21 coding merge the authoritative record is
audit/coding-121-final.csv, and the CSV mirror is written by
audit/sync_appendix_from_final.py. --write here recomputes the *old* rule-based
coding and would overwrite that merge, so it now requires --force as well.
Without --write the script only reports the 4x4 occupancy the current CSV
implies.

    python code_matrix.py            # report only
    python code_matrix.py --write --force   # legacy: recompute from v2 rules
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "appendix-matrix-code.csv"

# S-id level decisions that the authors confirmed by hand; these stay on top of
# the keyword rules.
OVERRIDES = {
    "S01": ("Loop/Op", "Analytical"),
    "S03": ("Loop/Op", "Analytical"),
    "S04": ("Loop/Op", "Analytical"),
    "S05": ("Loop/Op", "Analytical"),
    "S06": ("Loop/Op", "AutoSearch"),
    "S07": ("Loop/Op", "AutoSearch"),
    "S08": ("Graph", "Learned"),
    "S09": ("Other", "AutoSearch"),
    "S11": ("Other", "Analytical"),
    "S12": ("Graph", "Analytical"),
    "S13": ("Graph", "AutoSearch"),
    "S17": ("Graph", "Learned"),
    "S20": ("Loop/Op", "Analytical"),
    "S21": ("Loop/Op", "Analytical"),
    "S25": ("Loop/Op", "AutoSearch"),
    "S28": ("Placement", "Analytical"),
    "S29": ("Graph", "AutoSearch"),
    "S33": ("Placement", "Learned"),
    "S34": ("Placement", "Learned"),
    "S35": ("Power", "Analytical"),
    "S36": ("Power", "Learned"),
    "S38": ("Power", "AutoSearch"),
    "S40": ("Loop/Op", "AutoSearch"),
    "S47": ("Power", "AutoSearch"),
    "S48": ("Power", "AutoSearch"),
    "S52": ("Graph", "Learned"),
    "S53": ("Graph", "Analytical"),
    "S54": ("Graph", "Learned"),
    "S55": ("Loop/Op", "AutoSearch"),
    "S56": ("Loop/Op", "AutoSearch"),
    "S57": ("Loop/Op", "AutoSearch"),
    "S58": ("Graph", "AutoSearch"),
    "S60": ("Loop/Op", "Learned"),
    "S65": ("Graph", "AutoSearch"),
    "S67": ("Loop/Op", "AutoSearch"),
    "S68": ("Loop/Op", "AutoSearch"),
    "S69": ("Loop/Op", "AutoSearch"),
    "S71": ("Loop/Op", "AutoSearch"),
    "S95": ("Power", "Learned"),
    "S97": ("Power", "Analytical"),
    "S98": ("Power", "Analytical"),
}


def has(sub, *keys):
    return any(k in sub for k in keys)


def code_of(cat, sub):
    """v2 rule table: one explicit branch per category."""
    low = sub.lower()          # llm/agent 等英文关键词需大小写无关
    if cat == "建模":
        g = "Graph" if has(sub, "图", "网络模型", "层建模") else (
            "Loop/Op" if has(sub, "循环", "算子", "dataflow") else "Other")
        # 真机实测类不提出模型，记 Other（rubric 第 1 节）
        m = "Other" if has(sub, "实测", "测量") else (
            "Learned" if has(sub, "学习", "神经", "预测") else "Analytical")
    elif cat == "图层":
        g = "Graph"
        # 图级重写在重写序列上求解，默认 AutoSearch
        m = "Learned" if has(sub, "学习", "硬件反馈") else (
            "Analytical" if has(sub, "解析", "代价模型") else "AutoSearch")
    elif cat == "循环层":
        g = "Loop/Op"
        m = "Learned" if has(sub, "学习") else (
            "AutoSearch" if has(sub, "搜索", "调度", "自适应") else "Analytical")
    elif cat == "稀疏":
        g = "Graph" if has(sub, "图", "结构化", "精度") else "Loop/Op"
        m = "Learned" if has(sub, "学习") else (
            "AutoSearch" if has(sub, "搜索") else "Other")
    elif cat == "TinyML":
        g = "Graph" if has(sub, "NAS", "架构", "协同", "内存调度") else (
            "Loop/Op" if has(sub, "kernel", "库", "算子", "精度") else "Other")
        m = "Learned" if has(sub, "学习", "可微") else (
            "AutoSearch" if has(sub, "搜索", "NAS") else (
                "Analytical" if has(sub, "建模", "分析", "生命周期") else "Other"))
    elif cat == "异构":
        g = "Placement"
        m = "Learned" if has(sub, "学习", "强化") else (
            "AutoSearch" if has(sub, "搜索", "多目标", "调度") else (
                "Analytical" if has(sub, "建模", "预测", "设计空间") else "Other"))
    elif cat == "功耗":
        g = "Power"
        m = "Learned" if has(sub, "学习", "强化") else (
            "AutoSearch" if has(sub, "搜索", "优化", "编排", "规划") else (
                "Analytical" if has(sub, "建模", "仿射", "解析") else "Other"))
    elif cat == "AI4C":
        g = "Loop/Op" if has(sub, "循环", "向量化", "张量") else "Other"
        m = "Agentic" if has(low, "llm", "agent", "语言模型") else (
            "Learned" if has(sub, "学习", "强化", "表示") else "Other")
    elif cat == "测量":
        g = "Power" if has(sub, "功耗", "能耗") else "Other"
        m = "Analytical" if has(sub, "建模", "模型", "碳") else "Other"
    elif cat == "Pareto":
        g = "Loop/Op" if has(sub, "映射", "调度") else (
            "Power" if has(sub, "功耗", "频率") else (
                "Placement" if has(sub, "放置") else (
                    "Graph" if has(sub, "图") else "Other")))
        m = "Learned" if has(sub, "代理", "学习") else (
            "AutoSearch" if has(sub, "搜索", "贝叶斯", "优化") else "Analytical")
    else:
        g, m = "Other", "Other"
    return g, m


def table(rows):
    gs = ["Graph", "Loop/Op", "Placement", "Power"]
    ms = ["Analytical", "Learned", "AutoSearch", "Agentic"]
    print("{:<11}".format("Granularity") + "".join("{:>12}".format(m)
                                                   for m in ms))
    inside = 0
    for g in gs:
        counts = []
        for m in ms:
            c = sum(1 for r in rows if r["Granularity"] == g
                    and r["Mechanism"] == m)
            counts.append(c)
            inside += c
        print("{:<11}".format(g) + "".join("{:>12}".format(c) for c in counts))
    print("rows inside the matrix: {}".format(inside))
    gaps = [(g, m) for g in gs for m in ms
            if not any(r["Granularity"] == g and r["Mechanism"] == m
                       for r in rows)]
    print("empty cells: {}".format(
        ", ".join("{} x {}".format(g, m) for g, m in gaps) or "none"))


def main():
    write = "--write" in sys.argv
    if write and "--force" not in sys.argv:
        print("refusing to overwrite the merged two-coder coding; "
              "pass --force to restore the legacy rule-based coding")
        return 1
    with CSV.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())

    if write:
        for r in rows:
            sid = r["S"].strip()
            if sid in OVERRIDES:
                r["Granularity"], r["Mechanism"] = OVERRIDES[sid]
            else:
                r["Granularity"], r["Mechanism"] = code_of(
                    r["Category"], r["Subtype"] or "")
        with CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print("CSV rewritten from the v2 rules: {}".format(CSV.name))
    else:
        print("report only (pass --write to recompute {}):".format(CSV.name))

    table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
