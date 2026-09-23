#!/usr/bin/env bash
# Submit:  sbatch job/cuda_probe.slurm ; cat ~/slurm-<JOBID>-probe.out
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH -t 00:15:00
#SBATCH -J dlenergy-cuda-probe
#SBATCH --output=slurm-%j-probe.out

cd "$SLURM_SUBMIT_DIR" || exit 1
bash job/cuda_probe.sh
