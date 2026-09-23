#!/usr/bin/env bash
# ============================================================================
# x86 + NVIDIA (RTX 4090 / 5090) environment probe.
# Run it on a GPU compute node, not on the login node:
#   sbatch job/probe_x86.slurm
#   cat ~/slurm-<JOBID>-probe.out
# Everything is also written to $OUT_DIR/probe_report.txt for one-shot copy-back.
# ============================================================================
set -uo pipefail

OUT_DIR="${OUT_DIR:-$(pwd)/probe_out_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT_DIR"
REPORT="$OUT_DIR/probe_report.txt"
exec > >(tee "$REPORT") 2>&1

echo "=== [1/8] host ==="
hostname
uname -m
uname -r
head -3 /etc/os-release 2>/dev/null || true
echo "node=${SLURM_JOB_NODELIST:-n/a} partition=${SLURM_JOB_PARTITION:-n/a}"

echo
echo "=== [2/8] GPU ==="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L 2>&1 | head -8
  echo "-- capacity --"
  nvidia-smi --query-gpu=index,name,driver_version,memory.total,power.draw,power.limit \
    --format=csv 2>&1 | head -8
  echo "-- compute_cap (needs driver >= R550; N/A is fine) --"
  nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>&1 | head -8
else
  echo "nvidia-smi: NOT FOUND (did this job land on a GPU node?)"
fi
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"

echo
echo "=== [3/8] modules available (filtered) ==="
if command -v module >/dev/null 2>&1; then
  module avail 2>&1 | tr ' ' '\n' \
    | grep -Ei 'cuda|cudnn|tensorrt|trt|gcc|compilers|cmake|miniforge|miniconda|anaconda|python' \
    | sed 's/^[[:space:]]*//' | grep -v '^$' | sort -u | head -80
else
  echo "no module command"
fi

echo
echo "=== [4/8] module load trials ==="
if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true
  try_module() {
    local m="$1"
    [ -n "$m" ] || return 0
    if module load "$m" >/dev/null 2>&1; then
      echo "  OK   $m"
    else
      echo "  fail $m"
    fi
  }
  echo "-- miniforge / conda --"
  for m in "${MINIFORGE_MODULE:-}" miniforge3/26.3.2-3 miniforge3/24.1 miniforge3 miniconda3 anaconda3; do
    try_module "$m"
  done
  echo "-- gcc / cmake --"
  for m in "${GCC_MODULE:-}" compilers/gcc/11.3.0 compilers/gcc/12.2.0 compilers/gcc/13.2.0 gcc/11.3.0 gcc/12.2.0 cmake/3.26.3 cmake/3.31.6; do
    try_module "$m"
  done
  echo "-- cuda (5090/sm_120 needs >= 12.8) --"
  for m in "${CUDA_MODULE:-}" cuda/12.8.0 cuda/12.8 compilers/cuda/12.8 cuda/12.6.0 cuda/12.6 \
           compilers/cuda/12.6 cuda/12.4.0 compilers/cuda/12.4 cuda/12.2.0 compilers/cuda/12.2 \
           cuda/12.2 compilers/cuda/11.8 cuda/11.8.0; do
    try_module "$m"
  done
  echo "-- cudnn --"
  for m in "${CUDNN_MODULE:-}" cudnn/8.9.6.50_cuda12 cudnn/9.6.0.74_cuda12 \
           cudnn/9.8.0.87_cuda12.x cudnn/9.1.0.70_cuda12.x cudnn/8.9.5.29_cuda12.x \
           cudnn/8.9.4.25_cuda12.x cudnn/8.8.1.3_cuda12.x; do
    try_module "$m"
  done
  echo "-- TensorRT (5090/sm_120 needs >= 10.8) --"
  for m in "${TRT_MODULE:-}" TensorRT/10.8 TensorRT/10.7 TensorRT/10.6 TensorRT/10.5 \
           TensorRT/8.6.1 TensorRT/8.5.3.1-cuda11.8-cudnn8.6; do
    try_module "$m"
  done
  echo "-- effective module list --"
  module list 2>&1 | tail -20
else
  echo "no module command (container/bare-metal assumed)"
fi

echo
echo "=== [5/8] trtexec / ncu discovery ==="
TRT_BIN="$(command -v trtexec 2>/dev/null || true)"
if [ -z "$TRT_BIN" ]; then
  for root in /home/bingxing2/apps /opt /usr/local /usr/local/cuda /opt/tensorrt; do
    [ -d "$root" ] || continue
    found="$(timeout 25 find "$root" -maxdepth 5 -type f -name trtexec 2>/dev/null | head -1)"
    if [ -n "$found" ]; then TRT_BIN="$found"; break; fi
  done
fi
if [ -n "$TRT_BIN" ]; then
  echo "trtexec: $TRT_BIN"
  file "$TRT_BIN" 2>/dev/null || true
  if "$TRT_BIN" --help >/dev/null 2>&1; then echo "trtexec --help: OK"; else echo "trtexec --help: FAILED"; fi
  "$TRT_BIN" --version 2>&1 | grep -i tensorrt | head -2 || true
else
  echo "trtexec: not found"
fi
if command -v ncu >/dev/null 2>&1; then
  echo "ncu: $(command -v ncu)"
  ncu --version 2>&1 | head -2 || true
  echo "-- ncu permission test (DRAM counters; may fail without root) --"
  timeout 150 ncu --metrics dram__bytes_read.sum,dram__bytes_write.sum \
    --target-processes all python3 -c "print(1)" 2>&1 | tail -12 || true
