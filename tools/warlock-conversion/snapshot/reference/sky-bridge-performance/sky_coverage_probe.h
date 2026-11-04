#pragma once
// Opt-in numeric coverage of actual guest draws. Never nests a guest query.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <limits>
#include <vector>

namespace rex::graphics::d3d12 {
class SkyCoverageProbe {
 public:
  static SkyCoverageProbe& Get() { static SkyCoverageProbe p; return p; }
  static constexpr uint32_t kInvalid = UINT32_MAX;
  static constexpr uint32_t kCapacity = 16384;
  struct Record {
    uint64_t frame, sequence, shader, submission;
    uint32_t indices;
    bool ended=false, written=false;
  };
  template<typename Commands>
  uint32_t Begin(ID3D12Device* device, Commands& commands, bool guest_query_active,
                 uint64_t frame, uint64_t sequence, uint64_t shader,
                 uint32_t indices, uint64_t submission, uint64_t completed) {
    if (!enabled_ || failed_) return kInvalid;
    if(file_) Poll(completed);
    if(!sequence) return kInvalid;
    if (!file_ && !Initialize(device)) return kInvalid;
    if (guest_query_active) {
      fprintf(file_,"guest_query_active,%llu,%llu,%llu,%u,0,0,0\n",frame,sequence,shader,indices);
      return kInvalid;
    }
    if (records_.size()>=kCapacity) { failed_=true; fprintf(file_,"capacity,0,0,0,0,0,0,0\n"); return kInvalid; }
    const auto index=uint32_t(records_.size());
    records_.push_back({frame,sequence,shader,submission,indices});
    commands.D3DBeginQuery(heap_.Get(),D3D12_QUERY_TYPE_OCCLUSION,index);
    return index;
  }
  template<typename Commands>
  void End(Commands& commands, uint32_t index) {
    if (index==kInvalid) return;
    commands.D3DEndQuery(heap_.Get(),D3D12_QUERY_TYPE_OCCLUSION,index);
    commands.D3DResolveQueryData(heap_.Get(),D3D12_QUERY_TYPE_OCCLUSION,index,1,
                               readback_.Get(),uint64_t(index)*sizeof(uint64_t));
    records_[index].ended=true;
  }
  void Shutdown(uint64_t completed) {
    if (!file_) return;
    Poll(completed);
    for (uint32_t i=0;i<records_.size();++i) {
      const auto& r=records_[i];
      if (!r.written) fprintf(file_,"pending,%llu,%llu,%llu,%u,%u,%llu,0\n",r.frame,r.sequence,r.shader,r.indices,i,r.submission);
    }
    fprintf(file_,"end,0,0,0,0,%zu,0,0\n",records_.size());
    fclose(file_); file_=nullptr;
    if (mapping_) { readback_->Unmap(0,nullptr);mapping_=nullptr; }
  }
 private:
  SkyCoverageProbe() {
    const auto* on=std::getenv("OPENH3M_SKY_COVERAGE_TRACE");
    const auto* path=_wgetenv(L"OPENH3M_SKY_TRACE_DIR");
    if (!on || std::strcmp(on,"1") || !path || !*path) return;
    std::error_code ec;
    const auto base=std::filesystem::weakly_canonical(
      L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);
    if(ec)return;
    const auto dir=std::filesystem::weakly_canonical(path,ec);
    if(ec)return;
    const auto rel=dir.lexically_relative(base);
    if(rel.empty() || rel.is_absolute() || *rel.begin()==L"..")return;
    directory_=dir;enabled_=true;
  }
  bool Initialize(ID3D12Device* device) {
    file_=_wfopen((directory_/"coverage.csv").c_str(),L"wx");
    if(!file_){failed_=true;return false;}
    fprintf(file_,"event,frame,sequence,shader,index_count,query,submission,samples\n");
    D3D12_QUERY_HEAP_DESC query{};query.Type=D3D12_QUERY_HEAP_TYPE_OCCLUSION;query.Count=kCapacity;
    D3D12_HEAP_PROPERTIES heap{};heap.Type=D3D12_HEAP_TYPE_READBACK;heap.CreationNodeMask=heap.VisibleNodeMask=1;
    D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
    desc.Width=kCapacity*sizeof(uint64_t);desc.Height=1;desc.DepthOrArraySize=1;desc.MipLevels=1;
    desc.SampleDesc.Count=1;desc.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    void* mapping=nullptr;D3D12_RANGE range{0,size_t(desc.Width)};
    if(FAILED(device->CreateQueryHeap(&query,IID_PPV_ARGS(&heap_))) ||
       FAILED(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,
         D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&readback_))) ||
       FAILED(readback_->Map(0,&range,&mapping))) {
      failed_=true;fprintf(file_,"initialize_failed,0,0,0,0,0,0,0\n");fflush(file_);return false;
    }
    mapping_=static_cast<const uint64_t*>(mapping);records_.reserve(kCapacity);return true;
  }
  void Poll(uint64_t completed) {
    if(!file_ || !mapping_)return;
    const uint32_t previous=next_;
    while(next_<records_.size()) {
      auto& r=records_[next_];if(!r.ended || r.submission>completed)break;
      fprintf(file_,"sample,%llu,%llu,%llu,%u,%u,%llu,%llu\n",r.frame,r.sequence,r.shader,
              r.indices,next_,r.submission,mapping_[next_]);r.written=true;++next_;
    }
    if(next_!=previous)fflush(file_);
  }
  bool enabled_=false,failed_=false;
  FILE* file_=nullptr;std::filesystem::path directory_;
  Microsoft::WRL::ComPtr<ID3D12QueryHeap> heap_;
  Microsoft::WRL::ComPtr<ID3D12Resource> readback_;
  const uint64_t* mapping_=nullptr;std::vector<Record> records_;uint32_t next_=0;
};
} // namespace rex::graphics::d3d12
