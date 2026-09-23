#!/usr/bin/env bash
# ============================================================================
# Create the conda environment for the x86 batch (RTX 4090 / 5090).
# Safe to run on a login node (no GPU needed); it only installs packages.
#
#   module load miniforge3/26.3.2-3     # or whatever the cluster provides
#   bash job/setup_env_x86.sh
#
# Optional overrides:
#   ENV_NAME=dlx          conda env name            (default: dlx)
#   SM_ARCH=120           force the compute capability target
#   TORCH_INDEX=...       override the pip index URL
# ============================================================================
set -uo pipefail

ENV_NAME="${ENV_NAME:-dlx}"
LOG_DIR="${LOG_DIR:-$(pwd)/setup_logs}"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/setup_env_$(date +%Y%m%d_%H%M%S).log"

note() { echo "$@" | tee -a "$LOG"; }

note "=== [1/4] locate conda ==="
if ! command -v conda >/dev/null 2>&1; then
  if command -v module >/dev/null 2>&1; then
    for m in "${MINIFORGE_MODULE:-}" miniforge3/26.3.2-3 miniforge3/24.1 miniforge3; do
      [ -n "$m" ] || continue
      if module load "$m" >/dev/null 2>&1; then echo "loaded module $m" | tee -a "$LOG"; break; fi
    done
  fi
fi
CONDA_EXE="$(command -v conda 2>/dev/null || true)"
if [ -z "$CONDA_EXE" ]; then
  for c in "$HOME/miniforge3/bin/conda" "$HOME/miniconda3/bin/conda"; do
    [ -x "$c" ] && CONDA_EXE="$c" && break
  done
fi
if [ -z "$CONDA_EXE" ]; then
  note "ERROR: conda not found. Load a miniforge/miniconda module first."
  exit 1
fi
note "conda: $CONDA_EXE"

note "=== [2/4] detect GPU generation ==="
SM="${SM_ARCH:-}"
GPU_NAME=""
if [ -z "$SM" ] && command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
  SM="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d '.')"
  [ "$SM" = "N/A" ] && SM=""
fi
case "$GPU_NAME" in
  *5090*|*5080*|*B200*|*B100*) [ -z "$SM" ] && SM=120 ;;
  *4090*|*4080*|*L40*|*L4*)     [ -z "$SM" ] && SM=89 ;;
  *A100*)                       [ -z "$SM" ] && SM=80 ;;
esac
if [ -z "$SM" ]; then
  SM=89
  DETECTED=0
else
  DETECTED=1
fi
note "gpu='${GPU_NAME:-unknown}' sm_arch=$SM (detected=$DETECTED)"
if [ "$DETECTED" = "0" ]; then
  note ""
  note "NOTE: no GPU visible here (login node?), so this fell back to the sm_89 default,"
  note "      i.e. the build for an RTX 4090. That is correct if the GPU queue gives you"
  note "      a 4090. For a 5090 (sm_120) rebuild explicitly:"
  note "        SM_ARCH=120 ENV_NAME=dlx5090 bash job/setup_env_x86.sh"
  note "      Check which card you actually get with:"
  note "        sbatch --partition=<gpu-partition> --wrap=\"nvidia-smi --query-gpu=name,compute_cap --format=csv\""
  note ""
fi

if [ "$SM" -ge 120 ]; then
  # Blackwell: needs CUDA 12.8 wheels and a recent ONNX Runtime.
  TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu128}"
  ORT_SPEC="${ORT_SPEC:-onnxruntime-gpu}"
  note "target: Blackwell (sm_120) -> torch cu128, latest onnxruntime-gpu"
else
  TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu124}"
  ORT_SPEC="${ORT_SPEC:-onnxruntime-gpu==1.18.1}"
  note "target: Ada/Ampere (sm_$SM) -> torch cu124, onnxruntime-gpu 1.18.1"
fi

note "=== [3/4] create env '$ENV_NAME' (python 3.10) ==="
note "this can take 1-3 minutes (dependency solve + downloads). If the child"
note "output stays silent for more than ~10 minutes, see the '建环境卡住' section"
note "of job/README_x86.md before killing it."
# The classic solver can spend many minutes on a tiny spec; libmamba is much faster.
if "$CONDA_EXE" config --show solver >/dev/null 2>&1; then
  export CONDA_SOLVER="${CONDA_SOLVER:-libmamba}"
  note "conda solver: $CONDA_SOLVER"
fi
if "$CONDA_EXE" env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  note "env already exists; reusing"
else
  # </dev/null so a channel Terms-of-Service prompt fails fast instead of hanging.
  if ! "$CONDA_EXE" create -y -n "$ENV_NAME" python=3.10 ${CONDA_CREATE_EXTRA:-} \
       </dev/null 2>&1 | tee -a "$LOG"; then
    note ""
    note "ERROR: conda create failed. Common causes:"
    note "  - no outbound network on this node"
    note "    test: curl -sI --max-time 10 https://conda.anaconda.org/conda-forge/noarch/repodata.json | head -1"
    note "  - a configured channel mirror is unreachable (conda config --show channels)"
    exit 1
  fi
fi
ENV_PY="$("$CONDA_EXE" run -n "$ENV_NAME" python -c 'import sys; print(sys.executable)' 2>>"$LOG")"
if [ -z "$ENV_PY" ] || [ ! -x "$ENV_PY" ]; then
  ENV_PY="$("$CONDA_EXE" info --base)/envs/$ENV_NAME/bin/python"
fi
note "env python: $ENV_PY"

note "=== [4/4] install packages ==="
"$ENV_PY" -m pip install --upgrade pip 2>&1 | tail -2 | tee -a "$LOG"
note "-- torch / torchvision (index: $TORCH_INDEX) --"
"$ENV_PY" -m pip install torch torchvision --index-url "$TORCH_INDEX" 2>&1 | tail -5 | tee -a "$LOG"
note "-- onnx stack --"
"$ENV_PY" -m pip install onnx onnxscript 2>&1 | tail -3 | tee -a "$LOG"
note "-- onnxruntime-gpu ($ORT_SPEC) --"
if ! "$ENV_PY" -m pip install "$ORT_SPEC" 2>&1 | tail -3 | tee -a "$LOG"; then
  note "pinned ORT failed; trying latest onnxruntime-gpu"
  "$ENV_PY" -m pip install onnxruntime-gpu 2>&1 | tail -3 | tee -a "$LOG"
fi
note "-- misc --"
"$ENV_PY" -m pip install pynvml pandas numpy 2>&1 | tail -3 | tee -a "$LOG"

note "=== verify ==="
"$ENV_PY" -c "import torch; print('torch', torch.__version__, 'cuda_ok', torch.cuda.is_available())" 2>&1 | tee -a "$LOG"
"$ENV_PY" -c "import onnxruntime as ort; print('ort', ort.__version__, ort.get_available_providers())" 2>&1 | tee -a "$LOG"
note "SETUP_DONE"
note "python path for the scan job: $ENV_PY"
