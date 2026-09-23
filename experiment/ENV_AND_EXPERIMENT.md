# 实证实验：环境需求与验收清单（给平台/供应商）

> 用途：论文《能耗感知深度学习编译综述》的“最小验证实验”（正文
> `subsec:miniexperiment`）。当前 ARM64（鲲鹏）+ A100 节点无法执行任何主流 CUDA 编译栈
> （TensorRT 仅有 x86_64 版、aarch64 无 PyTorch/ONNX Runtime CUDA wheel、无容器支持），
> 因此需要按本清单提供环境。拿到环境后，实验脚本与回填模板均已就绪。

## 1. 一句话需求

一台 **x86_64 + NVIDIA GPU + 可读功耗** 的机器（或等价 SLURM 队列/容器镜像），能运行
CUDA 12.x、PyTorch(CUDA)、ONNX Runtime-GPU、TensorRT，联网 2–4 小时，跑完产出
`results.csv` 与 `summary.md`。

## 2. 硬件要求

| 项目 | 最低 | 推荐 |
|---|---|---|
| CPU 架构 | x86_64（Intel/AMD） | x86_64 |
| GPU | NVIDIA 显存 ≥ 24 GB（4090/3090/L40S） | A100-PCIe 40GB × 1 |
| 功耗接口 | `nvidia-smi --query-gpu=power.draw` 能返回数值 | 同左（整卡读数，无 MIG/vGPU 屏蔽） |
| 显存 | ≥ 24 GB（ViT-B/16 fp32 引擎 + workspace） | 40 GB |
| 磁盘 | ≥ 20 GB 可用 | 同左 |
| 时长 | 连续 2 小时 | 4 小时 |

## 3. 软件要求（任选其一）

### 方式 A：NGC PyTorch 容器（最省事，推荐）

镜像：`nvcr.io/nvidia/pytorch:24.10-py3`（或更新的 24.xx/25.xx）。
内含 CUDA 12.x、cuDNN、TensorRT、PyTorch(CUDA)。额外需要：

```bash
pip install onnxruntime-gpu==1.18.1 onnx onnxscript pynvml pandas numpy
```

### 方式 B：裸机/云主机 + conda

```text
OS: Ubuntu 20.04/22.04 x86_64（或其他 x86_64 Linux）
驱动: >= 535.104.12（nvidia-smi 可见）
CUDA: 12.2（与驱动匹配即可）
cuDNN: 8.9.x
TensorRT: >= 8.6（含 trtexec）
Python: 3.10（conda/miniforge）
pip 包: torch torchvision（+cu122/cu124，x86_64 官方源有）
        onnxruntime-gpu==1.18.1  onnx onnxscript pynvml pandas numpy
```

### 方式 C：SLURM x86 GPU 分区

需要可 `module load`：`cuda/12.x`、`cudnn/8.9.x`、`TensorRT/>=8.6`，
或提供含上述软件的 conda 环境；其余同方式 B。

## 4. 环境验收命令（拿到环境后先跑一遍）

```bash
uname -m                                             # 必须输出 x86_64
nvidia-smi --query-gpu=name,driver_version,memory.total,power.draw --format=csv   # power.draw 要有数值
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"      # True
python -c "import onnxruntime as ort; print(ort.get_available_providers())"        # 含 CUDAExecutionProvider
command -v trtexec && trtexec --help >/dev/null && echo TRT_OK                     # TensorRT 可用
python -c "import onnx, onnxscript, pynvml, pandas, numpy; print('deps OK')"
command -v ncu && echo NCU_OK                        # 可选：有 root/perf 权限时采集 DRAM 字节数
```

全部通过 → 把输出发回，我们按对应运行方式给出最终提交命令。

> 若验收时 `ncu` 可用（容器内 root 或驱动开放 perf 计数器），请同时跑：
> `ncu --metrics dram__bytes_read.sum,dram__bytes_write.sum --target-processes all <任意一次推理>`
> 能返回数值即可，DRAM 字节数将作为机理级证据写入论文。

## 4b. 实验与论文论点的对齐关系（为什么这样设计）

论文主线：FLOPs 不代理能耗（数据搬运主导）→ 专用 mapping/DSE 的能耗目标未传导进
生产级编译栈 → 测量协议不统一、缺一手数据 → OP1/OP2/OP4。

| 论文需要 | 实验构件 | 说明 |
|---|---|---|
| FLOPs 不预测能耗 | 同模型 tf32/fp32/fp16/int8（FLOPs 相同，J/inf 不同）；跨模型能效排序 vs FLOPs 排序 | MobileNetV2 FLOPs 最低，但访存占比高，未必 J/inf 最低 |
| 数据搬运主导能耗（机理） | DRAM 字节数（ncu，可选）；无计数器时用访存画像解释并声明缺失 | 有 ncu 时从现象级升级为机理级 |
| 延迟最优 ≠ 能耗最优 | 每模型内延迟最优配置 vs EDP/能耗最优配置（H2） | 直接对应“编译目标缺能耗”的断层判断 |
| 跨栈差异/未传导 | TRT(trtexec) vs ORT-CUDA vs ORT-TRT vs torch.compile | 同一模型不同栈的 J/inf 离散度 |
| 测量协议可执行 | 预热/稳态/0.1s 采样/idle 扣减/均值±std/p95/EDP | 落实第 measurement 节报告规范 |
| （可选强化）LLM 解码访存主导 | 自回归小模型单 token 解码 J/token（Level 3-opt） | 与正文 LLM 章节呼应；不做不影响核心 |