else
  echo "ncu: not found"
fi

echo
echo "=== [5b/8] ncu DRAM-counter test on a real CUDA kernel ==="
NCU_BIN="$(command -v ncu 2>/dev/null || true)"
NVCC_BIN="$(command -v nvcc 2>/dev/null || true)"
if [ -n "$NCU_BIN" ] && [ -n "$NVCC_BIN" ]; then
  cat > "$OUT_DIR/ncu_kernel_probe.cu" <<'CUEOF'
#include <cstdio>
__global__ void touch(float *a, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) a[i] = a[i] * 1.000001f + 0.5f;
}
int main() {
  int n = 1 << 22;
  size_t bytes = (size_t)n * sizeof(float);
  float *a, *b;
  cudaMalloc(&a, bytes);
  cudaMalloc(&b, bytes);
  cudaMemset(a, 1, bytes);
  cudaMemset(b, 2, bytes);
  for (int r = 0; r < 20; ++r) {
    touch<<<(n + 255) / 256, 256>>>(a, n);
    touch<<<(n + 255) / 256, 256>>>(b, n);
  }
  cudaError_t e = cudaDeviceSynchronize();
  printf("kernel %s\n", e == cudaSuccess ? "OK" : cudaGetErrorString(e));
  cudaFree(a);
  cudaFree(b);
  return e == cudaSuccess ? 0 : 1;
}
CUEOF
  if "$NVCC_BIN" -arch=native -O2 "$OUT_DIR/ncu_kernel_probe.cu" \
       -o "$OUT_DIR/ncu_kernel_probe" 2>"$OUT_DIR/nvcc.log"; then
    "$OUT_DIR/ncu_kernel_probe" 2>&1 | tail -2 | sed 's/^/  plain run: /'
    echo "  -- ncu on a real kernel (this decides whether DRAM counts are usable) --"
    timeout 300 "$NCU_BIN" --metrics dram__bytes_read.sum,dram__bytes_write.sum \
      --launch-count 2 --target-processes all \
      "$OUT_DIR/ncu_kernel_probe" 2>&1 | tail -22 | sed 's/^/  /'
  else
    echo "  nvcc compile failed:"
    tail -5 "$OUT_DIR/nvcc.log" | sed 's/^/  /'
  fi
else
  echo "  skipped: nvcc=$NVCC_BIN ncu=$NCU_BIN (run nvcc/ncu discovery above)"
fi

echo
echo "=== [6/8] python interpreters ==="
echo "-- conda envs on disk --"
ls -d "$HOME"/.conda/envs/*/ "$HOME"/miniconda3/envs/*/ "$HOME"/miniforge3/envs/*/ 2>/dev/null || echo "  none found"
if command -v conda >/dev/null 2>&1; then conda env list 2>&1 | head -20; fi
for cand in "$HOME/dlxvenv/bin/python" "$HOME/dlxc/bin/python" \
            "$HOME/.conda/envs/cp310cu122/bin/python" "$HOME/.conda/envs/dlx/bin/python" \
            "$HOME/.conda/envs/dlenergy/bin/python" "$HOME/miniconda3/bin/python" \
            "$HOME/miniforge3/bin/python" /opt/conda/bin/python python3; do
  if command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ]; then
    echo "-- $cand --"
    "$cand" --version 2>&1
    "$cand" -c "import torch; print('  torch',torch.__version__,'cuda_ok',torch.cuda.is_available())" 2>&1 | head -3
    "$cand" -c "import onnxruntime as ort; print('  ort',ort.__version__,ort.get_available_providers())" 2>&1 | head -3
  fi
done

echo
echo "=== [7/8] real ViT-B/16 ONNX export test (no attention surgery) ==="
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for cand in "$HOME/dlxvenv/bin/python" "$HOME/dlxc/bin/python" \
              "$HOME/.conda/envs/dlx/bin/python" "$HOME/.conda/envs/cp310cu122/bin/python" \
              "$HOME/.conda/envs/dlenergy/bin/python" "$HOME/miniforge3/bin/python" python3; do
    if command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ]; then PY="$cand"; break; fi
  done
fi
if [ -n "$PY" ]; then
  "$PY" - >"$OUT_DIR/vit_export_test.txt" 2>&1 <<'PYEOF'
import sys
try:
    import torch, torchvision
except Exception as exc:
    print("skipped: torch/torchvision missing:", exc)
    sys.exit(0)
print("torch", torch.__version__, "torchvision", torchvision.__version__)
import torchvision.models as M
m = M.vit_b_16(weights=None).eval()
x = torch.zeros(1, 3, 224, 224)
for kw in ({"dynamo": False}, {}):
    try:
        torch.onnx.export(m, x, "/tmp/_vit_probe.onnx", input_names=["input"],
                          output_names=["output"], opset_version=17, **kw)
        print("ViT real-model export: OK", kw)
        break
    except Exception as exc:
        print("ViT export failed with", kw, "->", type(exc).__name__, str(exc)[:200])
PYEOF
  tail -12 "$OUT_DIR/vit_export_test.txt"
else
  echo "  no python interpreter found"
fi

echo
echo "=== [8/8] usable summary ==="
echo "arch=$(uname -m)"
echo "gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
echo "power_readable_w=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null | head -1)"
echo "trtexec=${TRT_BIN:-none}"
echo "python=${PY:-none}"
echo
echo "PROBE_DONE"
echo "report: $REPORT"
