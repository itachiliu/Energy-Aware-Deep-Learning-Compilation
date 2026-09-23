#!/usr/bin/env bash
# Environment probe for the x86 GPU queue (RTX 4090 / 5090).
#   cd ~ && sbatch job/probe_x86.slurm
#   cat ~/slurm-<JOBID>-probe.out
#
# Partitions on this cluster: gpu_4090 / gpu_5090 / gpu_3090.
# The default below is gpu_4090; override on the command line for another card:
#   sbatch -p gpu_5090 job/probe_x86.slurm
# This cluster's submit plugin wants --gpus=N (not --gres=gpu:N), and CPU/memory
# are fixed per card (4090: 6 cores/60GB, 5090: 8 cores/126GB), so asking for
# more CPU or --mem gets rejected. Leave both out.
#SBATCH -N 1
#SBATCH --partition=gpu_4090
#SBATCH --gpus=1
#SBATCH -t 00:20:00
#SBATCH -J dlx-probe
#SBATCH --output=slurm-%j-probe.out

cd "$SLURM_SUBMIT_DIR" || exit 1
# Accept being submitted either from the parent of job/ or from inside job/.
if [ ! -f job/probe_x86.sh ] && [ -f probe_x86.sh ]; then cd ..; fi
if [ ! -f job/probe_x86.sh ]; then
  echo "ERROR: job/probe_x86.sh not found under $SLURM_SUBMIT_DIR"
  echo "       Submit from the directory that CONTAINS job/, e.g."
  echo "         cd ~/run && sbatch job/probe_x86.slurm"
  exit 1
fi
bash job/probe_x86.sh
