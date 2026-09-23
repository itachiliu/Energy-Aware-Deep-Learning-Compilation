# -*- coding: utf-8 -*-
"""Build the round-3 adjudication pack for the 65 cells still split after the
second reconciliation round.

Round 2 showed that deciding cell by cell reproduces the round-1 positions:
all 65 remaining splits have resolution-1 equal to coder A's round-1 value and
63 of 65 have resolution-2 equal to coder B's. Round 3 therefore asks the two
coders to decide the *rule* first (one ballot row per recurring conflict) and
only then apply it to the cells. The pack contains:

  supplements/adjudication-round3-guide.md        instructions + cell map
  supplements/adjudication-round3-rules.csv       rule ballot (13 recurr. rows)
  supplements/adjudication-round3-coder-A.csv     cell sheet, coder A
  supplements/adjudication-round3-coder-B.csv     cell sheet, coder B
  supplements/adjudication-round3-singles.csv     one-off cells (no rule at stake)

    python repro/make_adjudication3_sheets.py
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent          # repository root
SUP = HERE.parent                  # ../  = coding/ , where the coding data live
OUT = HERE                         # reports are written next to this script
FIELDS = ["category", "granularity", "mechanism", "object_type"]

# rule_id, field, question, opt1 label, opt1 value, opt2 label, opt2 value,
# cells, rubric clause
RULES = [
    ("R1", "category",
     "逐层位宽指派、混合精度与张量分解内存优化类工作，归入哪一类？",
     "图层：精度指派属图级重写", "图层",
     "Pareto：核心是精度与效率的多目标权衡", "Pareto",
     "S17 S18 S19", "§3 类别裁决表：图层 vs Pareto"),
    ("R2", "category",
     "面向多加速器映射/层切分的设计空间探索，归入哪一类？",
     "异构：决策是层到加速器的分配", "异构",
     "Pareto：核心是吞吐/能耗等多目标权衡", "Pareto",
     "S22 S29", "§3 类别裁决表：异构 vs Pareto"),
    ("R3", "category",
     "以学习/搜索模块服务张量调度的工作，是否因学习组件改记 AI4C？",
     "循环层：学习组件不改类别，主体是调度搜索", "循环层",
     "AI4C：主体是学习型编译方法", "AI4C",
     "S25 S68", "§3：循环层 vs AI4C（现无对应行，需新增）"),
    ("R4", "category",
     "把映射与调度写成约束优化并求解的工作，归入哪一类？",
     "循环层：贡献是映射/调度的求解", "循环层",
     "Pareto：贡献是前沿遍历与权衡", "Pareto",
     "S56 S57", "§3 类别裁决表：循环层 vs Pareto"),
    ("R5", "granularity",
     "作用于编译器 pass 序列、IR 或源码级改写的决策，其粒度记什么？",
     "Other：pass 与 IR 级决策不落四类粒度", "Other",
     "Loop/Op：按代码/算子层变换计", "Loop/Op",
     "S41 S42 S43 S45 S46 S78 S85 S86 S106 S108",
     "§2 粒度定义 / §1 粒度 Other 判据"),
    ("R6", "granularity",
     "对象是权重、通道结构、完整网络架构或训练过程的工作，其粒度记什么？",
     "Other：对象不是编译产物，不属四类粒度", "Other",
     "Graph：模型图/结构决策即图级", "Graph",
     "S79 S80 S81 S82 S89 S91 S92", "§2 粒度定义 / §1 粒度 Other 判据"),
    ("R7", "granularity",
     "稀疏格式与稀疏表示基础设施（生成单算子迭代代码），其粒度记什么？",
     "Loop/Op：产出单算子迭代代码", "Loop/Op",
     "Other：表示基础设施本身不作决策", "Other",
     "S74 S76", "§2 粒度定义（稀疏编译基础设施）"),
    ("R8", "mechanism",
     "以解析模型或规则驱动、一次性定位或启发式编排的方法，机制记什么？",
     "Analytical：白盒模型/规则直接给出决策", "Analytical",
     "AutoSearch：只要存在候选空间与评估即记搜索", "AutoSearch",
     "S15 S18 S19 S30 S32 S64 S66 S90 S102",
     "§1-§2 + v3 M1（M1 需补“以是否在候选空间中迭代评估为准”）"),
    ("R9", "mechanism",
     "搜索框架内部的学习模块，其机制记什么？",
     "AutoSearch：学习模块服务于搜索框架", "AutoSearch",
     "Learned：贡献本身是可复用的学习型模型/策略", "Learned",
     "S46 S68 S80", "§1-§2 + v3 M1/M2"),
    ("R10", "object_type",
     "架构级功耗/能耗模型（GPU 功耗模型、DVFS 延迟模型），依附对象记什么？",
     "测量与基准设施：产出是可迁移的建模方法", "测量与基准设施",
     "专用加速器与体系结构：模型依附特定架构", "专用加速器与体系结构",
     "S35 S97 S98", "v3 一、对象类型"),
    ("R11", "object_type",
     "以编译器 pass 实现、但决策对象偏模型层的方法，对象类型记什么？",
     "通用编译栈：方法学贡献依附编译栈", "通用编译栈",
     "负载与模型层：决策对象是模型/负载", "负载与模型层",
     "S18 S93", "v3 一、对象类型"),
    ("R12", "object_type",
     "面向特定平台的生产级 kernel 库或运行时框架，对象类型记什么？",
     "通用编译栈：面向商用 ISA 的生产级实现", "通用编译栈",
     "专用加速器与体系结构：绑定定制 ISA/硬件", "专用加速器与体系结构",
     "S37 S86", "v3 一、对象类型（现无手工 kernel 库桶，需新增）"),
]


def load(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return {(r["sample_id"], r["field"]): r for r in csv.DictReader(f)}


def main():
    res1 = load(SUP / "reconciliation-resolution-1-full.csv")
    res2 = load(SUP / "reconciliation-resolution-2.csv")
    split = sorted(k for k in res1
                   if (res1[k]["agreed"] or "").strip()
                   != (res2[k]["agreed"] or "").strip())

    rule_of, rows = {}, []
    for r in RULES:
        for sid in r[7].split():
            key = (sid, r[1])
            rule_of[key] = r[0]
            # the ballot must present the two options in the same order as the
            # coder sheets (option_1 = resolution-1 = round-1 coder A value)
            got = ((res1[key]["agreed"] or "").strip(),
                   (res2[key]["agreed"] or "").strip())
            if got != (r[4], r[6]):
                raise SystemExit("{} {}: ballot options {} but round-2 split is {}"
                                 .format(sid, r[1], (r[4], r[6]), got))

    singles = []
    for k in split:
        sid, field = k
        rec = {"sample_id": sid, "field": field,
               "option_A": (res1[k]["agreed"] or "").strip(),
               "option_B": (res2[k]["agreed"] or "").strip(),
               "rule_id": rule_of.get(k, ""), "round3": ""}
        rows.append(rec)
        if not rec["rule_id"]:
            singles.append(rec)

    for name in ("A", "B"):
        out = SUP / "adjudication-round3-coder-{}.csv".format(name)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["sample_id", "field", "option_A",
                                              "option_B", "rule_id", "round3"])
            w.writeheader()
            w.writerows(rows)

    with (SUP / "adjudication-round3-rules.csv").open(
            "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["rule_id", "field", "question", "option_1", "value_1",
                    "option_2", "value_2", "cells", "rubric_clause",
                    "coder_A_rule", "coder_B_rule", "adopted"])
        for r in RULES:
            w.writerow(list(r) + ["", "", ""])

    with (SUP / "adjudication-round3-singles.csv").open(
            "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "field", "option_A", "option_B",
                    "resolution_1_note"])
        for rec in singles:
            note = res1[(rec["sample_id"], rec["field"])]["note"]
            w.writerow([rec["sample_id"], rec["field"], rec["option_A"],
                        rec["option_B"], note])

    # ---- guide -----------------------------------------------------------
    per_field = {}
    for rec in rows:
        per_field.setdefault(rec["field"], []).append(rec)
    guide = [
        "# 第三轮裁定包（编码者间 65 个未收敛单元）",
        "",
        "## 给两位编码者的导语（可直接转发）",
        "",
        "上一轮我们对 96 个争议单元逐条复议，结果只收敛了 31 个，剩下的 65 个里，"
        "两份复议基本是把各自第一轮的取值又写了一遍。所以这一轮换个做法：先请两位各自"
        "对 `adjudication-round3-rules.csv` 里的 12 条复现性冲突给出选项，这些冲突覆盖"
        "65 个单元中的 47 个；然后再填 `adjudication-round3-coder-A.csv` 与 "
        "`adjudication-round3-coder-B.csv` 的 `round3` 列，填写时请与自己在规则表里的"
        "选择保持一致。两人先各自填，不要互相参照，回收后由脚本核对规则是否一致、"
        "单元选择是否与规则冲突。剩下 18 个单元没有一般规则可言，按个案判断。",
        "",
        "## 为什么要改成“先定判据、再落单元”",
        "",
        "第二轮复议采用逐单元裁定，结果 96 个争议单元只收敛 31 个。核查显示，"
        "在仍未收敛的 65 个单元里，复议表 1 的取值**全部**等于编码者 A 第一轮的取值，"
        "复议表 2 有 63 个等于编码者 B 第一轮的取值。也就是说，逐单元复议基本是"
        "各自立场的复述，没有形成可复用的判据。因此本轮改两步走：",
        "",
        "1. 先对 `adjudication-round3-rules.csv` 中的 12 条**复现性冲突**各自给出"
        "选项（这些冲突覆盖 47 个单元，占 65 个中的七成）；",
        "2. 再对 `adjudication-round3-coder-{A,B}.csv` 中全部 65 个单元填 `round3` 列，"
        "填的时候要求与第 1 步的规则选择一致；",
        "3. 两份规则表若一致，`repro/apply_adjudication3.py` 会检查每个单元的选择是否"
        "与该规则蕴含的取值一致，不一致的单元直接报出来复核。",
        "",
        "没有一般规则可言的 18 个单例单元在 `adjudication-round3-singles.csv` 中"
        "列出（含复议 1 的理由注记，供查阅），但它们同样填在 A/B 表的 `round3` 列里，"
        "按个案逐条裁定。",
        "",
        "## 规则表决表包含的 12 条复现性冲突",
        "",
        "| 规则 | 字段 | 冲突 | 涉及单元数 | 单元 |",
        "|---|---|---|---:|---|",
    ]
    for r in RULES:
        guide.append("| {} | {} | {} -> {} | {} | {} |".format(
            r[0], r[1], r[4], r[6], len(r[7].split()), r[7]))
    guide += [
        "",
        "## 单例单元（无一般规则，逐条裁定）",
        "",
        "| 单元 | 字段 | 复议 1 | 复议 2 |",
        "|---|---|---|---|",
    ]
    for rec in singles:
        guide.append("| {} | {} | {} | {} |".format(
            rec["sample_id"], rec["field"], rec["option_A"], rec["option_B"]))
    guide += [
        "",
        "## 填写与回收",
        "",
        "```bash",
        "# 回收后：校验规则一致性、写入最终编码并刷新附录与计数",
        "python repro/apply_adjudication3.py              # 只报告分歧",
        "python repro/apply_adjudication3.py --write      # 写入 coding-121-final.csv",
        "python repro/sync_appendix_from_final.py --write",
        "python repro/count_matrix.py",
        "```",
        "",
        "两位编码者填表时不要互相参照；规则表决表可各自先填，再比对。"
        "分歧单元若本轮仍不收敛，则按 `apply_adjudication3.py --write` "
        "的报告保留现状（第一作者裁定）并在正文按残余模糊性披露。",
        "",
    ]
    (SUP / "adjudication-round3-guide.md").write_text("\n".join(guide),
                                                      encoding="utf-8")

    print("split cells             : {}".format(len(rows)))
    print("covered by a rule       : {}".format(len(rows) - len(singles)))
    print("one-off cells           : {}".format(len(singles)))
    print("wrote adjudication-round3-{guide.md,rules.csv,coder-A.csv,"
          "coder-B.csv,singles.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
