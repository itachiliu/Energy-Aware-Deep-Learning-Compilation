# 第三轮裁定包（编码者间 65 个未收敛单元）

## 给两位编码者的导语（可直接转发）

上一轮我们对 96 个争议单元逐条复议，结果只收敛了 31 个，剩下的 65 个里，两份复议基本是把各自第一轮的取值又写了一遍。所以这一轮换个做法：先请两位各自对 `adjudication-round3-rules.csv` 里的 12 条复现性冲突给出选项，这些冲突覆盖65 个单元中的 47 个；然后再填 `adjudication-round3-coder-A.csv` 与 `adjudication-round3-coder-B.csv` 的 `round3` 列，填写时请与自己在规则表里的选择保持一致。两人先各自填，不要互相参照，回收后由脚本核对规则是否一致、单元选择是否与规则冲突。剩下 18 个单元没有一般规则可言，按个案判断。

## 为什么要改成“先定判据、再落单元”

第二轮复议采用逐单元裁定，结果 96 个争议单元只收敛 31 个。核查显示，在仍未收敛的 65 个单元里，复议表 1 的取值**全部**等于编码者 A 第一轮的取值，复议表 2 有 63 个等于编码者 B 第一轮的取值。也就是说，逐单元复议基本是各自立场的复述，没有形成可复用的判据。因此本轮改两步走：

1. 先对 `adjudication-round3-rules.csv` 中的 12 条**复现性冲突**各自给出选项（这些冲突覆盖 47 个单元，占 65 个中的七成）；
2. 再对 `adjudication-round3-coder-{A,B}.csv` 中全部 65 个单元填 `round3` 列，填的时候要求与第 1 步的规则选择一致；
3. 两份规则表若一致，`repro/apply_adjudication3.py` 会检查每个单元的选择是否与该规则蕴含的取值一致，不一致的单元直接报出来复核。

没有一般规则可言的 18 个单例单元在 `adjudication-round3-singles.csv` 中列出（含复议 1 的理由注记，供查阅），但它们同样填在 A/B 表的 `round3` 列里，按个案逐条裁定。

## 规则表决表包含的 12 条复现性冲突

| 规则 | 字段 | 冲突 | 涉及单元数 | 单元 |
|---|---|---|---:|---|
| R1 | category | 图层 -> Pareto | 3 | S17 S18 S19 |
| R2 | category | 异构 -> Pareto | 2 | S22 S29 |
| R3 | category | 循环层 -> AI4C | 2 | S25 S68 |
| R4 | category | 循环层 -> Pareto | 2 | S56 S57 |
| R5 | granularity | Other -> Loop/Op | 10 | S41 S42 S43 S45 S46 S78 S85 S86 S106 S108 |
| R6 | granularity | Other -> Graph | 7 | S79 S80 S81 S82 S89 S91 S92 |
| R7 | granularity | Loop/Op -> Other | 2 | S74 S76 |
| R8 | mechanism | Analytical -> AutoSearch | 9 | S15 S18 S19 S30 S32 S64 S66 S90 S102 |
| R9 | mechanism | AutoSearch -> Learned | 3 | S46 S68 S80 |
| R10 | object_type | 测量与基准设施 -> 专用加速器与体系结构 | 3 | S35 S97 S98 |
| R11 | object_type | 通用编译栈 -> 负载与模型层 | 2 | S18 S93 |
| R12 | object_type | 通用编译栈 -> 专用加速器与体系结构 | 2 | S37 S86 |

## 单例单元（无一般规则，逐条裁定）

| 单元 | 字段 | 复议 1 | 复议 2 |
|---|---|---|---|
| S01 | granularity | Other | Graph |
| S02 | object_type | 专用加速器与体系结构 | 测量与基准设施 |
| S118 | category | 建模 | 测量 |
| S118 | mechanism | Analytical | Other |
| S120 | category | Pareto | 功耗 |
| S120 | granularity | Graph | Power |
| S21 | category | 循环层 | 建模 |
| S58 | category | 异构 | 建模 |
| S58 | granularity | Placement | Loop/Op |
| S59 | mechanism | Learned | Other |
| S64 | category | 图层 | 循环层 |
| S64 | granularity | Graph | Loop/Op |
| S77 | object_type | 专用加速器与体系结构 | 通用编译栈 |
| S79 | mechanism | Other | Learned |
| S81 | mechanism | Other | Analytical |
| S84 | mechanism | AutoSearch | Analytical |
| S90 | category | TinyML | Pareto |
| S91 | category | TinyML | 稀疏 |

## 填写与回收

```bash
# 回收后：校验规则一致性、写入最终编码并刷新附录与计数
python repro/apply_adjudication3.py              # 只报告分歧
python repro/apply_adjudication3.py --write      # 写入 coding-121-final.csv
python repro/sync_appendix_from_final.py --write
python repro/count_matrix.py
```

两位编码者填表时不要互相参照；规则表决表可各自先填，再比对。分歧单元若本轮仍不收敛，则按 `apply_adjudication3.py --write` 的报告保留现状（第一作者裁定）并在正文按残余模糊性披露。
