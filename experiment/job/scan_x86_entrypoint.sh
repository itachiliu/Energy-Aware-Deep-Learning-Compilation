#!/usr/bin/env bash
# ============================================================================
# x86 (RTX 4090 / 5090) compiler-decision scan:
#   preflight -> modules -> python -> env snapshot -> ONNX export ->
#   ORT graph-opt/batch matrix + PyTorch eager matrix -> summary
# Optional TensorRT stage when trtexec works on this node (ENABLE_TRT=1).
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${OUT_DIR:-$(pwd)/scan_x86_out_$(date +%Y%m%d_%H%M%S)}"
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
MODELS="${MODELS:-}"
ENABLE_TRT="${ENABLE_TRT:-0}"
ENABLE_COMPILE="${ENABLE_COMPILE:-1}"
COMPILE_MODE="${COMPILE_MODE:-default}"

echo "=== [1/8] preflight ==="
mkdir -p "$OUT_DIR/env" "$LOG_DIR" "$MODEL_DIR"
echo "OUT_DIR=$OUT_DIR"
echo "MODEL_DIR=$MODEL_DIR"
echo "REPS=$REPS DURATION_S=$DURATION_S BATCHES=$BATCHES GRAPH_OPTS=$GRAPH_OPTS"
echo "EXTRA_MODELS=$EXTRA_MODELS ENABLE_TRT=$ENABLE_TRT"
echo "MODELS=${MODELS:-<default three>}"
echo "ENABLE_COMPILE=$ENABLE_COMPILE COMPILE_MODE=$COMPILE_MODE"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L 2>/dev/null | head -5 || true
else
  echo "WARN: nvidia-smi not found; this job must run on a GPU node"
fi

echo "=== [2/8] platform modules (best effort) ==="
if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true
  load_first() {
    for m in "$@"; do
      [ -n "$m" ] || continue
      if module load "$m" >/dev/null 2>&1; then echo "module loaded: $m"; return 0; fi
    done
    echo "WARN: none of these modules loaded: $*"
    return 1
  }
  load_first "${MINIFORGE_MODULE:-}" miniforge3/26.3.2-3 miniforge3/24.1 miniforge3 || true
  load_first "${GCC_MODULE:-}" gcc/11.3.0 gcc/12.4.0 gcc/13.3.0 \
             compilers/gcc/11.3.0 compilers/gcc/12.2.0 || true
  load_first "${CUDA_MODULE:-}" cuda/12.8 cuda/12.9 cuda/12.6 cuda/12.4 \
             cuda/12.8.0 compilers/cuda/12.8 compilers/cuda/12.2 || true
  # cuDNN module is skipped by default: torch and onnxruntime in the venv bring
  # their own cuDNN 9 wheels, and preloading the module's cuDNN 8 can make the
  # ORT CUDA EP fail to initialise (it then falls back to the CPU silently).
  if [ "${LOAD_CUDNN_MODULE:-0}" = "1" ]; then
    load_first "${CUDNN_MODULE:-}" cudnn/9.6.0.74_cuda12 cudnn/8.9.6.50_cuda12 || true
  else
    echo "cuDNN module skipped (LOAD_CUDNN_MODULE=1 to force it); using the env's wheels"
  fi
  if [ "$ENABLE_TRT" = "1" ]; then
    load_first "${TRT_MODULE:-}" TensorRT/10.8 TensorRT/10.7 TensorRT/10.6 \
               TensorRT/8.6.1 TensorRT/8.5.3.1-cuda11.8-cudnn8.6 || true
  fi
else
  echo "module command not found; assuming pre-loaded environment"
fi

echo "=== [3/8] python ==="
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  for cand in "$HOME/dlxvenv/bin/python" "$HOME/dlxc/bin/python" "$HOME/dlx5090/bin/python" \
              "$HOME/.conda/envs/dlx/bin/python" "$HOME/.conda/envs/cp310cu122/bin/python" \
              "$HOME/miniconda3/envs/dlx/bin/python" "$HOME/miniforge3/envs/dlx/bin/python" \
              "$HOME/.conda/envs/dlenergy/bin/python"; do
    if [ -x "$cand" ]; then PYTHON="$cand"; break; fi
  done
