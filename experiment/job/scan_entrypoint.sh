#!/usr/bin/env bash
# ============================================================================
# Compiler-decision scan: preflight -> dynamic-batch ONNX export (if needed) ->
# ORT graph-opt/batch matrix + PyTorch eager matrix -> summary.
# Target: ARM64 Kylin V10 + A100 + cp310cu122 conda env (already provisioned).
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${OUT_DIR:-$(pwd)/scan_out_$(date +%Y%m%d_%H%M%S)}"
MODEL_DIR="${MODEL_DIR:-$(pwd)/models_scan}"
LOG_DIR="$OUT_DIR/logs"
RESULTS_CSV="$OUT_DIR/results_scan.csv"
AGG_CSV="$OUT_DIR/results_scan_agg.csv"
SUMMARY_MD="$OUT_DIR/summary_scan.md"
REPS="${REPS:-8}"
DURATION_S="${DURATION_S:-20}"
BATCHES="${BATCHES:-1,16}"
GRAPH_OPTS="${GRAPH_OPTS:-0,1,2,99}"
EXTRA_MODELS="${EXTRA_MODELS:-0}"

echo "=== [1/7] preflight ==="
mkdir -p "$OUT_DIR/env" "$LOG_DIR" "$MODEL_DIR"
echo "OUT_DIR=$OUT_DIR"
echo "MODEL_DIR=$MODEL_DIR"
echo "REPS=$REPS DURATION_S=$DURATION_S BATCHES=$BATCHES GRAPH_OPTS=$GRAPH_OPTS EXTRA_MODELS=$EXTRA_MODELS"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L 2>/dev/null | head -5 || true
else
  echo "WARN: nvidia-smi not found; this job must run on a GPU node"
fi

echo "=== [2/7] platform modules ==="
if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true
  for m in "${CMAKE_MODULE:-cmake/3.26.3}" "${MINIFORGE_MODULE:-miniforge3/26.3.2-3}" \
           "${GCC_MODULE:-compilers/gcc/11.3.0}" "${CUDA_MODULE:-compilers/cuda/12.2}" \
           "${CUDNN_MODULE:-cudnn/8.9.5.29_cuda12.x}"; do
    if module load "$m" >/dev/null 2>&1; then
      echo "module loaded: $m"
    else
      echo "WARN: module load $m failed"
    fi
  done
else
  echo "module command not found; assuming pre-loaded environment"
fi

echo "=== [3/7] python ==="
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  for cand in "$HOME/.conda/envs/cp310cu122/bin/python" \
              "$HOME/miniconda3/envs/cp310cu122/bin/python" \
              "$HOME/.conda/envs/dlenergy/bin/python"; do
    if [ -x "$cand" ]; then PYTHON="$cand"; break; fi
  done
fi
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  echo "ERROR: no python>=3.8 found. Set PYTHON=/path/to/python or activate cp310cu122."
  exit 1
fi
echo "python: $PYTHON"
"$PYTHON" - <<'EOF'
import sys
print(sys.version)
try:
    import torch
    print("torch", torch.__version__, "cuda_ok", torch.cuda.is_available())
except Exception as e:
    print("torch unavailable:", e)
try:
    import onnxruntime as ort
    print("ort providers:", ort.get_available_providers())
except Exception as e:
    print("onnxruntime unavailable:", e)
EOF

echo "=== [4/7] environment snapshot ==="
{
  echo "host: $(hostname)"
  uname -a
  nvidia-smi --query-gpu=name,driver_version,memory.total,power.draw --format=csv 2>/dev/null || true
  echo "modules:"
  module list 2>/dev/null || true
} > "$OUT_DIR/env/snapshot.txt" 2>&1
cat "$OUT_DIR/env/snapshot.txt"

echo "=== [5/7] prepare dynamic-batch onnx models ==="
NEEDED="mobilenetv2 resnet50 vit_b_16"
if [ "$EXTRA_MODELS" = "1" ]; then
  NEEDED="$NEEDED resnet18 mobilenetv3_large"
fi
MISSING=0
for n in $NEEDED; do
  if [ ! -f "$MODEL_DIR/$n.onnx" ]; then
    echo "missing $MODEL_DIR/$n.onnx; exporting..."
    if ! "$PYTHON" "$SCRIPT_DIR/export_scan_models.py" --out "$MODEL_DIR" --only "$n"; then
      echo "ERROR: export of $n failed (see output above)"
      exit 1
    fi
    MISSING=1
  fi
done
[ "$MISSING" = "0" ] && echo "all required onnx models present"
ls -la "$MODEL_DIR"

echo "=== [6/7] run matrix ==="
EXTRA_FLAG=""
if [ "$EXTRA_MODELS" = "1" ]; then EXTRA_FLAG="--extra-models"; fi
"$PYTHON" "$SCRIPT_DIR/run_scan_all.py" \
  --python "$PYTHON" --models-dir "$MODEL_DIR" \
  --out "$RESULTS_CSV" --log-dir "$LOG_DIR" \
  --reps "$REPS" --duration-s "$DURATION_S" \
  --batches "$BATCHES" --graph-opts "$GRAPH_OPTS" $EXTRA_FLAG

echo "=== [7/7] summarize ==="
"$PYTHON" "$SCRIPT_DIR/summarize_scan.py" \
  --csv "$RESULTS_CSV" --out "$SUMMARY_MD" --agg "$AGG_CSV" \
  --failures "$LOG_DIR/failures.txt"

echo "SCAN_DONE"
