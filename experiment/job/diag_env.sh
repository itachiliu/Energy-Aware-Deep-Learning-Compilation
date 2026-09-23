#!/usr/bin/env bash
# Diagnostic job: print python/conda/module environment of the GPU node.
# Run:  sbatch job/diag_env.sh ; then cat ~/slurm-<jobid>.out
#SBATCH -N 1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH -t 00:10:00
#SBATCH -J diag-python-env

set +e
echo "=== which python / python3 ==="
for c in python python3; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "-- $c -> $(command -v $c)"
    "$c" --version 2>&1
  else
    echo "-- $c not found"
  fi
done

echo "=== common python locations ==="
ls -1 /usr/bin/python* /usr/local/bin/python* /opt/conda/bin/python* \
  /opt/*/bin/python* "$HOME"/miniconda3/bin/python* "$HOME"/anaconda3/bin/python* 2>/dev/null

echo "=== pip / ensurepip check ==="
for c in python python3; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "-- $c pip:"
    "$c" -m pip --version 2>&1 | head -2
    echo "-- $c ensurepip:"
    "$c" -m ensurepip --version 2>&1 | head -2
  fi
done

echo "=== conda ==="
if command -v conda >/dev/null 2>&1; then
  conda info --base 2>&1
  conda env list 2>&1
else
  echo "conda not found"
fi

echo "=== module ==="
if command -v module >/dev/null 2>&1; then
  module avail 2>&1 | head -60
else
  echo "module command not found"
fi

echo "=== tensorrt / trtexec ==="
if command -v module >/dev/null 2>&1; then
  module avail 2>&1 | grep -iE "tensorrt|cuda/11|cudnn/8.6" || true
fi
for c in trtexec nvcc; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "-- $c -> $(command -v $c)"
  else
    echo "-- $c not found"
  fi
done
echo "TRT_ROOT=${TENSORRT_ROOT:-unset} TENSORRT_HOME=${TENSORRT_HOME:-unset} LD_LIBRARY_PATH="
echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -iE "tensorrt|cuda|cudnn" || echo "(no cuda/cudnn/trt paths in LD_LIBRARY_PATH)"

echo "=== env (python/conda/cuda related) ==="
env | grep -iE 'python|conda|cuda|virtual_env|^PATH=' | sort

echo "=== os ==="
head -3 /etc/os-release 2>/dev/null

echo "=== nvidia-smi ==="
nvidia-smi 2>&1 | head -14

echo "DIAG_DONE"
