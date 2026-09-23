# Coding of the 121 included studies / 121 篇纳入文献的编码

## English

This folder holds the complete coding pipeline for the 121 studies in the
statistical sample: the controlled vocabulary, both coders' independent sheets,
the disagreement list, the reconciliation records, the third-round adjudication
package and the final merged table.

The coded fields are **category**, **granularity**, **mechanism** and
**object type**. Both coders worked independently from the same published
manual; units fixed by the worked-example sheets are excluded from the
agreement statistics.

| File | Role |
|---|---|
| `coding-rubric-v2.md`, `coding-rubric-v3.md` | The controlled vocabulary and decision rules, v2 and the extended v3 |
| `codebook-v2-worked-examples.csv`, `codebook-v3-worked-examples.csv` | Worked examples that fix the vocabulary |
| `coding-sheet-A-v2.csv`, `coding-sheet-A-v3.csv` | Coder A, first-round independent coding |
| `coding-sheet-B-v2.csv`, `coding-sheet-B-v3.csv` | Coder B, first-round independent coding |
| `reconciliation-sheet.csv` | The 96 disagreeing units |
| `reconciliation-resolution-1-full.csv`, `reconciliation-resolution-2.csv` | The two per-unit reconciliation rounds |
| `reconciliation-resolution-final.txt` | The single authoritative resolution table covering all 96 units |
| `adjudication-round3-guide.md`, `adjudication-round3-rules.csv`, `adjudication-round3-coder-A.csv`, `-coder-B.csv` | Third-round criterion-first adjudication package |
| `coding-121-final.csv` | **Final coding**, the source of truth for Appendix A and every count in the paper |
| `kappa/` | κ computation, reconciliation merge and appendix synchronisation scripts with their reports |

Agreement of the first independent round, using the standard two-coder Cohen's κ:

| Field | N | Agreement | κ |
|---|---|---|---|
| Category | 118 | 79.7% | 0.77 |
| Granularity | 118 | 74.6% | 0.66 |
| Mechanism | 114 | 73.7% | 0.65 |
| Object type | 118 | 89.8% | 0.85 |

Integrity: the first-round sheets are preserved unmodified. Reconciliation and
adjudication results live in separate files.

## 中文

本目录保存统计样本 121 篇文献的完整编码流水线：受控词表、两位编码者的独立
编码表、争议清单、复议记录、第三轮裁定包，以及最终归并表。

编码字段为**类别**、**粒度**、**机制**、**对象类型**四项。两位编码者依据同一份
公开手册独立完成；示例表所固定的单元不计入一致性统计。

| 文件 | 作用 |
|---|---|
| `coding-rubric-v2.md`、`coding-rubric-v3.md` | 受控词表与判据，v2 及扩充后的 v3 |
| `codebook-v2-worked-examples.csv`、`codebook-v3-worked-examples.csv` | 固定词表口径的示例 |
| `coding-sheet-A-v2.csv`、`coding-sheet-A-v3.csv` | 编码者 A 第一轮独立编码 |
| `coding-sheet-B-v2.csv`、`coding-sheet-B-v3.csv` | 编码者 B 第一轮独立编码 |
| `reconciliation-sheet.csv` | 96 个不一致单元清单 |
| `reconciliation-resolution-1-full.csv`、`reconciliation-resolution-2.csv` | 两轮逐单元复议记录 |
| `reconciliation-resolution-final.txt` | 覆盖全部 96 个单元的唯一权威决议表 |
| `adjudication-round3-*.md/.csv` | 第三轮"先定判据、再落单元"裁定包 |
| `coding-121-final.csv` | **最终编码**，附录 A 与正文全部计数的唯一来源 |
| `kappa/` | κ 计算、复议归并与附录同步脚本及其报告 |

第一轮独立编码的标准两人 Cohen's κ：类别 0.77、粒度 0.66、机制 0.65、
对象类型 0.85。诚实性：第一轮编码表不作修改，复议与裁定结果一律另存。
