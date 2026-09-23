# 补充实验环境需求（可直接转给平台工程师）

> 目标：补齐论文实验的四个缺口：
> ① ViT-B/16 的 ONNX 正常导出（不再用手写 attention 替换）；
> ② torch.compile（Inductor）或 TensorRT 至少打通一条编译路径；
> ③ DRAM 访存字节计数（ncu/CUPTI）；
> ④ 与现有 A100 批次同口径的可复现运行环境。

## 一句话需求

一台 **x86_64 + NVIDIA GPU + 可读功耗 + 开放性能计数器** 的机器（裸机/容器均可），
能运行 CUDA 12.x、PyTorch（CUDA）≥2.1、ONNX Runtime-GPU、TensorRT ≥8.6，
并允许运行 Nsight Compute 采集 DRAM 计数；无 root 时请预先放开计数器权限。

## 硬件要求

| 项目 | 最低 | 推荐 |
|---|---|---|
| CPU 架构 | x86_64 | x86_64 |
| GPU | NVIDIA，显存 ≥ 24 GB（4090/3090/L40S） | A100-PCIe 40GB × 1 |
| 功耗接口 | `nvidia-smi --query-gpu=power.draw` 返回数值 | 同左 |
| 性能计数器 | 可运行 `ncu` 采集 dram 字节 | NVreg_RestrictProfilingAdminUsers=0 或等价权限 |
| 磁盘 | ≥ 20 GB | 同左 |
| 时长 | 连续 4 小时 | 8 小时 |

## 软件要求（任选其一）

### 方式 A：NGC PyTorch 容器（最省事）

```text
镜像: nvcr.io/nvidia/pytorch:24.10-py3（或更新）
自带: CUDA 12.x, cuDNN, TensorRT, PyTorch(CUDA), Nsight Compute
补充安装:
  pip install onnxruntime-gpu==1.18.1 onnx onnxscript pynvml pandas numpy
```

### 方式 B：x86_64 裸机 + conda

```text
OS: Ubuntu 20.04/22.04 x86_64
驱动: ≥ 535.104.12（nvidia-smi 可读功耗）
CUDA: 12.2
cuDNN: 8.9.x
TensorRT: ≥ 8.6（含 trtexec）
Python: 3.10（conda/miniforge）
pip: torch>=2.1 torchvision（cu122/cu124 官方源）
     onnxruntime-gpu==1.18.1 onnx onnxscript pynvml pandas numpy
Nsight Compute: 与驱动匹配的 ncu
```

### 方式 C：SLURM x86 GPU 分区

```text
可 module load: cuda/12.x, cudnn/8.9.x, TensorRT>=8.6, miniforge3
作业节点需满足：nvidia-smi power.draw 可读；ncu 权限放开；单卡独占（无 MIG）
```

## 验收命令（拿到环境后先跑）

```bash
uname -m                                # 必须 x86_64
nvidia-smi --query-gpu=name,driver_version,memory.total,power.draw --format=csv
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"     # ≥2.1, True
python -c "import onnxruntime as ort; print(ort.get_available_providers())"       # 含 CUDA
command -v trtexec && trtexec --help >/dev/null && echo TRT_OK
python -c "import torch; m=torch.nn.Linear(8,8).eval();
import torchvision.models as M; v=M.vit_b_16(weights=None).eval();
import io
b=io.BytesIO(); torch.onnx.export(v, torch.zeros(1,3,224,224), b,
  dynamic_axes={'input':{0:'batch'}}, opset_version=17); print('ViT ONNX export OK')"
command -v ncu && ncu --version
ncu --metrics dram__bytes_read.sum,dram__bytes_write.sum --target-processes all \
    python -c "print(1)"     # 能返回非 0 的 dram 计数即权限已放开
```

## 与现有 ARM64 A100 批次的关系

- 现有 36 配置批次（aarch64 + cp310cu122 + ORT CUDA + torch eager）作为“批次一”；
- 新环境用于补跑三组对照：ViT 正常 ONNX 导出后的 ORT 结果（替代 attention 替换版）、
  TensorRT 或 torch.compile 至少一条编译路径、以及同一批配置的 ncu DRAM 字节计数；
- 两组数据在论文中以“批次一/批次二”区分，不混用绝对 J/inf 数字，只比相对结构。

## 验收后回传

```text
uname -m / nvidia-smi / torch / ort / trtexec / ncu 输出
ViT ONNX 正常导出确认输出
ncu dram 计数非 0 确认输出
```
