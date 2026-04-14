#include <cuda_runtime.h>

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#define CUDA_CHECK(call) do { \
  cudaError_t e = (call); \
  if (e != cudaSuccess) { \
    std::cerr << "CUDA error: " << cudaGetErrorString(e) << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
    std::exit(1); \
  } \
} while (0)

struct Args {
  std::string imgs_path;
  std::string labels_path;
  std::string weights_path;
  int n = 10000;
  int nin = 784;
  int nneurons = 150;
  int fps = 15;
  int batch = 2048;
  int warmup = 5;
  int repeat = 2000;
  float pixel_th = 0.3f;
};

bool parse_args(int argc, char** argv, Args& a) {
  for (int i = 1; i < argc; ++i) {
    std::string k = argv[i];
    auto need = [&](int n) { return i + n < argc; };
    if (k == "--imgs" && need(1)) a.imgs_path = argv[++i];
    else if (k == "--labels" && need(1)) a.labels_path = argv[++i];
    else if (k == "--weights" && need(1)) a.weights_path = argv[++i];
    else if (k == "--n" && need(1)) a.n = std::stoi(argv[++i]);
    else if (k == "--nin" && need(1)) a.nin = std::stoi(argv[++i]);
    else if (k == "--nneurons" && need(1)) a.nneurons = std::stoi(argv[++i]);
    else if (k == "--fps" && need(1)) a.fps = std::stoi(argv[++i]);
    else if (k == "--batch" && need(1)) a.batch = std::stoi(argv[++i]);
    else if (k == "--warmup" && need(1)) a.warmup = std::stoi(argv[++i]);
    else if (k == "--repeat" && need(1)) a.repeat = std::stoi(argv[++i]);
    else if (k == "--pixel-th" && need(1)) a.pixel_th = std::stof(argv[++i]);
    else {
      std::cerr << "Unknown/invalid arg: " << k << std::endl;
      return false;
    }
  }
  return !a.imgs_path.empty() && !a.labels_path.empty() && !a.weights_path.empty();
}

template <typename T>
bool load_bin(const std::string& path, std::vector<T>& out, size_t count) {
  std::ifstream f(path, std::ios::binary);
  if (!f) return false;
  out.resize(count);
  f.read(reinterpret_cast<char*>(out.data()), static_cast<std::streamsize>(count * sizeof(T)));
  return f.good() || f.eof();
}

__global__ void potential_kernel(
    const float* imgs,
    const int8_t* weights,
    int32_t* potentials,
    int nimgs,
    int nin,
    int nneurons,
    float pixel_th) {
  int neuron = blockIdx.x * blockDim.x + threadIdx.x;
  int img = blockIdx.y * blockDim.y + threadIdx.y;
  if (neuron >= nneurons || img >= nimgs) return;

  const float* x = imgs + static_cast<size_t>(img) * nin;
  const int8_t* w = weights + static_cast<size_t>(neuron) * nin;
  int32_t sum = 0;
  for (int i = 0; i < nin; ++i) {
    if (x[i] > pixel_th) {
      int32_t wi = static_cast<int32_t>(w[i]);
      if (wi > 0) sum += wi;
    }
  }
  potentials[static_cast<size_t>(img) * nneurons + neuron] = sum;
}

__global__ void argmax_kernel(const int32_t* potentials, int32_t* pred_cls, int nimgs, int nneurons, int fps) {
  int img = blockIdx.x * blockDim.x + threadIdx.x;
  if (img >= nimgs) return;

  const int32_t* p = potentials + static_cast<size_t>(img) * nneurons;
  int best_idx = 0;
  int32_t best_val = p[0];
  for (int j = 1; j < nneurons; ++j) {
    int32_t v = p[j];
    if (v > best_val) {
      best_val = v;
      best_idx = j;
    }
  }
  if (best_val <= 0) best_idx = 0;
  pred_cls[img] = best_idx / fps;
}

