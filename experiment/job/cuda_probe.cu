#include <cstdio>
#include <cuda_runtime.h>
#include <cublas_v2.h>

__global__ void vec_add(float *a, float *b, float *c, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) c[i] = a[i] + b[i];
}

int main() {
  int rc = 0;
  int n = 1 << 22;
  float *a, *b, *c;
  cudaMalloc(&a, n * sizeof(float));
  cudaMalloc(&b, n * sizeof(float));
  cudaMalloc(&c, n * sizeof(float));
  cudaMemset(a, 0, n * sizeof(float));
  cudaMemset(b, 1, n * sizeof(float));
  vec_add<<<(n + 255) / 256, 256>>>(a, b, c, n);
  cudaError_t err = cudaDeviceSynchronize();
  if (err != cudaSuccess) {
    printf("kernel FAILED: %s\n", cudaGetErrorString(err));
    rc = 1;
  } else {
    printf("kernel OK\n");
  }

  // cuBLAS availability check (sgemm on small matrices)
  cublasHandle_t h;
  cublasStatus_t st = cublasCreate(&h);
  if (st != CUBLAS_STATUS_SUCCESS) {
    printf("cublasCreate FAILED: %d\n", (int)st);
    rc = 1;
  } else {
    const int m = 128, k = 128, ncols = 128;
    float *A, *B, *Cmat;
    float alpha = 1.0f, beta = 0.0f;
    cudaMalloc(&A, m * k * sizeof(float));
    cudaMalloc(&B, k * ncols * sizeof(float));
    cudaMalloc(&Cmat, m * ncols * sizeof(float));
    cudaMemset(A, 1, m * k * sizeof(float));
    cudaMemset(B, 1, k * ncols * sizeof(float));
    st = cublasSgemm(h, CUBLAS_OP_N, CUBLAS_OP_N,
                     m, ncols, k, &alpha, A, m, B, k, &beta, Cmat, m);
    if (st != CUBLAS_STATUS_SUCCESS) {
      printf("cublasSgemm FAILED: %d\n", (int)st);
      rc = 1;
    } else {
      printf("cublasSgemm OK\n");
    }
    cublasDestroy(h);
    cudaFree(A); cudaFree(B); cudaFree(Cmat);
  }
  cudaFree(a); cudaFree(b); cudaFree(c);
  printf("PROBE_DONE rc=%d\n", rc);
  return rc;
}
