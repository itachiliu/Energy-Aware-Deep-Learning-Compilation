# 二维矩阵占用与空格

> 2026-09-21 更新：编码已改为两位编码者独立编码 + 两轮复议 + 第三轮联合裁定的口径，
> 最终决议表见 `reconciliation-resolution-final.txt`，最终编码见
> `coding-121-final.csv`，计数见 `matrix-counts-4x4.md`。本节第 1 节的六条裁决
> 属于单编码者阶段的历史记录，保留以说明争议条目的正文依据；第 2、3 节已按新口径
> 重算。

## 1. 最终裁决的 6 个易争议条目

| S | 工作 | 裁决（Granularity × Mechanism） | 理由（正文定位） |
|---|---|---|---|
| S12 | WELDER | Graph × Analytical | 图/张量级 tile-graph 以跨内存层数据流量解析模型为核心（第 IV-A 节） |
| S17 | HAQ | Graph × Learned | 逐层位宽策略由硬件反馈学习得出（图层量化小节） |
| S65 | Checkmate | Graph × AutoSearch | 以整数规划在重物化与内存之间搜索（峰值内存小节） |
| S58 | Stream | Loop/Op × Analytical | 细粒度调度模型，面向 multi-core 映射/调度（mapping/DSE 线） |
| S29 | ODiMO | Placement × AutoSearch | 在层粒度分区放置上以线性规划在能耗约束下求解（第 VI 节） |
| S38 | PowerFlow-DNN | Power × AutoSearch | 编译期 DVFS/门控编排，受截止期约束求解并做状态空间剪枝（第 VII 节） |

## 2. 附录统计口径 4×4 计数（coding-121-final.csv，n=68）

| 粒度单元 | Analytical | Learned | AutoSearch | Agentic |
|---|---:|---:|---:|---:|
| 计算图（Graph） | 6 | 3 | 11 | 0 |
| 循环/算子（Loop/Op） | 4 | 4 | 19 | 1 |
| 异构放置（Placement） | 2 | 3 | 5 | 0 |
| 功耗状态（Power） | 4 | 3 | 3 | 0 |

## 3. 最终空格判定（附录 + 正文双口径）

| 单元格 | 附录计数 | 正文代表 | 最终判定 |
|---|---|---|---|
| Graph × Agentic | 0 | Agentic MLIR（未入统计） | 非空格 |
| Loop/Op × Agentic | 1 | LLM-Vectorizer（已入统计） | 非空格 |
| Placement × Agentic | 0 | 无 | **空格** |
| Power × Learned | 3 | — | 非空格 |
| Power × Agentic | 0 | 无 | **空格** |

## 4. 备注

- AI4C 工作在正文中是“跨粒度 × 决策机制”的横切存在，不适合硬塞进 4×4 单格。
- 复跑入口：`python repro/count_matrix.py`；最终编码的生成见
  `repro/merge_reconciliation.py`，同步到附录见 `repro/sync_appendix_from_final.py`。
- `supplements/code_matrix.py` 与 `internal-audit.md` 记录的是单编码者阶段的规则式
  编码，仅作历史留痕，不再驱动正文计数。
