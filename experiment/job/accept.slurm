#!/usr/bin/env bash
# Run the environment acceptance probe on a GPU compute node.
#   sbatch job/accept.slurm
#   cat ~/slurm-<JOBID>-accept.out
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH -t 00:10:00
#SBATCH -J dlenergy-accept
#SBATCH --output=slurm-%j-accept.out

cd "$SLURM_SUBMIT_DIR" || exit 1
bash job/accept_env.sh
