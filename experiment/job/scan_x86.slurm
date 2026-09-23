#!/usr/bin/env bash
# Compiler-decision scan on the x86 GPU queue (RTX 4090 / 5090).
#   cd ~ && sbatch job/scan_x86.slurm
#
# TensorRT stage is off by default (module names differ per cluster):
#   ENABLE_TRT=1 sbatch job/scan_x86.slurm
# Faster smoke test:
#   REPS=2 DURATION_S=8 EXTRA_MODELS=0 sbatch job/scan_x86.slurm
#
# Partitions on this cluster: gpu_4090 / gpu_5090 / gpu_3090.
# The default below is gpu_4090; override on the command line for another card:
#   sbatch -p gpu_5090 job/scan_x86.slurm
# This cluster's submit plugin wants --gpus=N (not --gres=gpu:N), and CPU/memory
# are fixed per card (4090: 6 cores/60GB, 5090: 8 cores/126GB), so asking for
# more CPU or --mem gets rejected. Leave both out.
#SBATCH -N 1
#SBATCH --partition=gpu_4090
#SBATCH --gpus=1
#SBATCH -t 06:00:00
#SBATCH -J dlx-scan
#SBATCH --output=slurm-%j-scan.out

set -e
cd "$SLURM_SUBMIT_DIR" || exit 1
# Accept being submitted either from the parent of job/ or from inside job/.
if [ ! -f job/scan_x86_entrypoint.sh ] && [ -f scan_x86_entrypoint.sh ]; then cd ..; fi
if [ ! -f job/scan_x86_entrypoint.sh ]; then
  echo "ERROR: job/scan_x86_entrypoint.sh not found under $SLURM_SUBMIT_DIR"
  echo "       Submit from the directory that CONTAINS job/, e.g."
  echo "         cd ~/run && sbatch job/scan_x86.slurm"
  exit 1
fi
export MODEL_DIR="${MODEL_DIR:-$(pwd)/models_scan}"
export REPS="${REPS:-8}"
export BATCHES="${BATCHES:-1,16}"
export GRAPH_OPTS="${GRAPH_OPTS:-0,1,2,99}"
export EXTRA_MODELS="${EXTRA_MODELS:-0}"
export MODELS="${MODELS:-}"
export ENABLE_TRT="${ENABLE_TRT:-0}"
export ENABLE_COMPILE="${ENABLE_COMPILE:-1}"
export COMPILE_MODE="${COMPILE_MODE:-default}"
bash job/scan_x86_entrypoint.sh
