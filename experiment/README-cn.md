# 最小验证实验包（Path B：TensorRT 版，对应正文 \ref{subsec:miniexperiment}）

目标平台：天玑智算云 **A100-PCIe 40GB × 1**（鲲鹏 920 ARM64 / 麒麟 V10 / 驱动
535.104.12，无 root）。

平台不提供 PyTorch/ONNX Runtime 的 aarch64 CUDA wheel，也不支持自定义容器镜像，
因此本包只走 **TensorRT 8.5.3.1（CUDA 11.8/cuDNN 8.6）+ trtexec + nvidia-smi 功耗采样**
这一条可打通的 CUDA 链路（Path B）。比较主轴从“跨编译栈”收敛为
“**同一 TensorRT 图编译栈内的编译决策（TF32/FP32/FP16/INT8）× 跨模型访存画像**”，
并保留对 H1/H2 的检验；跨栈（TVM/IREE/ONNX Runtime）对比作为受平台限制的未来工作，
正文已同步改写。

## 目录

```text
miniexperiment/
├── README.md            # 本说明
├── job/                 # 自包含作业包（唯一需要上传的部分）
└── models/              # 3 个 ONNX（可选；不上传则让集群用 CPU torch 导出）
    ├── mobilenetv2.onnx
    ├── resnet50.onnx
    └── vit_b_16.onnx
```

## 1. 本地导出 ONNX（可选，推荐先本地导出再上传）

需要 Python ≥ 3.10 与 CPU 版 torch/torchvision/onnx（Windows 下可用
`pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`）：

```bash
python job/fetch_models.py --out models --opset 13 --size 224
```

默认随机初始化权重（固定种子）：本实验测量的是编译产物的延迟与能耗，取决于算子构成、
张量形状与访存足迹，与权重数值无关；若需 ImageNet 权重，加 `--pretrained`（需联网）。
导出规格：batch=1、224×224、opset 13——后两者是为 TensorRT 8.5 的 ONNX 解析兼容性
与静态形状构建选的。

## 2. 集群端运行

把 `job/`（及可选的 `models/`）上传到登录节点后：

```bash
cd ~
sbatch job/job.slurm          # models/ 已上传时
# 或先让集群导出模型：
# sbatch job/export_models.slurm
```

详细步骤、环境变量与常见问题见 `job/README_job.md`。

## 3. 输出与回填

作业生成 `experiment_out_<时间戳>/results.csv`（每(模型,精度,重复)一行）与
`summary.md`（聚合表 + H1/H2 快速检查）。回传这两个文件后，把结果填入论文
`\ref{subsec:miniexperiment}` 一节（表 + 1–2 段实证分析），并把本目录移出投稿工作区。

## 4. 测量口径与已知边界

- J/inf(总) = 平均功耗 / 吞吐（含静态）；J/inf(净) 额外扣除 idle 功耗，两者都报告；
- 功耗为 GPU 整卡（NVML/nvidia-smi 软件接口），不含主机 CPU/内存；云端无法外接功率计；
- DVFS 由服务商锁定，不作为实验变量；thermal throttling 以 nvidia-smi 当前/最大 SM 时钟核对；
- DRAM 访问字节数：平台未授予 Nsight Compute 计数器权限，显式标注缺失；
- INT8 为尽力而为（随机输入校准），构建失败（如 ViT 的 LayerNorm 子图）自动跳过并记录；
- 主机为 ARM64 只影响“可用运行时”的选择，不影响 GPU 端结论的作用域声明。