fi
if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  echo "ERROR: no python>=3.8 found. Run 'bash job/setup_env_x86.sh' first,"
  echo "       or set PYTHON=/path/to/python."
  exit 1
fi
echo "python: $PYTHON"
"$PYTHON" - <<'EOF'
import sys
print("python", sys.version.split()[0])
try:
    import torch
    print("torch", torch.__version__, "cuda_ok", torch.cuda.is_available())
except Exception as e:
    print("torch unavailable:", e)
try:
    import onnxruntime as ort
    print("ort", ort.__version__, ort.get_available_providers())
except Exception as e:
    print("onnxruntime unavailable:", e)
EOF

echo "=== [4/8] environment snapshot ==="
{
  echo "host: $(hostname)"
  uname -a
  nvidia-smi --query-gpu=name,driver_version,memory.total,power.draw,power.limit \
    --format=csv 2>/dev/null || true
  echo "modules:"
  module list 2>/dev/null || true
} > "$OUT_DIR/env/snapshot.txt" 2>&1
cat "$OUT_DIR/env/snapshot.txt"

echo "=== [4b/8] CUDA libraries from the environment wheels ==="
NVLIB="$("$PYTHON" - <<'PYEOF'
import glob, os, site
dirs = []
for sp in set(list(site.getsitepackages()) + [site.getusersitepackages()]):
    dirs += sorted(glob.glob(os.path.join(sp, "nvidia", "*", "lib")))
print(":".join(dirs))
PYEOF
)"
if [ -n "$NVLIB" ]; then
  export LD_LIBRARY_PATH="$NVLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  echo "added $(echo "$NVLIB" | tr ':' '\n' | wc -l) nvidia wheel lib dirs to LD_LIBRARY_PATH"
else
  echo "WARN: no nvidia/*/lib dirs in the env; is this torch a CPU build?"
fi

echo "=== [4c/8] runtime self-test (must pass before measuring) ==="
if "$PYTHON" - <<'PYEOF'
import sys

ok = True

try:
    import torch
    if not torch.cuda.is_available():
        print("FAIL torch: cuda not available")
        ok = False
    else:
        a = torch.randn(512, 512, device="cuda")
        (a @ a).sum().item()
        torch.cuda.synchronize()
        print(f"OK   torch {torch.__version__} on {torch.cuda.get_device_name(0)}")
except Exception as exc:
    print(f"FAIL torch: {type(exc).__name__}: {exc}")
    ok = False

