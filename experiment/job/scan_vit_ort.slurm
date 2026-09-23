#!/usr/bin/env bash
# Re-run ONLY the missing ViT-B/16 ORT group (graph-opt 0/1/2/99 x batch 1/16,
# 8 reps) and append to the existing scan results CSV.
# Submit from the directory containing job/:
#   cd ~ && sbatch job/scan_vit_ort.slurm
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH -t 02:00:00
#SBATCH -J dlenergy-scan-vit
#SBATCH --output=slurm-%j-scan-vit.out

set -euo pipefail
cd "$SLURM_SUBMIT_DIR" || exit 1

MODEL_DIR="${MODEL_DIR:-$(pwd)/models_scan}"
SCAN_CSV="${SCAN_CSV:-$(pwd)/scan_out_20260908_012226/results_scan.csv}"
LOG_DIR="${LOG_DIR:-$(pwd)/scan_out_20260908_012226/logs}"
JOB_DIR="${JOB_DIR:-$(pwd)/job}"
REPS="${REPS:-8}"
DURATION_S="${DURATION_S:-20}"

echo "JOB_DIR=$JOB_DIR"
echo "MODEL_DIR=$MODEL_DIR"
echo "SCAN_CSV=$SCAN_CSV"

echo "=== modules ==="
if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true
  for m in cmake/3.26.3 miniforge3/26.3.2-3 compilers/gcc/11.3.0 \
           compilers/cuda/12.2 cudnn/8.9.5.29_cuda12.x; do
    module load "$m" >/dev/null 2>&1 && echo "loaded: $m" || echo "WARN: $m"
  done
fi

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  for cand in "$HOME/.conda/envs/cp310cu122/bin/python" \
              "$HOME/miniconda3/envs/cp310cu122/bin/python"; do
    if [ -x "$cand" ]; then PYTHON="$cand"; break; fi
  done
fi
[ -x "$PYTHON" ] || { echo "ERROR: no python found (set PYTHON=...)"; exit 1; }
echo "python: $PYTHON"

mkdir -p "$MODEL_DIR" "$LOG_DIR"

echo "=== ensure vit_b_16.onnx ==="
if [ ! -f "$MODEL_DIR/vit_b_16.onnx" ]; then
  "$PYTHON" "$JOB_DIR/export_scan_models.py" \
    --out "$MODEL_DIR" --only vit_b_16
fi
ls -la "$MODEL_DIR/vit_b_16.onnx"

echo "=== append ViT ORT group ==="
for b in 1 16; do
  for o in 0 1 2 99; do
    tag="vit_b_16-ort-fp32-opt${o}-b${b}"
    log="$LOG_DIR/ort_${tag}.log"
    echo "[run] $tag reps=$REPS"
    "$PYTHON" "$JOB_DIR/measure_ort_scan.py" \
      --model "$MODEL_DIR/vit_b_16.onnx" --batch "$b" \
      --graph-opt-level "$o" --tag "$tag" \
      --reps "$REPS" --duration-s "$DURATION_S" \
      --flops 17.6 --out "$SCAN_CSV" 2>&1 | tee "$log"
  done
done

echo "=== summarize + check (expect 36 configs x $REPS rows) ==="
"$PYTHON" "$JOB_DIR/summarize_scan.py" \
  --csv "$SCAN_CSV" \
  --out "$(dirname "$SCAN_CSV")/summary_scan.md" \
  --agg "$(dirname "$SCAN_CSV")/results_scan_agg.csv" \
  --failures "$LOG_DIR/failures.txt" || true
"$PYTHON" "$JOB_DIR/check_scan.py" \
  --raw "$SCAN_CSV" --reps "$REPS" || true

echo "VIT_ORT_DONE"
