# x86 批次（RTX 4090 / 5090）操作说明

对应正文 `subsec:miniexperiment` 的“批次二”。x86 节点能补上 ARM64 批次的三个缺口：
真实 ViT-B/16 的 ONNX 导出、一条生产级编译路径、以及 DRAM 访存计数。

## 本机实测结论（2026-09-11 首次探测）

节点 `wqd10nba07g5`，Ubuntu 22.04.5，x86_64，驱动 580.82.07。
`NVIDIA GeForce RTX 4090`，24 GB 显存，功耗可读（空闲 17 W，上限 450 W），compute capability 8.9。

| 项目 | 结果 | 对实验的影响 |
|---|---|---|
| 模块名 | `miniforge3/26.3.2-3`、`gcc/11.3.0`、`cuda/12.8` 可用 | 脚本的候选列表已按实测名字排好 |
| cuDNN | 实际是 `cudnn/8.9.6.50_cuda12`、`cudnn/9.6.0.74_cuda12`（不是 `_cuda12.x`） | 候选列表已补上这两个名字 |
| TensorRT | **没有任何 TRT 模块**（10.x / 8.x 全试过，均失败） | TRT 阶段保持关闭，编译路径改走 `torch.compile`（Inductor） |
| Nsight Compute | 存在，`/data/apps/cuda/12.8/bin/ncu`，可执行 | 探测脚本已改成用真实 CUDA kernel 复测 DRAM 计数权限 |
| conda | base 在共享目录 `/data/apps/...`，家目录下尚无环境 | 建环境用 venv 路线，绕开 conda 求解 |

TRT 缺失不影响主线：正文要证的“生产级编译栈默认目标是延迟”里，**TorchInductor 本身就是
0/18 表中的一员**，用它做编译路径的实证比 TRT 更贴题。

## 上传

把整个 `job/` 目录上传到集群家目录（`~/job/`），模型不用上传，作业里会自己导出。

## 三步走

### 第 1 步：确认 GPU 分区

本集群按型号分区，提交时必须显式指定：

| 分区 | 显卡 | 架构 | 需要环境 |
|---|---|---|---|
| `gpu_4090` | RTX 4090 | sm_89 | `dlxvenv`（cu124 + ORT 1.18.1），默认 |
| `gpu_3090` | RTX 3090 | sm_86 | 同上 |
| `gpu_5090` | RTX 5090 | sm_120 | 另建（cu128 + 最新 ORT） |

两个 slurm 文件里默认已写 `gpu_4090`，换卡用 `-p` 覆盖：
`sbatch -p gpu_5090 job/scan_x86.slurm`。先用 4090 跑通整批。

### 第 2 步：建环境（登录节点，约 5–10 分钟）

```bash
module load miniforge3/26.3.2-3
bash job/setup_env_venv.sh
```

这条路线用模块自带的 python 建 venv，不做 conda 求解，所以不会再出现“卡在 create env”。
它会装 cu124 的 torch/torchvision、`onnxruntime-gpu==1.18.1`、onnx/onnxscript、pynvml。
结束时打印一行 `PYTHON=/data/home/<你的账号>/dlxvenv/bin/python`，记住它。

要装到别处或换框架版本：

```bash
VENV_DIR=~/myenv bash job/setup_env_venv.sh
TORCH_INDEX=https://download.pytorch.org/whl/cu128 VENV_DIR=~/dlx5090 bash job/setup_env_venv.sh
PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple bash job/setup_env_venv.sh   # 非 torch 包走国内镜像
```

（老的 `setup_env_x86.sh` 走 conda，仍保留作为备选；`conda` 求解慢或卡住时不用它。）

### 第 3 步：先探测，再跑正式实验

```bash
sbatch job/probe_x86.slurm        # 默认 gpu_4090，约 2–3 分钟
cat ~/slurm-<JOBID>-probe.out
```

这次要看四处：

| 看哪里 | 期望 |
|---|---|
| `arch=` | `x86_64` |
| `power_readable_w=` | 数值，不是 `N/A` |
| `[5b/8] ncu DRAM-counter test` | 出现 `dram__bytes_read.sum` 的数值行 → DRAM 计数可用 |
| `[6/8] python interpreters` | venv 路径下有 `torch ... cuda_ok True` 和 `ort ... CUDAExecutionProvider` |

探测通过后跑正式矩阵：

```bash
PYTHON=~/dlxvenv/bin/python sbatch job/scan_x86.slurm
```

不写 `PYTHON=` 也行，入口脚本会自动在 `~/dlxvenv/bin/python` 找。

时间预算（`REPS=8`、`DURATION_S=20`、`BATCHES=1,16`、含 Inductor 阶段）：约 2–2.5 小时。

冒烟测试（先确认能跑通再上正式档）：

```bash
REPS=2 DURATION_S=8 EXTRA_MODELS=0 PYTHON=~/dlxvenv/bin/python sbatch job/scan_x86.slurm
```

## 后端矩阵

作业默认跑三组，同一个 `results_scan.csv` 里按 `backend` 列区分：

