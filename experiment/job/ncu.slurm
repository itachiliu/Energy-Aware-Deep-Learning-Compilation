#!/usr/bin/env bash
# DRAM-bytes profiling job (Nsight Compute). Submit after models exist:
#   sbatch job/ncu.slurm ; cat ~/slurm-<JOBID>-ncu.out
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH -t 06:00:00
#SBATCH -J dlenergy-ncu
#SBATCH --output=slurm-%j-ncu.out

set -e
cd "$SLURM_SUBMIT_DIR" || exit 1
module purge >/dev/null 2>&1 || true
module load cmake/3.26.3 miniforge3/26.3.2-3 compilers/gcc/11.3.0 \
  compilers/cuda/12.2 cudnn/8.9.5.29_cuda12.x
export PY="$HOME/.conda/envs/cp310cu122/bin/python"
OUT="$(pwd)/ncu_out_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT/logs"
"$PY" job/run_ncu.py --python "$PY" --models-dir "$(pwd)/models" \
  --log-dir "$OUT/logs" | tee "$OUT/ncu_results.txt"
echo "NCU_OUT=$OUT"
