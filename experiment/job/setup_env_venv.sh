#!/usr/bin/env bash
# ============================================================================
# Build the x86 batch environment with venv + pip, skipping conda solving.
# Run on the LOGIN node (it has internet); compute nodes have none.
#
#   module load miniforge3/26.3.2-3
#   bash job/setup_env_venv.sh
#
# Overrides:
#   VENV_DIR=~/dlxvenv            where to create it
#   TORCH_INDEX=...               default: cu124 (works on 4090/3090)
#                                 for the 5090 use .../whl/cu128
#   PIP_MIRROR=...                e.g. https://pypi.tuna.tsinghua.edu.cn/simple
#   ORT_SPEC=...                  default: onnxruntime-gpu==1.18.1
# ============================================================================
set -uo pipefail

VENV_DIR="${VENV_DIR:-$HOME/dlxvenv}"
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cu124}"
# onnxruntime-gpu track matters more than the exact version: the newest releases
# are built against CUDA 13, while the torch cu124 wheels in this env ship CUDA
# 12 libraries. An ORT that wants CUDA 13 loads, then silently drops its CUDA EP
# at session time ("Failed to create CUDAExecutionProvider. Require ... CUDA 13.*").
# Try the newest CUDA-12 line first; ORT_SPEC overrides the whole list.
ORT_SPEC="${ORT_SPEC:-onnxruntime-gpu==1.22.* onnxruntime-gpu==1.21.* onnxruntime-gpu<1.23}"
# Home quotas on HPC clusters are often tight; the pip wheel cache would double
# the footprint, so it is off unless PIP_NO_CACHE=0.
PIP_NO_CACHE="${PIP_NO_CACHE:-1}"
LOG_DIR="${LOG_DIR:-$(pwd)/setup_logs}"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/setup_venv_$(date +%Y%m%d_%H%M%S).log"

note() { echo "$@" | tee -a "$LOG"; }

PIPFLAGS=()
if [ "$PIP_NO_CACHE" != "0" ]; then PIPFLAGS+=(--no-cache-dir); fi

note "=== [1/4] base python ==="
# Always bring the conda base into view: the system /usr/bin/python on Ubuntu
# usually has no venv module, so picking whatever `python` resolves to first
# would be wrong.
if command -v module >/dev/null 2>&1 && [ -z "${CONDA_PREFIX:-}" ]; then
  for m in "${MINIFORGE_MODULE:-}" miniforge3/26.3.2-3 miniforge3/26.1 \
           miniforge3/25.11.0-1 miniforge3; do
    [ -n "$m" ] || continue
    if module load "$m" >/dev/null 2>&1; then note "loaded module $m"; break; fi
  done
fi

CONDA_BASE=""
if command -v conda >/dev/null 2>&1; then
  CONDA_BASE="$(conda info --base 2>/dev/null || true)"
fi
if [ -z "$CONDA_BASE" ] && [ -n "${CONDA_PREFIX:-}" ]; then
  CONDA_BASE="$CONDA_PREFIX"
fi
note "conda base: ${CONDA_BASE:-not found}"

BASE_PY=""
CREATOR=""
for cand in "${BASE_PY_OVERRIDE:-}" \
            "$CONDA_BASE/bin/python" "$HOME/miniforge3/bin/python" \
            "$HOME/miniconda3/bin/python" /data/apps/miniforge3/26.3.2-3/bin/python \
            "$(command -v python 2>/dev/null || true)" \
            "$(command -v python3 2>/dev/null || true)"; do
  [ -n "$cand" ] && [ -x "$cand" ] || continue
  if "$cand" -c 'import sys, venv; assert sys.version_info >= (3, 8)' >/dev/null 2>&1; then
    BASE_PY="$cand"; CREATOR="venv"
    note "  usable (venv):    $cand ($("$cand" --version 2>&1))"
    break
  fi
  if "$cand" -c 'import sys, virtualenv; assert sys.version_info >= (3, 8)' >/dev/null 2>&1; then
    BASE_PY="$cand"; CREATOR="virtualenv"
    note "  usable (virtualenv): $cand ($("$cand" --version 2>&1))"
    break
  fi
  note "  skipped:          $cand ($("$cand" --version 2>&1 | head -1); no venv module)"
done

if [ -z "$BASE_PY" ]; then
  note ""
  note "ERROR: no interpreter with a venv module was found."
  note "  The system /usr/bin/python on Ubuntu lacks python3-venv, so point the"
  note "  script at the conda base python explicitly, e.g.:"
  note "    BASE_PY=$CONDA_BASE/bin/python bash job/setup_env_venv.sh"
  note "  or install one: python3 -m pip install --user virtualenv"
  exit 1
fi
note "base python: $BASE_PY (via $CREATOR)"

