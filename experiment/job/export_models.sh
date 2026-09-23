#!/usr/bin/env bash
# Install CPU torch/torchvision/onnx into the resolved Python env and export the
# three ONNX models (opset 13, batch 1, random weights by default).
# Used when the models were not uploaded; run with:
#   sbatch job/job.slurm   (MODE=models_only)   or   MODE=models_only bash job/entrypoint.sh
# Usage: bash export_models.sh <python> <model_dir> <log_dir>
set -uo pipefail

PY="${1:?python path required}"
MODEL_DIR="${2:?model dir required}"
LOGDIR="${3:?log dir required}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$MODEL_DIR" "$LOGDIR"
export PYTHONIOENCODING=utf-8

need() { "$PY" -c "import $1" >/dev/null 2>&1; }

if ! need torch || ! need torchvision; then
  echo "installing CPU torch/torchvision from download.pytorch.org (10-30 min)..."
  if ! timeout 1500 "$PY" -m pip install torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu \
        > "$LOGDIR/pip_torch_cpu.log" 2>&1; then
    echo "download.pytorch.org failed/timed out; retrying from default PyPI..."
    timeout 1800 "$PY" -m pip install torch torchvision \
        > "$LOGDIR/pip_torch_pypi.log" 2>&1 \
      || { echo "ERROR: torch install failed (see logs/pip_torch_cpu.log / pip_torch_pypi.log)"; exit 1; }
  fi
  "$PY" -c "import torch, torchvision; print('torch', torch.__version__, '| torchvision', torchvision.__version__)" \
    || { echo "ERROR: torch import check failed"; exit 1; }
fi
if ! need onnx; then
  echo "installing onnx..."
  timeout 600 "$PY" -m pip install onnx > "$LOGDIR/pip_onnx.log" 2>&1 \
    || { echo "ERROR: onnx install failed (see logs/pip_onnx.log)"; exit 1; }
fi
if ! need onnxscript; then
  echo "installing onnxscript (required by torch.onnx.export in torch >= 2.14)..."
  timeout 600 "$PY" -m pip install onnxscript > "$LOGDIR/pip_onnxscript.log" 2>&1 \
    || { echo "ERROR: onnxscript install failed (see logs/pip_onnxscript.log)"; exit 1; }
fi

PRE_FLAG=""
if [ "${PRETRAINED:-0}" = "1" ]; then
  PRE_FLAG="--pretrained"
  echo "using ImageNet-pretrained weights (downloads; only when PRETRAINED=1)"
fi

"$PY" "$SCRIPT_DIR/fetch_models.py" --out "$MODEL_DIR" --opset 13 --size 224 $PRE_FLAG \
  || { echo "ERROR: fetch_models.py failed"; exit 1; }
echo "exported models:"
ls -la "$MODEL_DIR"
echo "export OK"
