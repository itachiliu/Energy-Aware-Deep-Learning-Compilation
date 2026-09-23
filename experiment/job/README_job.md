# 智算云作业提交说明（Path B：TensorRT + trtexec + nvidia-smi）

> 平台限制：ARM64（鲲鹏 920 / 麒麟 V10）、无 root、无 PyTorch CUDA wheel、
> 无 onnxruntime-gpu wheel、不支持自定义容器镜像。因此本包不再尝试装 torch/onnxruntime
> 的 CUDA 运行时，只用平台提供的 **TensorRT 8.5.3.1（cuda11.8-cudnn8.6）** 做引擎构建，
> 用 **trtexec** 做基准，用 **nvidia-smi** 采样 GPU 功耗。

## 1. 上传

把 `job/` 整个目录上传到登录节点家目录，并（推荐）把本地导出的 ONNX 模型一并上传：

```text
~/
├── job/
│   ├── entrypoint.sh
│   ├── export_models.sh          # 模型缺失时的导出入口（需联网装 CPU torch）
│   ├── export_models.slurm       # 单独导出模型用
│   ├── fetch_models.py           # torch.onnx 导出脚本（opset 13, batch 1）
│   ├── run_trt.py                # TensorRT 独立测量（trtexec）
│   ├── run_all.py                # 多后端总调度（TRT/ORT/torch 自动探测）
│   ├── measure_onnx.py           # ONNX Runtime CUDA/TensorRT EP 测量
│   ├── measure_torch.py          # PyTorch eager / torch.compile 测量
│   ├── power.py                  # nvidia-smi 采样器
│   ├── summarize.py
│   ├── job.slurm
│   ├── diag_env.sh
│   └── README_job.md
└── models/                        # 3 个 .onnx（若本地已导出）
    ├── mobilenetv2.onnx
    ├── resnet50.onnx
    └── vit_b_16.onnx
```

## 2. 提交前自检

```bash
cd ~
bash -n job/entrypoint.sh && echo "syntax OK"
ls job/run_trt.py job/summarize.py job/power.py >/dev/null && echo "files OK"
module avail 2>&1 | grep -iE "tensorrt|cuda/11.8|cudnn/8.6"   # 确认模块存在
squeue -u $USER     # 若有积压的旧作业，先 scancel 再提新的，避免互相抢卡
```

## 3. 提交

### 3a. 模型已上传（推荐，最快）

```bash
cd ~
sbatch job/job.slurm
squeue -u $USER
```

### 3b. 模型没上传，让集群自己导出（需联网下载 CPU torch）

```bash
cd ~
sbatch job/export_models.slurm        # 导出到 ~/models
# 等这个作业结束后：
sbatch job/job.slurm
```

或在一个作业里“缺模型则导出”：

```bash
cd ~ && EXPORT_MODELS=1 sbatch job/job.slurm
```

### 3c. 交互式 GPU 节点直接跑

```bash
cd ~ && bash job/entrypoint.sh
```

## 4. 输出

```text
~/experiment_out_<时间戳>/
├── results.csv          # 每(模型,精度,重复)一行
├── summary.md           # 聚合表 + H1/H2 快速检查
├── engines/             # TensorRT engine（mobilenetv2-tf32.engine 等）
├── logs/                # build_*/bench_* 逐配置日志、failures.txt
└── env/                 # 驱动/CUDA/模块快照
~/experiment_out_<时间戳>.tar.gz
```

回传 `results.csv` 与 `summary.md`（或整个 tar.gz）即可。

## 5. 默认矩阵与耗时

模型：MobileNetV2 / ResNet-50 / ViT-B/16（224×224，batch=1，随机权重）。
`run_all.py` 自动探测节点上可用的后端并逐级执行：

| 后端 | 精度 | 说明 |
|---|---|---|
| TensorRT 独立（trtexec） | tf32 / fp32(noTF32) / fp16 / int8 | int8 失败自动跳过 |
| ONNX Runtime CUDA EP | fp32 | 部署型运行时基线 |
| ONNX Runtime TensorRT EP | fp32 / fp16 | 需要 onnxruntime 提供 TensorrtExecutionProvider |
| PyTorch eager | fp32 / fp16 | torchvision 随机权重 |
| PyTorch torch.compile | fp32 / fp16 | Inductor 编译路径 |

