#!/usr/bin/env bash
# Compiler-decision scan job (ORT graph-opt levels x batch + torch eager x batch).
# Submit from the directory containing job/ :
#   cd ~ && sbatch job/scan.slurm
# NOTE: N32-H per-GPU default memory is 55GB; do NOT add --mem.
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH -t 12:00:00
#SBATCH -J dlenergy-scan
#SBATCH --output=slurm-%j-scan.out

set -e
cd "$SLURM_SUBMIT_DIR" || exit 1
export MODEL_DIR="${MODEL_DIR:-$(pwd)/models_scan}"
export REPS="${REPS:-8}"
export BATCHES="${BATCHES:-1,16}"
export GRAPH_OPTS="${GRAPH_OPTS:-0,1,2,99}"
export EXTRA_MODELS="${EXTRA_MODELS:-0}"
bash job/scan_entrypoint.sh
