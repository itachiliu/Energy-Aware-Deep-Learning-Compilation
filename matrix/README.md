# 4×4 matrix counts and empty cells / 4×4 矩阵计数与空格

## English

The survey's organising skeleton is a two-dimensional matrix: optimisation
granularity (Graph, Loop/Op, Placement, Power) against decision mechanism
(Analytical, Learned, AutoSearch, Agentic). Only Appendix A samples whose
granularity and mechanism both fall inside those four values are counted
(n = 68).

| Granularity | Analytical | Learned | AutoSearch | Agentic |
|---|---|---|---|---|
| Graph | 6 | 3 | 11 | 0 |
| Loop / operator | 4 | 4 | 19 | 1 |
| Heterogeneous placement | 2 | 3 | 5 | 0 |
| Power state | 4 | 3 | 3 | 0 |

Row totals: Graph 20, Loop/Op 28, Placement 10, Power 10.

Empty cells are cells with an Appendix count of zero and no representative in
the text: **Placement × Agentic** and **Power × Agentic**. Graph × Agentic also
counts zero but is treated as non-empty because a non-statistical
representative, Agentic MLIR, is discussed in the text.

| File | Role |
|---|---|
| `matrix-counts-4x4.md`, `matrix-counts-4x4.tex` | The counts in the two formats used by the paper |
| `matrix-empty-cells.md` | Determination of the empty cells and the six most contestable entries |
| `count_matrix.py` | Recomputes the counts from `coding/coding-121-final.csv` |

## 中文

本文的组织骨架是一个二维矩阵：优化粒度（Graph、Loop/Op、Placement、Power）
× 决策机制（Analytical、Learned、AutoSearch、Agentic）。仅统计粒度与机制均落在
四类中的附录 A 样本（n = 68）。

行合计：Graph 20、Loop/Op 28、Placement 10、Power 10。

空格判定为"附录计数为 0 且正文无代表"：**Placement × Agentic** 与
**Power × Agentic**。Graph × Agentic 计数同为 0，但正文讨论了非统计代表
Agentic MLIR，故不记为空格。

| 文件 | 作用 |
|---|---|
| `matrix-counts-4x4.md`、`.tex` | 论文使用的两种格式的计数表 |
| `matrix-empty-cells.md` | 空格判定与六处最易争议条目的依据 |
| `count_matrix.py` | 由 `coding/coding-121-final.csv` 重算计数 |