| backend | 配置 |
|---|---|
| `ort-cuda` | fp32 × 图优化等级 0/1/2/99 × batch 1/16 |
| `torch-eager` | fp32/fp16 × batch 1/16 |
| `torch-compile` | fp32/fp16 × batch 1/16，Inductor（编译耗时单独记录在日志里，不计入测量窗口） |

TensorRT 阶段默认关闭（本集群无 TRT 模块）；假如以后接上了，用
`ENABLE_TRT=1 sbatch job/scan_x86.slurm` 打开，它会另写 `results_trt.csv`。

## 结果在哪

作业生成 `scan_x86_out_<时间戳>/`：

```text
results_scan.csv        # 每 (模型,后端,精度,batch,图优化,重复) 一行
results_scan_agg.csv    # 跨重复聚合
summary_scan.md         # 汇总表 + H2（延迟最优≠能耗最优）检查
logs/                   # 每个配置一条日志
env/snapshot.txt        # 主机/驱动/功耗上限快照
results_trt.csv         # 仅 ENABLE_TRT=1 时生成
```

回传 `results_scan.csv + summary_scan.md`（或整个目录）即可。

## 与 ARM64 批次的关系

| | 批次一（已有） | 批次二（本目录） |
|---|---|---|
| 机器 | 鲲鹏 920 ARM64 + A100-PCIE-40GB | x86_64 + RTX 4090 |
| 后端 | ORT-CUDA + torch eager | 加 torch.compile（Inductor） |
| ViT | 手写 attention 替换的 ONNX | 优先真实 ViT-B/16 |
| DRAM 计数 | 无权限，标注缺失 | 视 ncu 权限而定 |

两批数据在正文里以“批次一/批次二”分开陈述，只比相对结构，不混用绝对 J/inf 数值。

## 常见问题

- **`module load` 名字不对**：探测输出会打印哪个模块成功，用
  `MINIFORGE_MODULE=` / `CUDA_MODULE=` / `CUDNN_MODULE=` / `TRT_MODULE=` 固定下来。
- **不要写 `--cpus-per-task` 或 `--mem`**：本集群按卡配比固定分配（4090 = 1卡/6核/60GB），
  超额申请会被拒。
- **计算节点不通网**：装环境必须在登录节点；作业里没有任何下载动作（模型用随机权重导出）。
- **登录节点禁止跑作业**：探测和矩阵都走 `sbatch`，查看用 `parajobs`，取消用 `scancel <id>`。
- **5090 上跑 4090 的环境会报 no kernel image**：5090 需要另行建 cu128 的环境。

## 建环境卡住（只有走 conda 时才会遇到）

venv 路线不会有这个问题。若坚持用 `setup_env_x86.sh`：

```bash
du -sh ~/.conda/envs/dlx ; sleep 20 ; du -sh ~/.conda/envs/dlx   # 变大=在下载
tail -f setup_logs/setup_env_*.log
ps -u $USER -o pid,etime,cmd | grep -Ei 'conda|mamba' | grep -v grep
```

包缓存增长就等着；十分钟毫无变化且
`curl -sI --max-time 10 https://conda.anaconda.org/conda-forge/noarch/repodata.json` 超时，
就是登录节点出网有问题，直接改走 venv 路线。中途 Ctrl-C 过的话，先
`conda env remove -n dlx` 再重跑，避免把半成品当成好环境。

## 磁盘配额不足（Errno 122 Disk quota exceeded）

CUDA 版 torch 装完约 5 GB（torch 本体 + 一组 `nvidia-*` 运行时库），
如果 pip 还开着 wheel 缓存，占用会翻倍，很容易顶到家目录配额。
脚本默认已经带 `--no-cache-dir`，所以先清掉历史缓存再重跑：

```bash
du -sh ~/.cache/pip ~/dlxvenv 2>/dev/null     # 看是谁占的
rm -rf ~/.cache/pip                            # pip 缓存可随时重建，删掉最划算
df -h ~ ; quota -s 2>/dev/null                 # 看还剩多少额度
PIP_NO_CACHE=1 bash job/setup_env_venv.sh      # 重跑（已装好的包不会重复下载）
```

如果家目录配额本身就不够（例如只有 5–10 GB），把环境放到空间更大的挂载点：

```bash
df -h | grep -v tmpfs                          # 找一个 Avail 大的目录
VENV_DIR=/data/<你的可用目录>/dlxvenv PIP_NO_CACHE=1 bash job/setup_env_venv.sh
```

建好后记下新路径，提交作业时用它：

```bash
PYTHON=/data/<你的可用目录>/dlxvenv/bin/python sbatch job/scan_x86.slurm
```

实在没有余量，也可以找工程师把家目录配额提上去，或者申请一个临时工作目录
（典型需求口径：x86 计算节点可用、≥15 GB、作业运行期间可写）。

其它可以顺手清的东西：`~/.cache/torchinductor`、`~/.cache/triton`、
`setup_logs/`、以及跑完后不再需要的 `probe_out_*` 与 `scan_x86_out_*`。

## CPU 回退：数据看起来正常，其实全跑在 CPU 上

