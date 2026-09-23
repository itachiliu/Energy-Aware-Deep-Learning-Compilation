#!/usr/bin/env bash
# Path B measurement job (TensorRT + trtexec + nvidia-smi).
# Submit from the directory that contains job/ and models/:
#   cd ~ && sbatch job/job.slurm
#
# NOTE: N32-H 区每卡默认分配 55GB 内存，平台不允许显式 --mem 超额申请，
#       因此这里不写 --mem；需要更多内存请增加卡数（--gres=gpu:N）。
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH -t 06:00:00
#SBATCH -J dlenergy-trt
#SBATCH --output=slurm-%j-trt.out

set -e
cd "$SLURM_SUBMIT_DIR" || exit 1
export MINIFORGE_MODULE="${MINIFORGE_MODULE:-miniforge3/26.3.2-3}"
export MODEL_DIR="${MODEL_DIR:-$(pwd)/models}"
export MODE="${MODE:-all}"
bash job/entrypoint.sh
