#!/usr/bin/env bash
# ============================================================================
# Path B mini-experiment job: TensorRT 8.5 + trtexec + nvidia-smi power sampling
# Target platform: ARM64 Kylin V10, NVIDIA A100, Slurm + miniforge modules
#
#   all-in-one (build engines + measure):  sbatch job/job.slurm
#   export ONNX models only:               MODE=models_only sbatch job/job.slurm
#   manual run on a GPU node:              bash job/entrypoint.sh
#
# Env overrides: OUT_DIR, MODEL_DIR, MINIFORGE_MODULE, TRT_CUDA_MODULE,
#                TRT_CUDNN_MODULE, TRT_MODULE, TRTEXEC, PRECISIONS, REPS,
#                DURATION_MS, PYTHON, CONDA_ENV_NAME, EXPORT_MODELS
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${MODE:-all}"          # all | models_only
OUT_DIR="${OUT_DIR:-$(pwd)/experiment_out_$(date +%Y%m%d_%H%M%S)}"
MODEL_DIR="${MODEL_DIR:-$(pwd)/models}"
LOG_DIR="$OUT_DIR/logs"
ENGINE_DIR="$OUT_DIR/engines"
RESULTS_CSV="$OUT_DIR/results.csv"
SUMMARY_MD="$OUT_DIR/summary.md"

echo "=== [1/9] preflight ==="
mkdir -p "$OUT_DIR/env" "$LOG_DIR" "$MODEL_DIR" "$ENGINE_DIR"
echo "MODE=$MODE"
echo "SCRIPT_DIR=$SCRIPT_DIR"
echo "OUT_DIR=$OUT_DIR"
echo "MODEL_DIR=$MODEL_DIR"
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi found"
  nvidia-smi -L 2>/dev/null | head -5 || true
else
  echo "WARN: nvidia-smi not found on this node; the job must run on a GPU node"
fi

# ---------------------------------------------------------------------------
# [2/9] platform modules (purge first so an interactive session does not keep
#       an old CUDA/cuDNN that conflicts with the TensorRT-11.8 stack)
# ---------------------------------------------------------------------------
echo "=== [2/9] platform modules ==="
if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true

  CM="${CMAKE_MODULE:-cmake/3.26.3}"
  module load "$CM" >/dev/null 2>&1 && echo "module loaded: $CM" \
    || echo "WARN: cmake module load failed (set CMAKE_MODULE=<name>)"

  MOD="${MINIFORGE_MODULE:-miniforge3/26.3.2-3}"
  if module load "$MOD" >/dev/null 2>&1; then
    echo "module loaded: $MOD"
  else
    echo "WARN: module load $MOD failed; set MINIFORGE_MODULE=miniforge3/<version>"
  fi

  GCC_LOADED=""
  for gc in "${GCC_MODULE:-}" compilers/gcc/11.3.0 compilers/gcc/11.2.0; do
    [ -n "$gc" ] || continue
    if module load "$gc" >/dev/null 2>&1; then
      echo "module loaded: $gc"
      GCC_LOADED="$gc"
      break
    fi
  done

  CU_LOADED=""
  for cu in "${CUDA_MODULE:-}" compilers/cuda/12.2 cuda/12.2.0 cuda/12.2 compilers/cuda/11.8; do
    [ -n "$cu" ] || continue
    if module load "$cu" >/dev/null 2>&1; then
      echo "module loaded: $cu"
      CU_LOADED="$cu"
      break
    fi
  done
  [ -n "$CU_LOADED" ] || echo "WARN: no CUDA module loaded; set CUDA_MODULE=<name>"

  DN_LOADED=""
  for dn in "${CUDNN_MODULE:-}" cudnn/8.9.5.29_cuda12.x cudnn/8.6.0.163_cuda11.x; do
    [ -n "$dn" ] || continue
    if module load "$dn" >/dev/null 2>&1; then
      echo "module loaded: $dn"
      DN_LOADED="$dn"
      break
    fi
  done
  [ -n "$DN_LOADED" ] || echo "WARN: no cuDNN module loaded; set CUDNN_MODULE=<name>"

  TRT_LOADED=""
  for trt in "${TRT_MODULE:-}" TensorRT/8.5.3.1-cuda11.8-cudnn8.6 TensorRT/10.4.0-cuda12.2; do
    [ -n "$trt" ] || continue
    if module load "$trt" >/dev/null 2>&1; then
      echo "module loaded: $trt"
      TRT_LOADED="$trt"
      break
    fi
  done
  [ -n "$TRT_LOADED" ] || echo "WARN: no TensorRT module loaded (TRT 后端将跳过)"