刻意不做（避免误导审稿人）：DVFS/功耗门控专项（OP4/OP5 留未来）、TVM/IREE 编译
（安装面大且非本实验必需，跨栈结论由 ORT/TRT/torch.compile 覆盖并显式声明边界）。

## 5. 实验设计（脚本已实现或即将实现）

### 5.1 模型与权重

| 模型 | 输入 | 近似 FLOPs | 访存画像 |
|---|---|---|---|
| MobileNetV2 | 224×224 | ≈0.31 G | 轻量、深度可分离卷积，访存占比高 |
| ResNet-50 | 224×224 | ≈4.1 G | 规整中型 CNN |
| ViT-B/16 | 224×224 | ≈17.6 G | Transformer，稠密 GEMM + 注意力 |

批大小 1。权重默认随机（固定种子，不影响 FLOPs/访存足迹），可选 ImageNet 预训练。

### 5.2 编译/运行栈（按“环境实际打通”逐级启用，至少跑满第一级）

| 级别 | 栈 | 配置（精度） | 说明 |
|---|---|---|---|
| 1（必跑） | TensorRT 独立（trtexec） | tf32、fp32(noTF32)、fp16、int8* | 厂商图编译器 |
| 1（必跑） | ONNX Runtime CUDA EP | fp32、fp16 | 主流部署运行时 |
| 2（推荐） | ONNX Runtime TensorRT EP | fp32、fp16 | 经 ORT 调 TRT 引擎 |
| 2（推荐） | PyTorch eager | fp32、fp16 | 框架动态执行基线 |
| 2（推荐） | PyTorch 2.x `torch.compile`(Inductor) | fp32、fp16 | 生产级编译路径（正文核心对象） |
| 3（可选） | INT8（TRT/ORT） | int8* | INT8 构建失败自动跳过并记录 |
| 3-opt（可选强化） | 小自回归 LM（如 OPT-125M 随机权重） | torch.compile fp32/fp16 | 固定 prompt 长度，单 token 解码稳态循环，报告 J/token、p95 |

`*` INT8 为尽力而为：以随机输入校准，ViT 的 LayerNorm 子图可能在旧版 TRT 失败，跳过即可。

### 5.3 测量协议（每配置）

- 引擎/图构建一次；基准运行 3 次重复 × 20 s 稳态；
- trtexec/ORT/torch 均预热 ≥2 s；功耗以 nvidia-smi 0.1 s 间隔采样，跳过进程启动前 3 s；
- 记录：GPU 型号、驱动版本、SM 时钟（当前/最大）、功率上限、温度、占用、idle 功耗；
- 输出：平均延迟与标准差、p95、吞吐(qps)、平均功率(W)、J/inf（含/扣 idle 两口径）、EDP；
- DRAM 字节数：默认无 Nsight Compute 权限，显式标注缺失；DVFS 若被锁定则声明不适用；
- 结果写入 `results.csv`（每(模型,栈,精度,重复)一行），`summary.md` 自动聚合 + H1/H2 检查。

### 5.4 假设与论文对应

- **H1（FLOPs 不代理能耗）**：同模型不同精度/内核的 J/inf 显著不同；跨模型能耗排序与
  FLOPs 排序不一致（如 MobileNetV2 未必最低）。
- **H2（延迟最优 ≠ 能耗最优）**：同模型内延迟最低配置不是 EDP/能耗最低配置。
- **H3（跨栈传导初测）**：TRT / ORT / torch.compile 对同一模型的 J/inf 差异可被精度、
  内核选择与访存画像解释——为 OP1/OP2（能耗写进编译目标）提供一手坐标。

### 5.5 时间预算（单卡）

| 方案 | 时长 |
|---|---|
| 仅 Level 1（TRT + ORT-CUDA） | 1.5–2 h |
| Level 1+2（推荐） | 2–3 h |
| Level 1+2+3（含 INT8） | 3–4 h |
| Level 1+2+3+3-opt（含 LM J/token） | 4–5 h |

> 选配建议：优先保 **Level 1+2**（2–3 h）；若环境允许 ncu 则加 DRAM 计数；
> 时间有余再跑 INT8 与 LM J/token。论文实证小节按“实际跑通并记录”的口径撰写，
> 不虚构任何配置。

## 6. 给平台/供应商的原文（可直接转发）

> 需要一台 x86_64 架构、带 NVIDIA GPU 的 Linux 环境用于深度学习推理能耗实验。
> GPU 需支持 `nvidia-smi --query-gpu=power.draw` 返回数值；显存 ≥ 24 GB（A100 40GB 最佳）。
> 软件栈要求 CUDA 12.x、cuDNN、TensorRT(≥8.6，含 trtexec)，以及 Python 3.10 环境可安装
> PyTorch(CUDA)、onnxruntime-gpu==1.18.1、onnx、onnxscript。可使用 NGC PyTorch 容器
> （nvcr.io/nvidia/pytorch:24.10-py3）或等价裸机/模块环境。单次占用 2–4 小时，需要外网
> 访问 PyPI。验收命令见上文第 4 节。