2026-09-13 那批（`scan_x86_out_20260913_200246`）13 个配置全部是这种情况：
功耗停在 19.7–20.4 W（就是 4090 的闲时功耗），延迟却是 250 ms 到 34 s。
对照批次一，A100 上 MobileNetV2 b1 是 1.73 ms @ 81 W——慢了 360 倍且完全不耗 GPU。

**判定特征**：`mean_power_w` 与 `idle_power_w` 几乎相等。作业内部的实际原因是
ONNX Runtime 的 CUDA EP 初始化失败后**静默回退**到 `CPUExecutionProvider`，
于是 CPU 推理把 6 小时墙钟耗尽，只跑完 13 个配置就被砍掉。

用这两条命令自查任何一批结果：

```bash
python analyze_x86_batch.py scan_x86_out_*/results_scan.csv
# 会打印 power sanity 段落，并列出所有"功耗≈闲时功耗"的可疑配置
```

**已加的防护**（都要在更新后的 `job/` 里）：

| 位置 | 措施 |
|---|---|
| `scan_x86_entrypoint.sh` `[4c/8]` | 跑矩阵前先做运行时自检：torch 真跑一次 GPU 矩阵乘，ORT 真建一个 CUDA EP session；任一不通过就整体退出，不浪费机时 |
| `measure_ort_scan.py` | 建 session 后检查 `sess.get_providers()`，没有 CUDA 就返回非零，不再写出 CPU 行 |
| `measure_*.py` | warm-up 增加墙钟上限（默认 90 s），万一后端异常慢也不会把时间预算吃光 |
| `scan_x86_entrypoint.sh` `[2/8]` | 默认**不加载 cuDNN 模块**：环境里的 torch/ORT 自带 cuDNN 9 wheels，预加载模块的 cuDNN 8 会让 ORT 的 CUDA EP 起不来。需要时用 `LOAD_CUDNN_MODULE=1` 强制加载 |
| `scan_x86_entrypoint.sh` `[4b/8]` | 把环境里 `nvidia/*/lib` 全部加进 `LD_LIBRARY_PATH`，让 ORT 找得到 cuDNN/cuBLAS |

如果自检没过，先看它打印的 ORT provider 列表和异常信息，把那段发我。

### onnxruntime 的 CUDA EP 起不来怎么办

自检日志里 `session providers` 出现 `CPUExecutionProvider` 就是没起来。
自检已经把 ORT 的日志级别调到 VERBOSE，紧跟着那几行会点名缺哪个库。

**实测到的原因是 CUDA 大版本错配**（2026-09-14）：那次装到的是 `onnxruntime-gpu 1.30.0`，
它要求 **CUDA 13**；而 venv 里 torch cu124 带的是 CUDA 12.4 的库。自检日志里能看到：

```text
Failed to create CUDAExecutionProvider. Require cuDNN 9.* and CUDA 13.*
Failed to load libcublasLt.so.13: cannot open shared object file
```

找不到 `.so.13` 就说明是这个错配。装 CUDA 12 那条线的 ORT 即可：

```bash
~/dlxvenv/bin/pip install --no-cache-dir 'onnxruntime-gpu<1.23'
~/dlxvenv/bin/pip index versions onnxruntime-gpu     # 想看有哪些版本
```

`setup_env_venv.sh` 已改成默认依次尝试 `1.22.*` → `1.21.*` → `<1.23`，并**不再盲目回退到最新版**
（最新版是 CUDA 13 构建，装了也只会静默掉 CUDA EP）。cuDNN 侧不用额外处理：torch cu124
自带的 `nvidia-cudnn-cu12` 是 9.x，符合 ORT 的要求；脚本默认不加载模块的 cuDNN 8，
正是为了避免它抢在前面。

> 另一条路是 `module load cuda/13.0` 让 ORT 拿到 CUDA 13 库，但 `LD_LIBRARY_PATH`
> 优先级高于 torch 自带的 CUDA 12 库，可能把 torch 弄坏，不建议。

按顺序排查：

```bash
~/dlxvenv/bin/python -c "import onnxruntime as ort; print(ort.__version__, ort.get_available_providers())"
ls -d ~/dlxvenv/lib/python3.13/site-packages/nvidia/*/lib     # 确认 cuDNN 9 的库在里面
```

三条路，任选：

| 做法 | 命令 |
|---|---|
| 先拿到 torch 侧的数据，ORT 之后再修 | `SKIP_ORT=1 PYTHON=... sbatch job/scan_x86.slurm` |
| 换一个和 cuDNN 8 匹配的老 ORT（需要 Python ≤3.12 的环境） | 重建环境时 `VENV_DIR` 换新路径，并让基础解释器用 3.12 |
| 让 ORT 自己带库（推荐先试） | 确认自检里 `preload_dlls: ok`；若报错，把那一行发我 |

`SKIP_ORT=1` 走的是 torch eager + torch.compile 两条链路，批次二的"编译路径"证据
仍然成立（Inductor 正是正文 0/18 表里的对象），只是少了 ORT 图优化等级那条轴。
