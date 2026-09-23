# -*- coding: utf-8 -*-
"""Cross-check the machine-readable coding table against the published
Appendix A LaTeX table.

Appendix A is the artifact readers can verify, so where the two disagree the
LaTeX row wins. Prints every mismatch and, with --fix, repairs the CSV.

    python audit/crosscheck_appendix.py [--fix]
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = HERE / "appendix-matrix-code.csv"
TEX = ROOT / "manuscript" / "appendix-included-studies.tex"

ROW_RE = re.compile("^(S" + r"\d" + "+)" + r"\s*&(.+?)" + r"\\\\" + r"\s*$",
                    re.M)

# Appendix A column order: ID | BibKey | 文献 | 年 | 载体 | 审 | 类别 | 节 |
# 证据类型 | 能耗 | 开源 | 对象类型 | 纳入理由
# The machine-readable table stores 开源 under the name "Open"; 审 and 能耗 are
# not mirrored there.
COL = {"BibKey": 1, "Name": 2, "Year": 3, "Venue": 4,
       "Category": 6, "NearestSection": 7, "Subtype": 8,
       "Open": 10, "ObjectType": 11}


def parse_tex():
    text = TEX.read_text(encoding="utf-8")
    rows = {}
    for m in ROW_RE.finditer(text):
        sid = m.group(1)
        parts = [p.strip() for p in m.group(2).split(" & ")]
        rec = {"S": sid}
        for key, idx in COL.items():
            rec[key] = parts[idx - 1] if idx - 1 < len(parts) else ""
        rows[sid] = rec
    return rows


def clean(v):
    v = v.replace("\\seqsplit{", "").replace("}", "")
    v = v.replace("\\&", "&").replace("\\_", "_").strip()
    return v


# Appendix A abbreviates the object-type vocabulary (see the table caption).
ABBREV = {
    "通用编译栈": "编译栈",
    "专用加速器与体系结构": "加速器",
    "测量与基准设施": "测量设施",
    "负载与模型层": "模型层",
}


def main():
    fix = "--fix" in sys.argv
    tex = parse_tex()
    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    mismatches = []
    for r in rows:
        t = tex.get(r["S"])
        if not t:
            mismatches.append((r["S"], "row", "missing in appendix"))
            continue
        for key in ("Year", "Venue", "Open", "Category", "ObjectType"):
            a, b = clean(r[key]), clean(t[key])
            if key == "ObjectType":
                a = ABBREV.get(a, a)
            if a != b:
                mismatches.append((r["S"], key, a + "  ->  " + b))
                if fix:
                    r[key] = t[key].replace("\\&", "&")
    report = ["rows in csv: {}   rows parsed from appendix: {}".format(
        len(rows), len(tex)), "mismatches: {}".format(len(mismatches))]
    for m in mismatches:
        report.append("   {} {:<14} {}".format(*m))
    text = "\n".join(report)
    # console code pages mangle CJK, so keep an ASCII summary on stdout and the
    # full report in a UTF-8 file
    print(report[0])
    print(report[1])
    (HERE / "crosscheck-report.txt").write_text(text + "\n",
                                                         encoding="utf-8")
    if fix and mismatches:
        with CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print("CSV repaired (LaTeX row wins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
