# 附录编码内部一致性审计（非人类独立复核）

> **2026-09-21 状态更新。**本文件记录的是**单编码者阶段**的规则式编码
> （`appendix-matrix-code.csv` 由 `code_matrix.py` 从类别与子类规则生成）。
> 该阶段的编码已被两人独立编码 + 复议归并的结果取代，最终编码见
> `coding-121-final.csv`，附录镜像由 `repro/sync_appendix_from_final.py` 写入。
> 下方“23 行由 S 级覆盖改变默认规则”只对该历史阶段成立；当前若再用
> `code_matrix.py` 复算，差异行数为 87，这正是规则式编码与人工编码不一致的度量。

> 运行：`python supplements/audit_internal.py`。
> 说明：这是“显式 S 级覆盖 vs (类别,子类) 默认规则”的差异清单，供审稿人检查
> 每处人工裁决是否有正文依据。它**不是**第三方独立编码的替代品。

结果：121 行中 23 行由 S 级覆盖改变了默认规则；其余 98 行与默认规则一致。

覆盖分类：

1. **建模类跨切到 Loop/Op（S01/S03–S09/S11/S52–S60 等）**：这些工作虽属“能耗与代价建模”，
   但正文定位是对循环/映射/调度做能耗估计，按正文口径放入 Loop/Op 行；
2. **Graph 行机制（S12 WELDER→Analytical、S13 TASO→AutoSearch、
   S17 HAQ→Learned）**：见 matrix-empty-cells.md 的裁决理由；
3. **Placement/Power 行（S28、S29、S35–S40、S95–S98 等）**：见裁决表。

需要人工重点复核的是第 1 类中“模型所服务的粒度”判断，尤其 S11（roofline 概念）、
S52–S54（网络结构级能耗预测是否应算 Loop/Op）、S57（Mind Mappings）。

## 与投稿的关系

- 正文已写明空格判定依据附录编码，脚本与差异清单作为补充材料；
- 如果期刊接受“作者双编码 + 公开 rubric + 可复跑脚本”，当前透明度和可复核性已达到
  一般综述要求；
- 如果审稿人要求非作者抽查，再把 `coding-audit-sample30.csv` 交给第三方填录并跑
  `audit_coding.py` 输出 κ。
