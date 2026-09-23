# 0/18 生态表：逐系统证据载体与候选排除记录

> 数据来源：article-cn.tex 的 tab:ecosystem（L181–L200）与正文对系统的表述。
> 状态：初稿，可直接复核；标“官方仓库/文档（版本在投稿定稿时固定）”的格子需要补具体 commit/版本号。

## 1. 选取规则（已写入正文 L214 段）

截至 2026 年 5 月有正式论文或官方发布、在生态中被广泛部署或代表一类生产执行路径、
可由公开文档或源码复核。

## 2. 证据载体优先级（已写入 tab:ecosystem 表注）

论文 > 官方文档 > 公开源码；标注源码位置的条目可直接复核。

## 3. 18 个条目的逐系统证据（按表顺序）

| # | 系统/组件 | 论文/文档证据（正文 cite key） | 源码/可复核点 | 状态 |
|---|---|---|---|---|
| 1 | TVM | chen\_tvm\_2018 | 开源；正文给出 `src/auto_scheduler/measure.cc` 的 ProgramMeasurer | 已复核 |
| 2 | Ansor（TVM） | zheng\_ansor\_2020 | 同上；代价模型以延迟为默认预测目标 | 已复核 |
| 3 | TVM Unity / Relax | tvm\_unity | 官方仓库/文档 | 官方仓库/文档（版本在投稿定稿时固定） |
| 4 | TorchInductor | ansel\_pytorch\_2024 | 官方仓库/文档 | 官方仓库/文档（版本在投稿定稿时固定） |
| 5 | Triton | triton | 官方仓库 | 官方仓库/文档（版本在投稿定稿时固定） |
| 6 | XLA | openxla | 正文给出 ProfileGuidedLatencyEstimator 与 GPU Speed-of-Light 代价模型位置 | 已复核 |
| 7 | IREE | iree | 官方仓库/文档 | 官方仓库/文档（版本在投稿定稿时固定） |
| 8 | TensorRT | nvidia\_tensorrt | 闭源；官方文档 + 仓库外围组件；表注 a 说明开放范围 | 文档级 |
| 9 | TensorRT-LLM | nvidia\_trtllm | 开源仓库；执行依赖闭源 TRT 运行时（表注 a） | 已复核 |
| 10 | OpenVINO | intel\_openvino | 官方仓库/文档 | 官方仓库/文档（版本在投稿定稿时固定） |
| 11 | ONNX Runtime | onnxruntime | 官方仓库/文档 | 官方仓库/文档（版本在投稿定稿时固定） |
| 12 | TFLite / NNAPI | google\_tflite | 文档；表注 b 给出 ANEURALNETWORKS\_PREFER\_LOW\_POWER | 文档级 |
| 13 | Core ML | apple\_coreml | 文档；表注 c 给出 MLComputeUnits 枚举 | 文档级 |
| 14 | ExecuTorch | executorch | 官方仓库/文档 | 官方仓库/文档（版本在投稿定稿时固定） |
| 15 | MNN | mnn | 官方仓库 | 官方仓库/文档（版本在投稿定稿时固定） |
| 16 | NCNN | ncnn | 官方仓库 | 官方仓库/文档（版本在投稿定稿时固定） |
| 17 | Paddle Lite | paddlelite | 官方仓库 | 官方仓库/文档（版本在投稿定稿时固定） |
| 18 | MLC-LLM | mlcllm | 官方仓库（Relax + TensorIR 栈） | 官方仓库/文档（版本在投稿定稿时固定） |

## 4. 候选但未入选（依据正文可追溯项）

| 候选 | 类别/功能 | 未入选原因（正文依据） |
|---|---|---|
| vLLM 等 LLM 服务/连续批处理运行时 | 服务期调度、分页与 KV cache 管理 | 决策主体是服务期运行时，不是编译期目标函数（正文 LLM 部署与补充追踪处讨论） |
| TensorRT-LLM 服务侧优化（补充追踪部分） | 服务期运行时能力 | 正文 L311 将其归入运行时提示/服务期能力，不改变“编译期目标 vs 运行时提示”口径 |
| MileStone / AutoPass / DualScale（2026 预印本） | 窗口后趋势 | 未正式发表、不满足纳入标准；见 supplements/2026-preprint-tracking.md |
| torch.compile 的 Dynamo 前端 | 图捕获前端 | 后端决策内核由 TorchInductor 承担，Dynamo 不引入新的代价模型/目标函数 |

## 5. 结论口径（正文同步）

0/18 的范围是“本综述选取的 18 个代表性通用/生产级栈（16 个独立项目）”，不覆盖全部生产栈；
该结论不否认运行时低功耗提示的存在，也不外推到专用 mapping/DSE 工具链。
