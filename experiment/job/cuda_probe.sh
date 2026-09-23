#!/usr/bin/env bash
# CUDA toolchain probe on the ARM A100 node (run via sbatch, not on login node).
set -uo pipefail

if command -v module >/dev/null 2>&1; then
  module purge >/dev/null 2>&1 || true
  module load cmake/3.26.3 >/dev/null 2>&1 || true
  module load miniforge3/26.3.2-3 >/dev/null 2>&1 || true
  module load compilers/gcc/11.3.0 >/dev/null 2>&1 && echo "module gcc OK"
  module load compilers/cuda/12.2 >/dev/null 2>&1 && echo "module cuda OK"
  module load cudnn/8.9.5.29_cuda12.x >/dev/null 2>&1 && echo "module cudnn OK"
fi

echo "=== nvcc ==="
command -v nvcc && nvcc --version | tail -2 || echo "nvcc not found"

echo "=== compile & run probe ==="
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1
nvcc -arch=sm_80 -O2 cuda_probe.cu -o cuda_probe -lcublas \
  && echo "compile OK" || { echo "compile FAILED"; exit 2; }
./cuda_probe || echo "run FAILED"

echo "=== ncu ==="
if command -v ncu >/dev/null 2>&1; then
  ncu --version 2>&1 | head -1
else
  echo "ncu not found"
fi
