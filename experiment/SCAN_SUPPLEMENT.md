# 编译决策空间扫描（补充实验包）

本包与 `job/` 原有脚本同目录，复用同一套 `power.py` 功耗采样与测量协议，
把实验从“9 个 batch=1 配置”扩展为“编译决策维度 × 批处理”扫描。

## 新增文件

```text
job/
├── export_scan_models.py    # 动态 batch 的 ONNX 导出（供 ORT batch 1/16）
├── measure_ort_scan.py      # ORT CUDA EP：batch × 图优化等级 × intra-op 线程
├── measure_torch_scan.py    # PyTorch eager：batch × fp32/fp16
├── run_scan_all.py          # 矩阵调度（写 results_scan.csv）
├── summarize_scan.py        # 聚合 + H2 快速检查 + 图优化极差（写 summary_scan.md）
├── scan.slurm               # 提交入口
└── scan_entrypoint.sh       # preflight / 模块 / 模型导出 / 汇总
```

## 默认矩阵（与正文主线对齐）

| 维度 | 取值 |
|---|---|
| 模型 | MobileNetV2、ResNet-50、ViT-B/16（`EXTRA_MODELS=1` 加 ResNet-18、MobileNetV3-Large） |
| ORT CUDA EP | fp32，图优化等级 0/1/2/99（disable/basic/extended/all）× batch 1/16 |
| PyTorch eager | fp32/fp16 × batch 1/16 |
| 重复 | 8 个 20 s 稳态窗口/配置 |

默认 3 模型 = 24 个 ORT 配置 + 12 个 eager 配置，约 2 小时；开
`EXTRA_MODELS=1` 后约 3–3.5 小时。

## 提交

```bash
# 在登录节点，job/ 目录里已包含本包
cd ~
bash -n job/scan_entrypoint.sh && echo OK
sbatch job/scan.slurm
squeue -u $USER
```

环境变量覆盖：

```bash
REPS=8 BATCHES=1,16 GRAPH_OPTS=0,1,2,99 EXTRA_MODELS=0 sbatch job/scan.slurm
```

输出在 `~/scan_out_<时间戳>/`：

```text
results_scan.csv        # 每 (模型,后端,精度,batch,图优化,重复) 一行
results_scan_agg.csv    # 跨重复聚合
summary_scan.md         # 汇总表 + H2 检查 + ORT 图优化极差
logs/                   # 逐配置日志与 failures.txt
env/snapshot.txt
```

## 口径说明（写论文时保持一致）

- 一个“推理单元”= 一次 batch 调用；`J/inf` 与 EDP 均按 batch 调用计算，
  跨 batch 比较时在正文中明确该口径（并可用 `÷batch` 换算到单样本）。
- `J/inf(净)` 扣除测量前冷态 idle；`static%` = idle/平均功耗。
- DRAM 字节计数仍受 `ERR_NVGPUCTRPERM` 限制时，不硬凑，正文以
  延迟/J/inf/EDP/占用率的相对变化为证据。

## 与正文的对应

| 结果 | 论文位置 |
|---|---|
| ORT 图优化等级对延迟/J/inf 的影响 | 第 IV 节图层优化（融合/布局同向性） |
| batch 对 J/inf 与 static% 的影响 | 测量协议节 gross/net 口径与主机开销讨论 |
| 同一模型×batch 内延迟最优与能耗最优是否一致 | 实验小节 H2（分歧频率） |
| 跨配置 (latency, J/inf) Pareto 前沿 | 第 VII 节 Pareto 范式 / OP4 |
| 跨模型 FLOPs 排序 vs J/inf 排序 | 实验小节 H1 |

## 回填步骤

1. 回传 `scan_out_<时间戳>/`（或 `results_scan.csv + summary_scan.md`）。
2. 本地据此填充 `scan_latex_fragment.tex` 中的表与数字，替换正文
   “9 个可运行配置”等旧口径表述。
3. 数据核对脚本会校验：配置数=预期、无空能耗列、跨重复非零方差、
   H2 判定与 summary 一致。
