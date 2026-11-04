#pragma once
// Sparse numeric depth readback. The guest depth resource is read through an
// SRV and restored to its original state; only a private UAV receives writes.
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <vector>
#include <d3dcompiler.h>

namespace rex::graphics::d3d12 {
class SkyDepthValueProbe {
 public:
  static SkyDepthValueProbe& Get(){static SkyDepthValueProbe p;return p;}
  static constexpr uint32_t kCapacity=8192,kWords=16;
  inline static constexpr std::array<std::array<uint32_t,2>,4> points{{
    {501,175},{503,173},{497,178},{711,197}}};
  bool Enabled()const{return enabled_&&!failed_;}
  static bool Selected(uint64_t shader,uint32_t indices){
    if(indices!=562&&indices!=11)return false;
    switch(shader){
      case 8562590739555380577ull:case 6159915361788144154ull:
      case 12021865740332317413ull:case 17893540736724855907ull:
      case 14007674117786981017ull:case 10996139680788563763ull:return true;
      default:return false;
    }
  }
  // Allocate returns a one-use SRV descriptor pair on the caller's active heap.
  // SetPipeline must invalidate the caller's cached guest PSO. Invoke before
  // ordinary guest pipeline/root binding or after the ordinary draw is over.
  template<typename Commands,typename Allocate,typename SetPipeline,typename Barrier,typename Flush>
  void Record(ID3D12Device* device,Commands& commands,ID3D12Resource* source,
              DXGI_FORMAT format,D3D12_RESOURCE_STATES original_state,
              uint64_t frame,uint64_t sequence,uint64_t shader,uint32_t indices,uint32_t phase,
              bool guest_query,bool memexport,bool host_targets,uint64_t submission,uint64_t completed,
              Allocate allocate,SetPipeline set_pipeline,Barrier barrier,Flush flush){
    if(!Enabled())return;
    Poll(completed);
    if(!sequence||(!all_draws_&&!Selected(shader,indices))||phase>1||finished_)return;
    if(!file_&&!Initialize(device,frame))return;
    if(guest_query||memexport||!host_targets){Event("unsafe_scope",frame,sequence);return;}
    if(!source){Event("no_depth",frame,sequence);return;}
    const auto now=std::chrono::steady_clock::now();
    if(frame-first_frame_>=300||now-start_>=std::chrono::seconds(15)||records_.size()>=kCapacity){
      finished_=true;Event("limit",frame,sequence);return;
    }
    const auto d=source->GetDesc();
    if(d.Dimension!=D3D12_RESOURCE_DIMENSION_TEXTURE2D||d.DepthOrArraySize!=1||d.MipLevels!=1||
       !(d.Flags&D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL)||(d.Flags&D3D12_RESOURCE_FLAG_DENY_SHADER_RESOURCE)||
       (d.SampleDesc.Count!=1&&d.SampleDesc.Count!=2&&d.SampleDesc.Count!=4)||
       (format!=DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS&&format!=DXGI_FORMAT_R24_UNORM_X8_TYPELESS)){
      Event("unsupported_depth",frame,sequence);return;
    }
    for(const auto& p:points)if(p[0]>=d.Width||p[1]>=d.Height){Event("out_of_bounds",frame,sequence);return;}
    D3D12_CPU_DESCRIPTOR_HANDLE cpu{};D3D12_GPU_DESCRIPTOR_HANDLE gpu{};
    if(!allocate(cpu,gpu)){Event("descriptor_failed",frame,sequence);failed_=true;return;}
    D3D12_SHADER_RESOURCE_VIEW_DESC srv{};srv.Format=format;
    srv.Shader4ComponentMapping=D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.ViewDimension=d.SampleDesc.Count==1?D3D12_SRV_DIMENSION_TEXTURE2D:D3D12_SRV_DIMENSION_TEXTURE2DMS;
    if(d.SampleDesc.Count==1)srv.Texture2D.MipLevels=1;
    device->CreateShaderResourceView(source,&srv,cpu);
    const uint32_t record=uint32_t(records_.size());
    records_.push_back({frame,sequence,shader,submission,uint64_t(reinterpret_cast<uintptr_t>(source)),
      indices,phase,uint32_t(format),uint32_t(d.Width),d.Height,d.SampleDesc.Count});
    barrier(source,original_state,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);flush();
    set_pipeline(pipelines_[d.SampleDesc.Count==1?0:1].Get());
    commands.D3DSetComputeRootSignature(root_.Get());
    commands.D3DSetComputeRootDescriptorTable(0,gpu);
    commands.D3DSetComputeRootUnorderedAccessView(1,output_->GetGPUVirtualAddress()+record*kWords*4);
    uint32_t constants[12]{};for(uint32_t i=0;i<4;++i){constants[i*2]=points[i][0];constants[i*2+1]=points[i][1];}
    constants[8]=d.SampleDesc.Count;
    commands.D3DSetComputeRoot32BitConstants(2,12,constants,0);
    commands.D3DDispatch(1,1,1);
    barrier(output_.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_COPY_SOURCE);
    barrier(source,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,original_state);flush();
    commands.D3DCopyBufferRegion(readback_.Get(),record*kWords*4,output_.Get(),record*kWords*4,4*4*d.SampleDesc.Count);
    barrier(output_.Get(),D3D12_RESOURCE_STATE_COPY_SOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS);flush();
  }
  void Poll(uint64_t completed){
    if(!file_||!mapping_)return;const auto before=next_;
    while(next_<records_.size()&&records_[next_].submission<=completed){
      const auto& r=records_[next_];
      for(uint32_t point=0;point<4;++point)for(uint32_t sample=0;sample<r.samples;++sample)
        fprintf(file_,"sample,%llu,%llu,%u,%llu,%u,%llu,%u,%llu,%u,%u,%u,%u,%u,%u,%u,%u\n",
          r.frame,r.sequence,r.phase,r.shader,r.indices,r.submission,next_,r.resource,r.format,r.width,r.height,r.samples,
          points[point][0],points[point][1],sample,mapping_[next_*kWords+point*r.samples+sample]);
      ++next_;
    }
    if(before!=next_)fflush(file_);
  }
  void Shutdown(uint64_t completed){
    if(!file_)return;Poll(completed);
    if(next_!=records_.size())Event("pending",0,records_.size()-next_);
    Event("end",0,records_.size());fclose(file_);file_=nullptr;
    if(mapping_){readback_->Unmap(0,nullptr);mapping_=nullptr;}
  }
 private:
  struct RecordInfo{
    uint64_t frame,sequence,shader,submission,resource;
    uint32_t indices,phase,format,width,height,samples;
  };
  SkyDepthValueProbe(){
    const auto* on=std::getenv("OPENH3M_SKY_DEPTH_VALUE_TRACE");const auto* path=_wgetenv(L"OPENH3M_SKY_TRACE_DIR");
    if(!on||std::strcmp(on,"1")||!path||!*path)return;
    std::error_code ec;const auto base=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);if(ec)return;
    directory_=std::filesystem::canonical(path,ec);if(ec)return;
    auto rel=directory_.lexically_relative(base);if(rel.empty()||rel==L"."||rel.is_absolute())return;
    for(auto& component:rel)if(component==L"..")return;
    const auto* all=std::getenv("OPENH3M_SKY_DEPTH_WRITER_TRACE");all_draws_=all&&!std::strcmp(all,"1");
    enabled_=true;
  }
  void Event(const char* name,uint64_t frame,uint64_t sequence){
    fprintf(file_,"%s,%llu,%llu,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",name,frame,sequence);fflush(file_);
  }
  bool Initialize(ID3D12Device* device,uint64_t frame){
    file_=_wfopen((directory_/"depth-values.csv").c_str(),L"wx");if(!file_){failed_=true;return false;}
    fprintf(file_,"event,frame,sequence,phase,shader,index_count,submission,record,resource,format,width,height,samples,x,y,sample,depth_bits\n");
    start_=std::chrono::steady_clock::now();first_frame_=frame;
    D3D12_DESCRIPTOR_RANGE range{D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,0,0,0};
    D3D12_ROOT_PARAMETER parameters[3]{};parameters[0].ParameterType=D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
    parameters[0].DescriptorTable={1,&range};parameters[1].ParameterType=D3D12_ROOT_PARAMETER_TYPE_UAV;
    parameters[1].Descriptor={0,0};parameters[2].ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;
    parameters[2].Constants={0,0,12};D3D12_ROOT_SIGNATURE_DESC rd{3,parameters,0,nullptr,D3D12_ROOT_SIGNATURE_FLAG_NONE};
    Microsoft::WRL::ComPtr<ID3DBlob> signature,error;
    HRESULT hr=D3D12SerializeRootSignature(&rd,D3D_ROOT_SIGNATURE_VERSION_1,&signature,&error);
    if(SUCCEEDED(hr))hr=device->CreateRootSignature(0,signature->GetBufferPointer(),signature->GetBufferSize(),IID_PPV_ARGS(&root_));
    for(uint32_t multisampled=0;SUCCEEDED(hr)&&multisampled<2;++multisampled){
      const char* code=R"(
        #ifdef MULTISAMPLED
        Texture2DMS<float> depth_source:register(t0);
        #else
        Texture2D<float> depth_source:register(t0);
        #endif
        RWByteAddressBuffer result:register(u0);
        cbuffer Inputs:register(b0){uint4 xy01;uint4 xy23;uint sample_count;uint3 padding;};
        [numthreads(16,1,1)] void main(uint3 tid:SV_DispatchThreadID){
          uint i=tid.x;if(i>=4*sample_count)return;
          uint p=i/sample_count;uint s=i%sample_count;
          uint2 xy=p==0?xy01.xy:p==1?xy01.zw:p==2?xy23.xy:xy23.zw;
          #ifdef MULTISAMPLED
          float value=depth_source.Load(int2(xy),s);
          #else
          float value=depth_source.Load(int3(xy,0));
          #endif
          result.Store(i*4,asuint(value));
        })";
      D3D_SHADER_MACRO defines[]={{"MULTISAMPLED","1"},{nullptr,nullptr}};
      Microsoft::WRL::ComPtr<ID3DBlob> shader;
      hr=D3DCompile(code,std::strlen(code),nullptr,multisampled?defines:nullptr,nullptr,"main","cs_5_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&shader,&error);
      if(SUCCEEDED(hr)){
        D3D12_COMPUTE_PIPELINE_STATE_DESC pd{};pd.pRootSignature=root_.Get();pd.CS={shader->GetBufferPointer(),shader->GetBufferSize()};
        hr=device->CreateComputePipelineState(&pd,IID_PPV_ARGS(&pipelines_[multisampled]));
      }
    }
    D3D12_HEAP_PROPERTIES heap{};heap.Type=D3D12_HEAP_TYPE_DEFAULT;heap.CreationNodeMask=heap.VisibleNodeMask=1;
    D3D12_RESOURCE_DESC d{};d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;d.Width=kCapacity*kWords*4;
    d.Height=d.DepthOrArraySize=d.MipLevels=1;d.SampleDesc.Count=1;d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    d.Flags=D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS;
    if(SUCCEEDED(hr))hr=device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&d,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,nullptr,IID_PPV_ARGS(&output_));
    heap.Type=D3D12_HEAP_TYPE_READBACK;d.Flags=D3D12_RESOURCE_FLAG_NONE;
    if(SUCCEEDED(hr))hr=device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&d,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&readback_));
    void* data=nullptr;D3D12_RANGE read{0,size_t(d.Width)};
    if(SUCCEEDED(hr))hr=readback_->Map(0,&read,&data);
    if(FAILED(hr)){failed_=true;Event("initialize_failed",frame,uint32_t(hr));return false;}
    mapping_=static_cast<const uint32_t*>(data);records_.reserve(kCapacity);return true;
  }
  bool enabled_=false,failed_=false,finished_=false,all_draws_=false;
  std::filesystem::path directory_;FILE* file_=nullptr;
  std::chrono::steady_clock::time_point start_;uint64_t first_frame_=0;uint32_t next_=0;
  Microsoft::WRL::ComPtr<ID3D12RootSignature> root_;
  std::array<Microsoft::WRL::ComPtr<ID3D12PipelineState>,2> pipelines_;
  Microsoft::WRL::ComPtr<ID3D12Resource> output_,readback_;const uint32_t* mapping_=nullptr;
  std::vector<RecordInfo> records_;
};
}