else
  echo "module command not found; assuming pre-loaded environment"
fi

# ---------------------------------------------------------------------------
# [3/9] locate trtexec
# ---------------------------------------------------------------------------
echo "=== [3/9] locate trtexec ==="
TRTEXEC="${TRTEXEC:-}"
if [ -z "$TRTEXEC" ]; then
  TRTEXEC="$(command -v trtexec 2>/dev/null || true)"
fi
if [ -z "$TRTEXEC" ]; then
  for cand in "$HOME/tensorrt/bin/trtexec" /usr/local/tensorrt/bin/trtexec \
              /opt/tensorrt/bin/trtexec /usr/src/tensorrt/bin/trtexec \
              /usr/local/bin/trtexec; do
    if [ -x "$cand" ]; then
      TRTEXEC="$cand"
      break
    fi
  done
fi
if [ -z "$TRTEXEC" ] || [ ! -x "$TRTEXEC" ]; then
  echo "WARN: trtexec not found; TensorRT 独立后端将跳过（CUDA torch / ORT 仍可运行）"
  TRTEXEC=""
else
  echo "trtexec: $TRTEXEC"
  # Some clusters only add the TensorRT bin dir to PATH; add lib dirs to
  # LD_LIBRARY_PATH so trtexec can start.
  TRT_BIN_DIR="$(dirname "$TRTEXEC")"
  TRT_ROOT_DIR="$(cd "$TRT_BIN_DIR/.." 2>/dev/null && pwd)"
  if [ -n "$TRT_ROOT_DIR" ] && [ -d "$TRT_ROOT_DIR" ]; then
    for f in $(find "$TRT_ROOT_DIR" -maxdepth 4 -name 'libnvinfer.so*' 2>/dev/null); do
      d="$(dirname "$f")"
      case ":$LD_LIBRARY_PATH:" in
        *":$d:"*) ;;
        *) export LD_LIBRARY_PATH="$d:$LD_LIBRARY_PATH" ;;
      esac
    done
  fi
  echo "LD_LIBRARY_PATH (tensorrt/cuda part):"
  echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -iE 'tensorrt|cuda|cudnn' || echo "(none)"
  if "$TRTEXEC" --help >/dev/null 2>&1; then
    echo "trtexec --help: OK"
  else
    echo "WARN: trtexec --help failed (architecture mismatch?); TRT 后端将跳过"
    TRTEXEC=""
  fi
fi

# ---------------------------------------------------------------------------
# [4/9] resolve a usable Python >= 3.8 (conda env reused across jobs)
# ---------------------------------------------------------------------------
echo "=== [4/9] python ==="
PY=""
if [ -n "${PYTHON:-}" ]; then
  if [ -x "$PYTHON" ]; then
    PY="$PYTHON"
  else
    PY="$(command -v "$PYTHON" 2>/dev/null || true)"
  fi
fi

CONDA_ROOT=""
if command -v conda >/dev/null 2>&1; then
  CONDA_ROOT="$(conda info --base 2>/dev/null || true)"
fi
if [ -z "$CONDA_ROOT" ]; then
  for d in "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3" /opt/conda /opt/miniforge3; do
    if [ -x "$d/bin/conda" ]; then
      CONDA_ROOT="$d"
      break
    fi
  done
fi