每配置：3 次重复 × 20 s 稳态窗口（预热在重复前完成，功耗 0.1 s 间隔采样）。
预计总耗时：仅 TRT/ORT 约 1.5–2 h；含 torch.compile 约 2.5–4 h。

## 6. 常用开关（环境变量）

| 变量 | 作用 |
|---|---|
| `OUT_DIR=/path` | 指定输出目录 |
| `MODEL_DIR=/path` | 指定 ONNX 目录（默认 `$(pwd)/models`） |
| `PRECISIONS=tf32,fp32,fp16,int8` | 直接运行 `run_trt.py` 时覆盖其精度矩阵；`run_all.py` 使用固定多后端矩阵 |
| `REPS=3` | 每配置重复次数 |
| `DURATION_MS=20000` | 每次稳态测量时长 |
| `MINIFORGE_MODULE=miniforge3/26.3.2-3` | miniforge 模块 |
| `CMAKE_MODULE=cmake/3.26.3` | cmake 模块 |
| `GCC_MODULE=compilers/gcc/11.3.0` | gcc 模块 |
| `CUDA_MODULE=compilers/cuda/12.2` | CUDA 模块（默认优先 12.2） |
| `CUDNN_MODULE=cudnn/8.9.5.29_cuda12.x` | cuDNN 模块（默认优先 8.9/cuda12.x） |
| `TRT_MODULE=TensorRT/...` | TensorRT 模块（可选；缺失时 TRT 后端自动跳过） |
| `TRTEXEC=/path/to/trtexec` | 直接指定 trtexec（找不到模块时用） |
| `PYTHON=/path/to/python` | 直接指定 Python ≥ 3.8 |
| `CONDA_ENV_NAME=cp310cu122` | 平台 CUDA conda 环境（默认 `cp310cu122`） |
| `CONDA_CREATE=1` | 仅当确需新建 CPU 环境时启用自动创建 |
| `EXPORT_MODELS=1` | 模型缺失时自动用 CPU torch 导出 |
| `PRETRAINED=1` | 导出时下载 ImageNet 权重（默认随机权重） |

## 7. 常见问题

- **`ERROR: trtexec not found`**：`module avail | grep -i tensorrt` 看模块名，提交时加
  `TRT_MODULE=<名称>`；或 `module load` 后 `which trtexec`，把路径设成 `TRTEXEC=...`。
- **模块加载告警（WARN）**：入口会依次尝试多个候选名；告警不影响继续，只要 `trtexec`
  能找到。全部失败时按上一条处理。
- **int8 构建失败**：某些模型（尤其 ViT 的 LayerNorm/Softmax 子图）在 TRT 8.5 的 INT8
  下可能不支持，属预期，日志 `logs/build_vit_b_16_int8.log` 会写明原因；结果表不含该行。
- **功耗列全空**：平台未开放功率读数或 `nvidia-smi -i <idx>` 被限制，如实保留空列并在论文中声明。
- **重复作业积压**：提交前 `squeue -u $USER`，用 `scancel <jobid>` 取消旧任务。
- **`sbatch` 报内存超额**：平台每卡默认 55GB，禁止显式 `--mem`，本包未申请；若你改过，
  删掉 `#SBATCH --mem` 行。
- **需要更多内存/避免排队**：按平台规则 `--gres=gpu:N` 增加卡数而非加 `--mem`。

## 8. 与论文的关系

本包对应正文《一个可执行的小规模验证实验》：报告 J/inference（含/扣 idle 两口径）、p95、
EDP、平均功耗与吞吐；用“同模型不同精度/内核”检验 FLOPs 不代理能耗（H1）与
延迟最优≠能耗最优（H2）；单栈（TensorRT）内编译决策的能耗差异为 H3 提供一手坐标。
DRAM 字节数因平台无 Nsight Compute 权限而缺失，正文已作显式边界声明。
