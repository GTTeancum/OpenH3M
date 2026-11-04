#pragma once
// Opt-in numeric causal test. Replays only witnessed, non-memexport model draws
// with every color/depth/stencil write disabled, then restores the guest PSO.
// No query overlaps an active guest visibility query. No image output.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <map>
#include <mutex>
#include <vector>

namespace rex::graphics::d3d12 {
class SkyDepthTestProbe {
 public:
  static SkyDepthTestProbe& Get(){static SkyDepthTestProbe p;return p;}
  static constexpr uint32_t kCapacity=8192;
  static bool Selected(uint64_t shader){
    switch(shader){
      case 8562590739555380577ull:case 6159915361788144154ull:
      case 12021865740332317413ull:case 17893540736724855907ull:
      case 14007674117786981017ull:case 10996139680788563763ull:return true;
      default:return false;
    }
  }
  void Register(ID3D12Device* device,ID3D12PipelineState* original,
                const D3D12_GRAPHICS_PIPELINE_STATE_DESC& desc,uint64_t shader,bool host_targets){
    if(!enabled_||!host_targets||!Selected(shader))return;
    std::lock_guard<std::mutex> lock(mutex_);
    if(pipelines_.count(original))return;
    if(pipelines_.size()>=128){registration_failed_=true;return;}
    Entry entry;entry.original=original;entry.depth=desc.DepthStencilState;
    entry.raster=desc.RasterizerState;entry.sample_mask=desc.SampleMask;
    auto copy=desc;
    for(auto& target:copy.BlendState.RenderTarget)target.RenderTargetWriteMask=0;
    copy.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ZERO;
    copy.DepthStencilState.StencilWriteMask=0;
    for(auto* face:{&copy.DepthStencilState.FrontFace,&copy.DepthStencilState.BackFace}){
      face->StencilFailOp=face->StencilDepthFailOp=face->StencilPassOp=D3D12_STENCIL_OP_KEEP;
    }
    copy.CachedPSO={};
    // 0: original tests; 1: depth ALWAYS; 2: stencil disabled; 3: both bypassed.
    // Keep depth enabled when it was enabled originally: a depth-only fixture
    // with no PS and both tests disabled may legally skip rasterization.
    for(uint32_t variant=0;variant<4;++variant){
      copy.DepthStencilState.DepthEnable=desc.DepthStencilState.DepthEnable;
      copy.DepthStencilState.DepthFunc=(variant&1)?D3D12_COMPARISON_FUNC_ALWAYS:desc.DepthStencilState.DepthFunc;
      copy.DepthStencilState.StencilEnable=(variant&2)?FALSE:desc.DepthStencilState.StencilEnable;
      entry.result=device->CreateGraphicsPipelineState(&copy,IID_PPV_ARGS(&entry.variants[variant]));
      if(FAILED(entry.result))break;
    }
    pipelines_.emplace(original,std::move(entry));
  }
  template<typename Commands,typename Draw>
  void Record(ID3D12Device* device,Commands& commands,ID3D12PipelineState* original,
              bool guest_query_active,bool memexport,bool host_targets,uint64_t frame,
              uint64_t sequence,uint64_t shader,uint32_t indices,uint64_t submission,
              uint64_t completed,Draw draw){
    if(!enabled_||failed_)return;
    if(file_)Poll(completed);
    if(!sequence||!Selected(shader)||(indices!=562&&indices!=11))return;
    if(!file_&&!Initialize(device))return;
    if(guest_query_active||memexport||!host_targets){
      fprintf(file_,"unsafe_scope,%llu,%llu,0,%llu,%u,0,0,0,0,0,0,0,0,0,0\n",frame,sequence,shader,indices);return;
    }
    Entry entry;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      auto found=pipelines_.find(original);
      if(!original||found==pipelines_.end()||registration_failed_){
        fprintf(file_,"pipeline_missing,%llu,%llu,0,%llu,%u,0,0,0,0,0,0,0,0,0,0\n",frame,sequence,shader,indices);return;
      }
      entry=found->second;
    }
    if(FAILED(entry.result)){
      fprintf(file_,"pipeline_failed,%llu,%llu,0,%llu,%u,0,0,0,0,0,0,0,0,0,%u\n",frame,sequence,shader,indices,uint32_t(entry.result));failed_=true;return;
    }
    if(records_.size()+4>kCapacity){fprintf(file_,"capacity,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n");failed_=true;return;}
    for(uint32_t variant=0;variant<4;++variant){
      const auto query=uint32_t(records_.size());
      records_.push_back({frame,sequence,shader,submission,indices,variant,entry.depth,entry.raster.CullMode,entry.sample_mask});
      commands.D3DSetPipelineState(entry.variants[variant].Get());
      commands.D3DBeginQuery(heap_.Get(),D3D12_QUERY_TYPE_OCCLUSION,query);
      draw();
      commands.D3DEndQuery(heap_.Get(),D3D12_QUERY_TYPE_OCCLUSION,query);
      commands.D3DResolveQueryData(heap_.Get(),D3D12_QUERY_TYPE_OCCLUSION,query,1,readback_.Get(),query*sizeof(uint64_t));
    }
    // Only the PSO was changed. Root arguments, heaps, dynamic stencil ref,
    // vertex/index bindings, viewport and scissor remain untouched.
    commands.D3DSetPipelineState(original);
  }
  void Shutdown(uint64_t completed){
    if(!file_)return;Poll(completed);
    if(next_!=records_.size())fprintf(file_,"pending,0,0,0,0,0,0,0,0,0,0,0,0,0,0,%zu\n",records_.size()-next_);
    fprintf(file_,"end,0,0,0,0,0,0,0,0,0,0,0,0,0,0,%zu\n",records_.size());fclose(file_);file_=nullptr;
    if(mapping_){readback_->Unmap(0,nullptr);mapping_=nullptr;}
  }
 private:
  struct Entry{
    Microsoft::WRL::ComPtr<ID3D12PipelineState> original;
    std::array<Microsoft::WRL::ComPtr<ID3D12PipelineState>,4> variants;
    D3D12_DEPTH_STENCIL_DESC depth{};D3D12_RASTERIZER_DESC raster{};
    uint32_t sample_mask=0;HRESULT result=S_OK;
  };
  struct QueryRecord{
    uint64_t frame,sequence,shader,submission;uint32_t indices,variant;
    D3D12_DEPTH_STENCIL_DESC depth;D3D12_CULL_MODE cull;uint32_t sample_mask;
  };
  SkyDepthTestProbe(){
    const auto* on=std::getenv("OPENH3M_SKY_DEPTH_TEST_TRACE");const auto* path=_wgetenv(L"OPENH3M_SKY_TRACE_DIR");
    if(!on||std::strcmp(on,"1")||!path||!*path)return;
    std::error_code ec;const auto base=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);if(ec)return;
    directory_=std::filesystem::canonical(path,ec);if(ec){directory_.clear();return;}
    auto rel=directory_.lexically_relative(base);if(rel.empty()||rel==L"."||rel.is_absolute())return;
    for(auto& component:rel)if(component==L"..")return;
    enabled_=true;
  }
  bool Initialize(ID3D12Device* device){
    file_=_wfopen((directory_/"depth-tests.csv").c_str(),L"wx");if(!file_){failed_=true;return false;}
    fprintf(file_,"event,frame,sequence,variant,shader,index_count,query,submission,samples,depth_enabled,depth_func,stencil_enabled,stencil_front_func,stencil_read_mask,cull,sample_mask\n");
    D3D12_QUERY_HEAP_DESC q{};q.Type=D3D12_QUERY_HEAP_TYPE_OCCLUSION;q.Count=kCapacity;
    D3D12_HEAP_PROPERTIES h{};h.Type=D3D12_HEAP_TYPE_READBACK;h.CreationNodeMask=h.VisibleNodeMask=1;
    D3D12_RESOURCE_DESC d{};d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;d.Width=kCapacity*sizeof(uint64_t);
    d.Height=d.DepthOrArraySize=d.MipLevels=1;d.SampleDesc.Count=1;d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    void* mapping=nullptr;D3D12_RANGE range{0,size_t(d.Width)};
    if(FAILED(device->CreateQueryHeap(&q,IID_PPV_ARGS(&heap_)))||
       FAILED(device->CreateCommittedResource(&h,D3D12_HEAP_FLAG_NONE,&d,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&readback_)))||
       FAILED(readback_->Map(0,&range,&mapping))){
      fprintf(file_,"initialize_failed,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n");fflush(file_);failed_=true;return false;
    }
    mapping_=static_cast<const uint64_t*>(mapping);records_.reserve(kCapacity);return true;
  }
  void Poll(uint64_t completed){
    if(!file_||!mapping_)return;const auto previous=next_;
    while(next_<records_.size()){
      const auto& r=records_[next_];if(r.submission>completed)break;
      fprintf(file_,"sample,%llu,%llu,%u,%llu,%u,%u,%llu,%llu,%u,%u,%u,%u,%u,%u,%u\n",
        r.frame,r.sequence,r.variant,r.shader,r.indices,next_,r.submission,mapping_[next_],
        uint32_t(r.depth.DepthEnable),uint32_t(r.depth.DepthFunc),uint32_t(r.depth.StencilEnable),
        uint32_t(r.depth.FrontFace.StencilFunc),uint32_t(r.depth.StencilReadMask),uint32_t(r.cull),r.sample_mask);
      ++next_;
    }
    if(next_!=previous)fflush(file_);
  }
  bool enabled_=false,failed_=false,registration_failed_=false;
  std::filesystem::path directory_;std::mutex mutex_;std::map<ID3D12PipelineState*,Entry> pipelines_;
  FILE* file_=nullptr;uint32_t next_=0;
  Microsoft::WRL::ComPtr<ID3D12QueryHeap> heap_;
  Microsoft::WRL::ComPtr<ID3D12Resource> readback_;const uint64_t* mapping_=nullptr;
  std::vector<QueryRecord> records_;
};
}