ENV_NAME="${CONDA_ENV_NAME:-cp310cu122}"
locate_env_py() {
  ENV_PY=""
  for d in "$CONDA_ROOT/envs/$ENV_NAME" "$HOME/.conda/envs/$ENV_NAME"; do
    if [ -x "$d/bin/python" ]; then
      ENV_PY="$d/bin/python"
      return 0
    fi
  done
  if [ -n "$CONDA_ROOT" ] && [ -x "$CONDA_ROOT/bin/conda" ]; then
    d="$("$CONDA_ROOT/bin/conda" env list 2>/dev/null | awk -v n="$ENV_NAME" '$1 == n {print $NF; exit}')"
    if [ -n "$d" ] && [ -x "$d/bin/python" ]; then
      ENV_PY="$d/bin/python"
      return 0
    fi
  fi
  return 1
}

if [ -z "$PY" ] && [ -n "$CONDA_ROOT" ] && [ -x "$CONDA_ROOT/bin/conda" ]; then
  if ! locate_env_py; then
    if [ "${CONDA_CREATE:-0}" = "1" ]; then
      echo "creating conda env '$ENV_NAME' with python=3.10 (CONDA_CREATE=1; see $LOG_DIR/conda_create.log)"
      if "$CONDA_ROOT/bin/conda" create -y -n "$ENV_NAME" python=3.10 pip \
          > "$LOG_DIR/conda_create.log" 2>&1; then
        echo "conda env created"
      else
        echo "ERROR: conda create failed; last lines of log:"
        tail -20 "$LOG_DIR/conda_create.log" || true
        exit 4
      fi
    else
      echo "ERROR: conda env '$ENV_NAME' not found."
      echo "  Please use the platform-provided environment (e.g. 'conda activate cp310cu122')"
      echo "  or set CONDA_ENV_NAME=<env>; set CONDA_CREATE=1 only if a fresh CPU env is intended."
      exit 4
    fi
  fi
  locate_env_py || true
  if [ -n "$ENV_PY" ]; then
    PY="$ENV_PY"
  fi
fi

if [ -z "$PY" ]; then
  for cand in python3 python "$HOME/miniforge3/bin/python" /opt/conda/bin/python \
              "$HOME/miniconda3/bin/python" "$HOME/anaconda3/bin/python"; do
    cpath="$(command -v "$cand" 2>/dev/null || true)"
    if [ -n "$cpath" ] && "$cpath" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      PY="$cpath"
      break
    fi
  done
fi

if [ -z "$PY" ] || [ ! -x "$PY" ]; then
  echo "ERROR: no usable Python >= 3.8 found."
  echo "  Options: 1) module load miniforge3/<version>;"
  echo "           2) set PYTHON=/path/to/python."
  exit 4
fi
echo "python: $PY ($("$PY" --version 2>&1))"

if ! "$PY" -m pip --version >/dev/null 2>&1; then
  "$PY" -m ensurepip --upgrade --user >/dev/null 2>&1 || true
fi
if ! "$PY" -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip unavailable for $PY"
  exit 4
fi

# ---------------------------------------------------------------------------
# [5/9] environment snapshot + light deps
# ---------------------------------------------------------------------------
echo "=== [5/9] environment snapshot + deps ==="
{
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host: $(hostname)"
  echo "uname: $(uname -m 2>/dev/null || true)"
  echo "python: $PY $("$PY" --version 2>&1)"
  echo "trtexec: $TRTEXEC"
  echo "modules: ${TRT_LOADED:-none} / ${CU_LOADED:-none} / ${DN_LOADED:-none}"
  echo "--- nvidia-smi ---"
  nvidia-smi 2>&1 || echo "nvidia-smi unavailable"
  echo "--- pip packages ---"
  "$PY" -m pip list 2>/dev/null | grep -Ei "numpy|pandas|pynvml|onnx|torch" || true
} > "$OUT_DIR/env/snapshot.txt" 2>&1
nvidia-smi -q > "$OUT_DIR/env/nvidia_smi_q.txt" 2>&1 || true

for pkg in numpy pandas pynvml; do
  if ! "$PY" -c "import $pkg" >/dev/null 2>&1; then
    echo "installing $pkg (best effort)"
    timeout 600 "$PY" -m pip install -q "$pkg" > "$LOG_DIR/pip_$pkg.log" 2>&1 \
      || echo "WARN: $pkg install failed (see logs/pip_$pkg.log)"
  fi
