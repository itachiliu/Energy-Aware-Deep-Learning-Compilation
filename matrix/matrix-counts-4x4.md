# 附录 A 的 4×4 矩阵计数（可入正文附录）

> 计数口径：仅统计粒度与机制均落在四类中的附录 A 样本（$n=68$）。编码取自
> `coding-121-final.csv`，即两位编码者独立编码、经复议归并后的最终版本；
> 计数脚本见 `matrix/count_matrix.py`。版本：2026-09-21。

| 粒度单元 | Analytical | Learned | AutoSearch | Agentic |
|---|---:|---:|---:|---:|
| 计算图（Graph） | 6 | 3 | 11 | 0$^{\dagger}$ |
| 循环/算子（Loop/Op） | 4 | 4 | 19 | 1 |
| 异构放置（Placement） | 2 | 3 | 5 | **0** |
| 功耗状态（Power） | 4 | 3 | 3 | **0** |

行合计：Graph 20、Loop/Op 28、Placement 10、Power 10。

空格（计数为 0 且正文无代表）：Placement × Agentic、Power × Agentic。
$^{\dagger}$ Graph × Agentic 计数为 0，但正文有非统计代表（agentic MLIR），
故不计为空格。
