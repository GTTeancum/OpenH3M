#pragma once
// Private, opt-in, three-frame timestamp trace. No waits or render-state changes.
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <vector>

namespace rex::graphics::d3d12 {
class DrawGpuProbe {
 public:
  static DrawGpuProbe& Get() { static DrawGpuProbe p; return p; }
  static constexpr uint32_t kInvalid = UINT32_MAX, kCapacity = 16384;
  struct Sample { uint64_t frame, shader, submission, vertex_shader; bool memexport; uint32_t indices; bool ended = false; };
  template<typename Commands>
  uint32_t Begin(ID3D12Device* device, ID3D12CommandQueue* queue, Commands& commands,
                 uint64_t frame, uint64_t shader, uint32_t indices,
                 uint64_t submission, uint64_t completed, uint64_t vertex_shader, bool memexport) {
    if (directory_.empty() || failed_) return kInvalid;
    Poll(completed);
    if (file_ && !capture_complete_ && frame >= first_frame_ + 3 && next_ == samples_.size()) {
      capture_complete_ = true;
      fprintf(file_, "# capture_complete=1 total=%zu first_frame=%llu capacity_hit=%u\n",
              samples_.size(), first_frame_, unsigned(samples_.size() >= kCapacity));
      fflush(file_);
    }
    if (!file_) {
      std::error_code ec;
      if (!std::filesystem::exists(directory_ / "arm", ec)) return kInvalid;
      if (!Initialize(device, queue)) return kInvalid;
      first_frame_ = frame;
    }
    if (frame >= first_frame_ + 3 || samples_.size() >= kCapacity) return kInvalid;
    uint32_t index = uint32_t(samples_.size());
    samples_.push_back({frame, shader, submission, vertex_shader, memexport, indices});
    commands.D3DEndQuery(heap_.Get(), D3D12_QUERY_TYPE_TIMESTAMP, index * 2);
    return index;
  }
  template<typename Commands> void End(Commands& commands, uint32_t index) {
    if (index == kInvalid) return;
    commands.D3DEndQuery(heap_.Get(), D3D12_QUERY_TYPE_TIMESTAMP, index * 2 + 1);
    commands.D3DResolveQueryData(heap_.Get(), D3D12_QUERY_TYPE_TIMESTAMP, index * 2, 2,
                               readback_.Get(), uint64_t(index) * 16);
    samples_[index].ended = true;
  }
  void Shutdown(uint64_t completed) {
    if (!file_) return;
    Poll(completed);
    fprintf(file_, "# total=%zu completed=%u first_frame=%llu capacity=%u\n",
            samples_.size(), next_, first_frame_, kCapacity);
    fclose(file_); file_ = nullptr; failed_ = true;
    if (mapping_) { readback_->Unmap(0, nullptr); mapping_ = nullptr; }
  }
 private:
  DrawGpuProbe() {
    auto path = _wgetenv(L"OPENH3M_DRAW_GPU_DIR");
    if (!path || !*path) return;
    std::error_code ec;
    auto base = std::filesystem::weakly_canonical(
      L"C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks", ec);
    if (ec) return;
    auto dir = std::filesystem::weakly_canonical(path, ec);
    if (ec) return;
    auto rel = dir.lexically_relative(base);
    if (rel.empty() || rel.is_absolute() || *rel.begin() == L"..") return;
    directory_ = dir;
  }
  bool Initialize(ID3D12Device* device, ID3D12CommandQueue* queue) {
    file_ = _wfopen((directory_ / "draw-gpu.csv").c_str(), L"wx");
    if (!file_) { failed_ = true; return false; }
    fprintf(file_, "frame,shader,index_count,submission,milliseconds,vertex_shader,memexport\n");
    D3D12_QUERY_HEAP_DESC query{}; query.Type = D3D12_QUERY_HEAP_TYPE_TIMESTAMP; query.Count = kCapacity * 2;
    D3D12_HEAP_PROPERTIES heap{}; heap.Type = D3D12_HEAP_TYPE_READBACK; heap.CreationNodeMask = heap.VisibleNodeMask = 1;
    D3D12_RESOURCE_DESC desc{}; desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    desc.Width = kCapacity * 16; desc.Height = 1; desc.DepthOrArraySize = 1; desc.MipLevels = 1;
    desc.SampleDesc.Count = 1; desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    void* mapping = nullptr; D3D12_RANGE range{0, size_t(desc.Width)};
    if (FAILED(queue->GetTimestampFrequency(&frequency_)) || !frequency_ ||
        FAILED(device->CreateQueryHeap(&query, IID_PPV_ARGS(&heap_))) ||
        FAILED(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc,
          D3D12_RESOURCE_STATE_COPY_DEST, nullptr, IID_PPV_ARGS(&readback_))) ||
        FAILED(readback_->Map(0, &range, &mapping))) {
      failed_ = true; fprintf(file_, "# initialization failed\n"); fflush(file_); return false;
    }
    mapping_ = static_cast<const uint64_t*>(mapping); samples_.reserve(kCapacity); return true;
  }
  void Poll(uint64_t completed) {
    if (!file_ || !mapping_ || completed == UINT64_MAX) return;
    uint32_t previous = next_;
    while (next_ < samples_.size()) {
      const auto& s = samples_[next_];
      if (!s.ended || s.submission > completed) break;
      uint64_t begin = mapping_[next_ * 2], end = mapping_[next_ * 2 + 1];
      double ms = end >= begin ? double(end - begin) * 1000.0 / double(frequency_) : -1;
      fprintf(file_, "%llu,%llu,%u,%llu,%.6f,%llu,%u\n", s.frame, s.shader, s.indices, s.submission, ms, s.vertex_shader, unsigned(s.memexport));
      ++next_;
    }
    if (previous != next_) fflush(file_);
  }
  std::filesystem::path directory_;
  bool failed_ = false, capture_complete_ = false; FILE* file_ = nullptr;
  uint64_t frequency_ = 0, first_frame_ = 0; uint32_t next_ = 0;
  Microsoft::WRL::ComPtr<ID3D12QueryHeap> heap_;
  Microsoft::WRL::ComPtr<ID3D12Resource> readback_;
  const uint64_t* mapping_ = nullptr; std::vector<Sample> samples_;
};
}
