#!/usr/bin/env bash
# Environment acceptance probe: run this ON THE GPU COMPUTE NODE (via sbatch or
# as the console job's startup command), not on the login node.
set -uo pipefail

echo "=== [1/5] host ==="
hostname
uname -m
uname -r
cat /etc/os-release 2>/dev/null | head -2 || true

echo "=== [2/5] nvidia ==="
nvidia-smi -L 2>&1 | head -5 || echo "nvidia-smi unavailable"
nvidia-smi --query-gpu=name,driver_version,memory.total,power.draw --format=csv 2>&1 || true

echo "=== [3/5] modules (best effort) ==="
if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true
  module load "${CMAKE_MODULE:-cmake/3.26.3}" >/dev/null 2>&1 && echo "module: cmake OK" || echo "cmake module load failed"
  module load "${MINIFORGE_MODULE:-miniforge3/26.3.2-3}" >/dev/null 2>&1 && echo "module: miniforge OK" || echo "miniforge module load failed"
  module load "${GCC_MODULE:-compilers/gcc/11.3.0}" >/dev/null 2>&1 && echo "module: gcc OK" || echo "gcc module load failed"
  for cu in "${CUDA_MODULE:-}" compilers/cuda/12.2 cuda/12.2.0 cuda/12.2 compilers/cuda/11.8; do
    [ -n "$cu" ] || continue
    if module load "$cu" >/dev/null 2>&1; then echo "module: $cu"; break; fi
  done
  for dn in "${CUDNN_MODULE:-}" cudnn/8.9.5.29_cuda12.x cudnn/8.6.0.163_cuda11.x; do
    [ -n "$dn" ] || continue
    if module load "$dn" >/dev/null 2>&1; then echo "module: $dn"; break; fi
  done
  for trt in "${TRT_MODULE:-}" TensorRT/8.5.3.1-cuda11.8-cudnn8.6; do
    [ -n "$trt" ] || continue
    if module load "$trt" >/dev/null 2>&1; then echo "module: $trt"; break; fi
  done
else
  echo "no module command (container/bare-metal assumed)"
fi

echo "=== [4/5] python / runtimes ==="
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for cand in "$HOME/.conda/envs/cp310cu122/bin/python" "$HOME/.conda/envs/dlenergy/bin/python" \
              "$HOME/miniforge3/bin/python" /opt/conda/bin/python python3; do
    cpath="$(command -v "$cand" 2>/dev/null || true)"
    [ -n "$cpath" ] && PY="$cpath" && break
    [ -x "$cand" ] && PY="$cand" && break
  done
fi
echo "python: ${PY:-none}"
if [ -n "${PY:-}" ] && [ -x "$PY" ]; then
  "$PY" --version 2>&1
  "$PY" -c "import torch; print('torch', torch.__version__, 'cuda_ok=', torch.cuda.is_available())" 2>&1 || echo "torch: unavailable"
  "$PY" -c "import onnxruntime as ort; print('ort', ort.__version__, ort.get_available_providers())" 2>&1 || echo "onnxruntime: unavailable"
  "$PY" -c "import numpy,pandas,pynvml,onnx,onnxscript; print('deps OK')" 2>&1 || echo "some python deps missing"
fi

echo "=== [5/5] trtexec / ncu ==="
if command -v trtexec >/dev/null 2>&1; then
  T="$(command -v trtexec)"
  echo "trtexec: $T"
  file "$T" 2>/dev/null || true
  "$T" --help >/dev/null 2>&1 && echo "trtexec --help: OK" || echo "trtexec --help: FAILED"
else
  echo "trtexec: not found in PATH"
fi
if command -v ncu >/dev/null 2>&1; then
  ncu --version 2>&1 | head -1 || true
else
  echo "ncu: not found"
fi
echo "ACCEPT_DONE"
