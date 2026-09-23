# Small-scale validation experiment / 小规模验证实验

## English

This folder holds everything needed to reproduce and audit the small-scale
validation experiment of the paper.

**Design.** Hardware and frequency are fixed. The variables are compilation
decisions (the ONNX Runtime graph optimisation level, and the precision and
execution mode of PyTorch), the batch size, and the model, chosen to span
different memory-access profiles. Every configuration is measured over eight
20 s steady-state windows under one protocol.

**Coverage.** Two batches. Batch 1 runs on an NVIDIA A100-PCIe 40GB with 3
models, ORT graph optimisation levels 0/1/2/99 at batch 1 and 16, plus eager
FP32/FP16, giving 36 runnable configurations. Batch 2 runs on an RTX 4090 24 GB
and extends the same matrix to 5 models, adding `torch.compile` (Inductor), for
80 configurations.

**Hypotheses.** H1: FLOPs are not an adequate proxy for energy. H2: the
latency-optimal configuration is not necessarily the energy-optimal one. H3:
the energy difference across compilation stacks or decisions is partly explained
by precision, kernel selection and memory-access profile.

| Path | Contents |
|---|---|
| `ENV_AND_EXPERIMENT.md` | Environment, job layout and experiment log |
| `ENV_REQUIREMENTS.md` | Required packages and acceptance commands |
| `SCAN_SUPPLEMENT.md` | Supplement describing the configuration scan |
| `batch2_5models_results.csv` | Aggregated results of the second batch |
| `data/` | Raw per-run measurements, one directory per scan, plus the packed archives |
| `job/` | Self-contained job package: SLURM scripts, model export, measurement and analysis code |
| `scripts/` | Plotting scripts for Figures 10–12 |
| `scan_latex_fragment.tex` | The table fragment used in the paper |
| `README-cn.md` | The original Chinese description of the package |

**Measurement conventions.** J/inf (gross) is average power divided by
throughput and includes static power; J/inf (net) additionally subtracts the
cold idle level. Power is whole-card GPU power through NVML / `nvidia-smi`,
which excludes host CPU and memory. DRAM byte counts are not collected
first-hand because unprivileged access to the performance counters was refused
on both platforms; the relevant mechanism attribution therefore rests on
literature evidence. DVFS was locked by the provider and is not an experimental
variable.

## 中文

本目录保存复现与复核论文"小规模验证实验"一节所需的全部内容。

**设计。** 固定硬件与频率，变量为编译决策（ONNX Runtime 图优化等级、PyTorch 的
精度与执行模式）、批处理大小，以及访存画像不同的模型；每个配置按统一协议测量
8 个 20~s 稳态窗口。

**覆盖范围。** 分两批。批次一在 NVIDIA A100-PCIe 40GB 上运行 3 个模型，
ORT 图优化 0/1/2/99 × batch 1/16，外加 eager FP32/FP16，共 36 个可运行配置。
批次二在 RTX 4090 24~GB 上把同一矩阵扩到 5 个模型并加入 `torch.compile`
（Inductor），共 80 个配置。

**假设。** H1：FLOPs 不足代理能耗；H2：延迟最优配置并不必然是能耗最优配置；
H3：跨编译栈或编译决策的能耗差异可被精度、内核选择与访存画像部分解释。

| 路径 | 内容 |
|---|---|
| `ENV_AND_EXPERIMENT.md` | 环境、作业布局与实验记录 |
| `ENV_REQUIREMENTS.md` | 依赖包与验收命令 |
| `SCAN_SUPPLEMENT.md` | 配置扫描说明 |
| `batch2_5models_results.csv` | 批次二聚合结果 |
| `data/` | 逐次原始测量，每轮扫描一个目录，另附打包存档 |
| `job/` | 自包含作业包：SLURM 脚本、模型导出、测量与分析代码 |
| `scripts/` | 图 10--12 的绘图脚本 |
| `scan_latex_fragment.tex` | 正文使用的表格片段 |
| `README-cn.md` | 作业包最初的完整中文说明 |

**测量口径。** J/inf（gross）为平均功耗除以吞吐，含静态功耗；J/inf（net）另扣除
冷态 idle。功耗为 GPU 整卡（NVML / `nvidia-smi`），不含主机 CPU 与内存。
两代平台均拒绝非特权进程访问性能计数器，故 DRAM 字节数未纳入一手采集，相关机制
归因以文献证据为主。DVFS 由服务商锁定，不作为实验变量。