try:
    import numpy as np
    from onnx import TensorProto, helper
    import onnxruntime as ort

    print(f"     ort version: {ort.__version__}")
    print(f"     compiled-in providers: {ort.get_available_providers()}")
    if not hasattr(ort, "preload_dlls"):
        print("     preload_dlls: unavailable in this ort build")
    else:
        try:
            ort.preload_dlls()
            print("     preload_dlls: ok")
        except Exception as exc:
            print(f"     preload_dlls: {type(exc).__name__}: {exc}")

    graph = helper.make_graph(
        [helper.make_node("MatMul", ["X", "W"], ["Y"])],
        "selftest",
        [helper.make_tensor_value_info("X", TensorProto.FLOAT, [16, 16]),
         helper.make_tensor_value_info("W", TensorProto.FLOAT, [16, 16])],
        [helper.make_tensor_value_info("Y", TensorProto.FLOAT, [16, 16])],
    )
    # Pin the opset explicitly: make_model() defaults to the newest opset the
    # installed onnx knows, which ORT refuses ("opset N under development").
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    so = ort.SessionOptions()
    so.log_severity_level = 1     # surface the loader error naming the culprit
    sess = ort.InferenceSession(
        model.SerializeToString(), sess_options=so,
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    providers = sess.get_providers()
    print(f"     session providers: {providers}")
    if "CUDAExecutionProvider" not in providers:
        print("FAIL ort: CUDA EP did not initialise; see the loader output above")
        ok = False
    else:
        sess.run(None, {"X": np.zeros((16, 16), np.float32),
                        "W": np.zeros((16, 16), np.float32)})
        print("OK   onnxruntime CUDA EP")
except Exception as exc:
    print(f"FAIL ort: {type(exc).__name__}: {exc}")
    ok = False

sys.exit(0 if ok else 1)
PYEOF
then
  echo "self-test passed"
else
  echo "ERROR: runtime self-test failed; aborting before spending GPU hours."
  echo "       If the loader above says 'libcublas.so.13' or 'libcudart.so.13' is"
  echo "       missing, the installed onnxruntime-gpu is a CUDA 13 build while the"
  echo "       env carries CUDA 12 libraries. Fix on the login node with:"
  echo "         \$PYTHON -m pip install --no-cache-dir 'onnxruntime-gpu<1.23'"
  echo "       Or measure the torch backends only: SKIP_ORT=1 sbatch job/scan_x86.slurm"
  echo "       See job/README_x86.md, 'onnxruntime 的 CUDA EP 起不来怎么办'."
  exit 1
fi

echo "=== [5/8] prepare dynamic-batch onnx models ==="
NEEDED="mobilenetv2 resnet50 vit_b_16"
if [ "$EXTRA_MODELS" = "1" ]; then NEEDED="$NEEDED resnet18 mobilenetv3_large"; fi
if [ -n "$MODELS" ]; then NEEDED="$(echo "$MODELS" | tr ',' ' ')"; fi
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

echo "=== [6/8] run ORT + PyTorch matrix ==="
EXTRA_FLAG=""
if [ "$EXTRA_MODELS" = "1" ]; then EXTRA_FLAG="--extra-models"; fi
MODELS_FLAG=""
if [ -n "$MODELS" ]; then MODELS_FLAG="--models $MODELS"; fi
COMPILE_FLAG=""
if [ "$ENABLE_COMPILE" = "1" ]; then COMPILE_FLAG="--with-compile"; fi
SKIP_ORT_FLAG=""
if [ "${SKIP_ORT:-0}" = "1" ]; then SKIP_ORT_FLAG="--skip-ort"; fi
"$PYTHON" "$SCRIPT_DIR/run_scan_all.py" \
  --python "$PYTHON" --models-dir "$MODEL_DIR" \
  --out "$RESULTS_CSV" --log-dir "$LOG_DIR" \
  --reps "$REPS" --duration-s "$DURATION_S" \
  --batches "$BATCHES" --graph-opts "$GRAPH_OPTS" \
  --compile-mode "$COMPILE_MODE" $EXTRA_FLAG $MODELS_FLAG $COMPILE_FLAG $SKIP_ORT_FLAG

echo "=== [7/8] summarize ==="
"$PYTHON" "$SCRIPT_DIR/summarize_scan.py" \
  --csv "$RESULTS_CSV" --out "$SUMMARY_MD" --agg "$AGG_CSV" \
  --failures "$LOG_DIR/failures.txt" || true

if [ "$ENABLE_TRT" = "1" ]; then
  echo "=== [7b/8] optional TensorRT stage ==="
  TRT_BIN="$(command -v trtexec 2>/dev/null || true)"
  if [ -z "$TRT_BIN" ]; then
    echo "WARN: trtexec not found; skipping TensorRT stage"
  else
    TRT_MODEL_DIR="$OUT_DIR/models_trt"
    mkdir -p "$TRT_MODEL_DIR"
    if [ ! -f "$TRT_MODEL_DIR/resnet50.onnx" ]; then
      "$PYTHON" "$SCRIPT_DIR/fetch_models.py" --out "$TRT_MODEL_DIR" --opset 13 --size 224 || \
        echo "WARN: static ONNX export for TensorRT failed; skipping TRT stage"
    fi
    if ls "$TRT_MODEL_DIR"/*.onnx >/dev/null 2>&1; then
      "$PYTHON" "$SCRIPT_DIR/run_trt.py" \
        --trtexec "$TRT_BIN" --models-dir "$TRT_MODEL_DIR" \
        --engines-dir "$OUT_DIR/engines" --out "$OUT_DIR/results_trt.csv" \
        --log-dir "$OUT_DIR/logs_trt" --precisions "${TRT_PRECISIONS:-tf32,fp32,fp16}" \
        --reps "${TRT_REPS:-3}" --duration-ms "${TRT_DURATION_MS:-20000}" || \
        echo "WARN: TensorRT stage returned non-zero"
    fi
  fi
fi

echo "=== [8/8] done ==="
echo "results: $RESULTS_CSV"
echo "summary: $SUMMARY_MD"
echo "SCAN_DONE"