note "=== [2/4] create env at $VENV_DIR ==="
if [ -x "$VENV_DIR/bin/python" ]; then
  note "env already exists; reusing"
else
  if ! "$BASE_PY" -m "$CREATOR" "$VENV_DIR" 2>&1 | tee -a "$LOG"; then
    note "first attempt failed; retrying without the pip bootstrap"
    # Only clear the directory we just tried to create.
    if [ -d "$VENV_DIR/bin" ] || [ -f "$VENV_DIR/pyvenv.cfg" ]; then
      rm -rf "$VENV_DIR"
    fi
    "$BASE_PY" -m venv --without-pip "$VENV_DIR" 2>&1 | tee -a "$LOG" \
      || { note "ERROR: env creation failed"; exit 1; }
    "$VENV_DIR/bin/python" -m ensurepip --upgrade 2>&1 | tail -3 | tee -a "$LOG" || true
  fi
fi
VPY="$VENV_DIR/bin/python"
note "venv python: $VPY ($("$VPY" --version 2>&1))"

note "=== [2b/4] disk check ==="
df -h "$VENV_DIR" 2>/dev/null | tail -2 | tee -a "$LOG" || true
avail_kb="$(df -Pk "$VENV_DIR" 2>/dev/null | awk 'NR==2{print $4}')"
if [ -n "${avail_kb:-}" ]; then
  if [ "$avail_kb" -lt 2097152 ] 2>/dev/null; then
    note "ERROR: under 2 GB free in $VENV_DIR's filesystem -- the CUDA torch stack"
    note "       cannot fit. This is usually a home-directory quota, which is separate"
    note "       from the /data volume size. Put the env on a roomier path, e.g.:"
    note "         VENV_DIR=\$PWD/dlxvenv PIP_NO_CACHE=1 bash job/setup_env_venv.sh"
    exit 1
  elif [ "$avail_kb" -lt 12582912 ] 2>/dev/null; then
    note "WARN: under 12 GB free where the env lives. The CUDA torch stack needs about"
    note "      5 GB installed; with the pip cache on it needs roughly double that."
  fi
fi

note "=== [3/4] install packages (this downloads ~3 GB) ==="
"$VPY" -m pip install "${PIPFLAGS[@]}" --upgrade pip 2>&1 | tail -2 | tee -a "$LOG"

note "-- torch / torchvision from $TORCH_INDEX --"
"$VPY" -m pip install "${PIPFLAGS[@]}" torch torchvision --index-url "$TORCH_INDEX" \
  2>&1 | tail -8 | tee -a "$LOG" \
  || { note "ERROR: torch install failed. If the log above says 'Disk quota exceeded',";
       note "       free space (rm -rf ~/.cache/pip) or move VENV_DIR, then rerun.";
       exit 1; }

EXTRA=()
if [ -n "${PIP_MIRROR:-}" ]; then EXTRA=(-i "$PIP_MIRROR"); fi

note "-- onnx stack --"
"$VPY" -m pip install "${PIPFLAGS[@]}" "${EXTRA[@]}" onnx onnxscript 2>&1 | tail -3 | tee -a "$LOG"

note "-- onnxruntime-gpu ($ORT_SPEC) --"
ORT_OK=0
for spec in $ORT_SPEC; do
  note "  trying $spec"
  if "$VPY" -m pip install "${PIPFLAGS[@]}" "${EXTRA[@]}" "$spec" 2>&1 | tail -3 | tee -a "$LOG"; then
    ORT_OK=1
    note "  installed $spec"
    break
  fi
done
if [ "$ORT_OK" = "0" ]; then
  note "WARN: no CUDA-12 onnxruntime-gpu could be installed for this Python."
  note "      Do NOT fall back to the newest release blindly: those are built for"
  note "      CUDA 13 and will silently drop the CUDA EP. Run the job with"
  note "      SKIP_ORT=1 to measure the torch backends, or list what exists with"
  note "      '$VPY -m pip index versions onnxruntime-gpu'."
fi

note "-- misc --"
"$VPY" -m pip install "${PIPFLAGS[@]}" "${EXTRA[@]}" pynvml pandas numpy 2>&1 | tail -3 | tee -a "$LOG"

note "=== [4/4] verify ==="
"$VPY" -c "import torch; print('torch', torch.__version__, 'cuda_ok', torch.cuda.is_available())" 2>&1 | tee -a "$LOG"
"$VPY" -c "import torchvision; print('torchvision', torchvision.__version__)" 2>&1 | tee -a "$LOG"
"$VPY" -c "import onnxruntime as ort; print('ort', ort.__version__, ort.get_available_providers())" 2>&1 | tee -a "$LOG"
note ""
note "SETUP_DONE"
note "submit the scan with:"
note "  PYTHON=$VPY sbatch job/scan_x86.slurm"
