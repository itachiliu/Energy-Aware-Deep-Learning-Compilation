#!/usr/bin/env bash
# Standalone model-export job (only needed when models/ was not uploaded).
#   sbatch job/export_models.slurm
# then submit the measurement job normally:
#   sbatch job/job.slurm
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH -t 06:00:00
#SBATCH -J dlenergy-export
#SBATCH --output=slurm-%j-export.out

set -e
cd "$SLURM_SUBMIT_DIR" || exit 1
export MINIFORGE_MODULE="${MINIFORGE_MODULE:-miniforge3/26.3.2-3}"
export MODEL_DIR="${MODEL_DIR:-$(pwd)/models}"
export MODE=models_only
bash job/entrypoint.sh
