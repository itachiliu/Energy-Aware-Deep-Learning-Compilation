# Evidence for the 0/18 result / 0/18 结果的证据

## English

Table 2 of the paper compares 18 representative general-purpose and
production-grade compilation and deployment stacks (16 independent projects)
against a single criterion: whether an energy, power or EDP term enters the
compile-time objective function, the search criterion or a pass decision.
None of the 18 does, which is the **0/18** result.

`ecosystem-selection.md` records, for every row, the evidence hierarchy used
(paper > official documentation > public source code), the exact documentation
or source location that can be checked, the position on runtime low-power
preferences versus compile-time objectives, and the candidates that were
considered and excluded. Excluded candidates include vLLM-style serving-time
continuous batching runtimes, 2026 preprints, and the Dynamo front end of
`torch.compile`.

The control group is the dedicated mapping and DSE toolchain: 6 of 6 write
energy, power or EDP directly into the search objective.

## 中文

论文表 2 用同一判据对照 18 个代表性通用/生产级编译与部署栈（16 个独立项目）：
energy/power/EDP 是否进入编译期目标函数、搜索准则或 pass 决策。18 个条目无一满足，
即 **0/18**。

`ecosystem-selection.md` 逐条记录了打标依据的优先级（论文 > 官方文档 > 公开源码）、
可直接复核的文档或源码位置、运行时长时低功耗偏好与编译期目标的区分，以及考虑过
但未入选的候选（vLLM 一类服务期连续批处理运行时、2026 预印本、`torch.compile` 的
Dynamo 前端等）。

对照组为专用 mapping / DSE 工具链：6 项中 6 项把 energy/power/EDP 直接写入搜索目标。
