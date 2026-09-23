# -*- coding: utf-8 -*-
"""Audit the scope subsection against Appendix A and the rest of the paper.

Checks, in order:
  1. Appendix A (LaTeX + machine copy) against the final coding table;
  2. every sample cited at least once in the body, and present in ref.bib;
  3. every sample's nearest-section pointer resolves to a real \\label;
  4. category / object-type counts used by the scope discussion;
  5. category-count sentence in the Appendix A caption.

    python audit/audit_scope_appendix_consistency.py
"""
import collections
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MANUSCRIPT = ROOT / "manuscript"   # manuscript sources are not shipped in this repository
SUP = HERE


def load_coding():
    with (SUP / "coding-121-final.csv").open(newline="",
                                              encoding="utf-8-sig") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def load_appendix():
    with (SUP / "appendix-matrix-code.csv").open(newline="",
                                                 encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def plain_key(value):
    return value.replace("\\", "").strip()


def main():
    tex = (MANUSCRIPT / "article-cn.tex").read_text(encoding="utf-8")
    appendix_tex = (MANUSCRIPT / "appendix-included-studies.tex").read_text(
        encoding="utf-8")
    bib = (MANUSCRIPT / "ref.bib").read_text(encoding="utf-8")
    coding = load_coding()
    rows = load_appendix()

    cited = collections.Counter()
    for group in re.findall(r"\\cite\{([^}]*)\}", tex):
        for key in group.split(","):
            cited[key.strip()] += 1
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    labels = set(re.findall(r"\\label\{([^}]+)\}", tex))

    problems = []
    for row in rows:
        sid = row["S"]
        key = plain_key(row["BibKey"])
        if cited[key] == 0:
            problems.append(("not cited in the body", sid, key))
        if key not in bib_keys:
            problems.append(("missing from ref.bib", sid, key))
        label = re.search(r"\\ref\{([^}]+)\}", row["NearestSection"])
        if label and label.group(1) not in labels:
            problems.append(("dead section pointer", sid, label.group(1)))
        want = coding[sid]
        for col, field in (("Category", "category"),
                           ("ObjectType", "object_type"),
                           ("Mechanism", "mechanism"),
                           ("Granularity", "granularity")):
            if row[col] != want[field]:
                problems.append(("coding mismatch " + col, sid,
                                 row[col] + " vs " + want[field]))

    groups = {name: collections.Counter() for name in
              ("category", "object_type", "granularity", "mechanism")}
    for sid, row in coding.items():
        for name in groups:
            groups[name][row[name]] += 1

    print("Appendix A rows            : {}".format(len(rows)))
    print("category counts            : {}".format(dict(groups["category"])))
    print("object type counts         : {}".format(dict(groups["object_type"])))
    print("granularity counts         : {}".format(dict(groups["granularity"])))
    print("mechanism counts           : {}".format(dict(groups["mechanism"])))

    caption = re.search(r"各类计数依次为 ([0-9、]+) 篇", appendix_tex)
    if caption:
        order = ["建模", "图层", "循环层", "稀疏", "TinyML", "异构", "功耗",
                 "AI4C", "测量", "Pareto"]
        want = [groups["category"][c] for c in order]
        got = [int(v) for v in caption.group(1).split("、")]
        print("caption count sentence     : {} (expected {})".format(got, want))
        if got != want:
            problems.append(("caption counts out of date", "appendix",
                             str(got) + " vs " + str(want)))
    else:
        problems.append(("caption counts not found", "appendix", ""))

    print("")
    if not problems:
        print("no inconsistencies found")
        return 0
    print("{} problem(s):".format(len(problems)))
    for what, sid, detail in problems:
        print("   {:<26} {:<10} {}".format(what, sid, detail))
    return 1


if __name__ == "__main__":
    sys.exit(main())