done
if ! "$PY" -c "import onnxruntime" >/dev/null 2>&1; then
  echo "installing onnxruntime-gpu (best effort; x86_64 only, aarch64 has no wheel)"
  timeout 900 "$PY" -m pip install -q onnxruntime-gpu > "$LOG_DIR/pip_ort_gpu.log" 2>&1 \
    || echo "WARN: onnxruntime-gpu install failed (see logs/pip_ort_gpu.log); ORT 后端将跳过"
fi

# ---------------------------------------------------------------------------
# [6/9] optional: export ONNX models (only when requested / models missing)
# ---------------------------------------------------------------------------
if [ "$MODE" = "models_only" ]; then
  echo "=== [6/9] export ONNX models ==="
  bash "$SCRIPT_DIR/export_models.sh" "$PY" "$MODEL_DIR" "$LOG_DIR"
  rc=$?
  echo "export finished rc=$rc; files in $MODEL_DIR:"
  ls -la "$MODEL_DIR" || true
  exit $rc
fi

ONNX_COUNT="$(find "$MODEL_DIR" -maxdepth 1 -name '*.onnx' 2>/dev/null | wc -l)"
if [ "$ONNX_COUNT" -eq 0 ] && [ "${EXPORT_MODELS:-0}" = "1" ]; then
  echo "=== [6/9] no models found; exporting with CPU torch ==="
  bash "$SCRIPT_DIR/export_models.sh" "$PY" "$MODEL_DIR" "$LOG_DIR" \
    || { echo "ERROR: model export failed"; exit 5; }
  ONNX_COUNT="$(find "$MODEL_DIR" -maxdepth 1 -name '*.onnx' 2>/dev/null | wc -l)"
fi
if [ "$ONNX_COUNT" -eq 0 ]; then
  echo "ERROR: no *.onnx in $MODEL_DIR."
  echo "  Either upload models/ (miniexperiment/models/*.onnx), or run"
  echo "  MODE=models_only sbatch job/job.slurm  to export them on the cluster."
  exit 5
fi
echo "=== [6/9] models ready ($ONNX_COUNT onnx files in $MODEL_DIR) ==="

# ---------------------------------------------------------------------------
# [7/9] benchmark matrix (build engines + measure)
# ---------------------------------------------------------------------------
echo "=== [7/9] benchmark matrix ==="
"$PY" "$SCRIPT_DIR/run_all.py" \
  --python "$PY" \
  --trtexec "$TRTEXEC" \
  --models-dir "$MODEL_DIR" \
  --engines-dir "$ENGINE_DIR" \
  --out "$RESULTS_CSV" \
  --log-dir "$LOG_DIR" \
  --reps "${REPS:-3}" \
  --duration-ms "${DURATION_MS:-20000}" \
  > "$LOG_DIR/run_all.log" 2>&1
RC=$?
echo "run_all rc=$RC (see $LOG_DIR/run_all.log for per-config details)"

if [ ! -s "$RESULTS_CSV" ]; then
  echo "ERROR: no results produced; inspect $LOG_DIR/run_all.log"
  exit 3
fi

# ---------------------------------------------------------------------------
# [8/9] summarize + package
# ---------------------------------------------------------------------------
echo "=== [8/9] summarize ==="
"$PY" "$SCRIPT_DIR/summarize.py" \
  --csv "$RESULTS_CSV" \
  --out "$SUMMARY_MD" \
  --failures "$LOG_DIR/failures.txt" \
  > "$LOG_DIR/summarize.log" 2>&1 || echo "WARN: summarize failed (see logs/summarize.log)"

tar -czf "$OUT_DIR.tar.gz" -C "$(dirname "$OUT_DIR")" "$(basename "$OUT_DIR")" \
  2>/dev/null || true

# ---------------------------------------------------------------------------
# [9/9] done
# ---------------------------------------------------------------------------
echo "=== [9/9] done ==="
echo "  results: $RESULTS_CSV"
echo "  summary: $SUMMARY_MD"
echo "  engines: $ENGINE_DIR"
echo "  tarball: $OUT_DIR.tar.gz"
echo "  To fetch:  scp 'scx7es6@<host>:~/$(basename "$OUT_DIR").tar.gz' ."
exit 0