int main(int argc, char** argv) {
  Args a;
  if (!parse_args(argc, argv, a)) {
    std::cerr << "Usage: gpu_ann_kernel_bench --imgs <bin> --labels <bin> --weights <bin> [--n 10000 --nin 784 --nneurons 150 --fps 15 --batch 2048 --warmup 5 --repeat 2000 --pixel-th 0.3]" << std::endl;
    return 2;
  }

  std::vector<float> h_imgs;
  std::vector<uint8_t> h_labels;
  std::vector<int8_t> h_weights;

  if (!load_bin<float>(a.imgs_path, h_imgs, static_cast<size_t>(a.n) * a.nin)) {
    std::cerr << "Failed to load imgs: " << a.imgs_path << std::endl;
    return 3;
  }
  if (!load_bin<uint8_t>(a.labels_path, h_labels, static_cast<size_t>(a.n))) {
    std::cerr << "Failed to load labels: " << a.labels_path << std::endl;
    return 4;
  }
  if (!load_bin<int8_t>(a.weights_path, h_weights, static_cast<size_t>(a.nneurons) * a.nin)) {
    std::cerr << "Failed to load weights: " << a.weights_path << std::endl;
    return 5;
  }

  float* d_imgs = nullptr;
  int8_t* d_weights = nullptr;
  int32_t* d_pot = nullptr;
  int32_t* d_pred = nullptr;

  CUDA_CHECK(cudaMalloc(&d_imgs, h_imgs.size() * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_weights, h_weights.size() * sizeof(int8_t)));
  CUDA_CHECK(cudaMalloc(&d_pot, static_cast<size_t>(a.batch) * a.nneurons * sizeof(int32_t)));
  CUDA_CHECK(cudaMalloc(&d_pred, static_cast<size_t>(a.n) * sizeof(int32_t)));

  CUDA_CHECK(cudaMemcpy(d_imgs, h_imgs.data(), h_imgs.size() * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_weights, h_weights.data(), h_weights.size() * sizeof(int8_t), cudaMemcpyHostToDevice));

  int warm_n = std::min(a.batch, a.n);
  dim3 block_p(16, 16);
  dim3 grid_p((a.nneurons + block_p.x - 1) / block_p.x, (warm_n + block_p.y - 1) / block_p.y);
  dim3 block_a(256);
  dim3 grid_a((warm_n + block_a.x - 1) / block_a.x);

  for (int i = 0; i < a.warmup; ++i) {
    potential_kernel<<<grid_p, block_p>>>(d_imgs, d_weights, d_pot, warm_n, a.nin, a.nneurons, a.pixel_th);
    argmax_kernel<<<grid_a, block_a>>>(d_pot, d_pred, warm_n, a.nneurons, a.fps);
  }
  CUDA_CHECK(cudaDeviceSynchronize());

  cudaEvent_t ev_start, ev_end;
  CUDA_CHECK(cudaEventCreate(&ev_start));
  CUDA_CHECK(cudaEventCreate(&ev_end));

  CUDA_CHECK(cudaEventRecord(ev_start));

  int repeat = std::max(1, a.repeat);
  for (int r = 0; r < repeat; ++r) {
    for (int s = 0; s < a.n; s += a.batch) {
      int cur = std::min(a.batch, a.n - s);
      const float* d_imgs_s = d_imgs + static_cast<size_t>(s) * a.nin;
      int32_t* d_pred_s = d_pred + s;

      dim3 g_p((a.nneurons + block_p.x - 1) / block_p.x, (cur + block_p.y - 1) / block_p.y);
      dim3 g_a((cur + block_a.x - 1) / block_a.x);

      potential_kernel<<<g_p, block_p>>>(d_imgs_s, d_weights, d_pot, cur, a.nin, a.nneurons, a.pixel_th);
      argmax_kernel<<<g_a, block_a>>>(d_pot, d_pred_s, cur, a.nneurons, a.fps);
    }
  }

  CUDA_CHECK(cudaEventRecord(ev_end));
  CUDA_CHECK(cudaEventSynchronize(ev_end));

  float elapsed_ms = 0.0f;
  CUDA_CHECK(cudaEventElapsedTime(&elapsed_ms, ev_start, ev_end));

  std::vector<int32_t> h_pred(static_cast<size_t>(a.n));
  CUDA_CHECK(cudaMemcpy(h_pred.data(), d_pred, static_cast<size_t>(a.n) * sizeof(int32_t), cudaMemcpyDeviceToHost));

  int correct = 0;
  for (int i = 0; i < a.n; ++i) {
    if (h_pred[i] == static_cast<int32_t>(h_labels[i])) ++correct;
  }

  double elapsed_s = static_cast<double>(elapsed_ms) / 1000.0;
  double total_imgs = static_cast<double>(a.n) * static_cast<double>(repeat);
  double ms_per_img = (total_imgs > 0.0) ? (static_cast<double>(elapsed_ms) / total_imgs) : 0.0;
  double throughput = (elapsed_s > 0.0) ? (total_imgs / elapsed_s) : 0.0;
  double acc = static_cast<double>(correct) / static_cast<double>(a.n);

  std::ostringstream oss;
  oss.setf(std::ios::fixed);
  oss.precision(12);
  oss << "{"
      << "\"n_images\":" << a.n << ","
      << "\"correct\":" << correct << ","
      << "\"acc_ann\":" << acc << ","
      << "\"elapsed_s\":" << elapsed_s << ","
      << "\"repeat\":" << repeat << ","
      << "\"ms_per_image\":" << ms_per_img << ","
      << "\"throughput_img_s\":" << throughput
      << "}";
  std::cout << oss.str() << std::endl;

  CUDA_CHECK(cudaFree(d_imgs));
  CUDA_CHECK(cudaFree(d_weights));
  CUDA_CHECK(cudaFree(d_pot));
  CUDA_CHECK(cudaFree(d_pred));
  CUDA_CHECK(cudaEventDestroy(ev_start));
  CUDA_CHECK(cudaEventDestroy(ev_end));

  return 0;
}
