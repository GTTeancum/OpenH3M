#pragma once
// Numeric color-0 observations around identified draws. No image output.
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>

namespace rex::graphics::d3d12 {
class SkyStageProbe {
 public:
  static SkyStageProbe& Get(){static SkyStageProbe probe;return probe;}
  inline static constexpr std::array<std::array<uint32_t,2>,16> points{{
    {664,193},{720,193},{748,205},{720,217},{888,181},{888,205},
    {916,205},{945,193},{1001,193},{1029,205},{888,229},{945,229},
    {973,229},{1001,229},{973,241},{945,253}}};
  struct Slot {
    Microsoft::WRL::ComPtr<ID3D12Resource> buffer;
    uint64_t submission=0,frame=0,sequence=0,shader=0,resource=0;
    uint32_t phase=0,count=0,format=0,resource_format=0,bytes=0,width=0,height=0;
  };
  bool Enabled()const{return !directory_.empty();}
  template<typename Copy>
  void Record(ID3D12Device* device,ID3D12Resource* source,DXGI_FORMAT format,
              uint64_t frame,uint64_t sequence,uint64_t shader,uint32_t count,
              uint32_t phase,uint64_t submission,uint64_t completed,Copy copy){
    if(directory_.empty())return;
    Poll(completed);if(finished_)return;
    const auto now=std::chrono::steady_clock::now();
    if(!file_){
      if(!sequence)return;
      file_=_wfopen((directory_/"stages.csv").c_str(),L"wx");
      if(!file_){finished_=true;return;}
      fprintf(file_,"event,frame,sequence,phase,shader,index_count,submission,resource,format,resource_format,width,height,x,y,bytes,w0,w1,w2,w3\n");
      first_frame_=frame;start_=now;
    }
    if(frame-first_frame_>=300||now-start_>=std::chrono::seconds(15)||rows_>=100000){
      fprintf(file_,"end,%llu,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",frame);
      fflush(file_);finished_=true;return;
    }
    if(!sequence)return;
    uint32_t bytes=0;
    switch(format){
      case DXGI_FORMAT_R32G32B32A32_FLOAT:bytes=16;break;
      case DXGI_FORMAT_R16G16B16A16_FLOAT:
      case DXGI_FORMAT_R16G16B16A16_UNORM:
      case DXGI_FORMAT_R16G16B16A16_SNORM:bytes=8;break;
      case DXGI_FORMAT_R10G10B10A2_UNORM:
      case DXGI_FORMAT_R11G11B10_FLOAT:
      case DXGI_FORMAT_R8G8B8A8_UNORM:
      case DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:
      case DXGI_FORMAT_B8G8R8A8_UNORM:bytes=4;break;
      default:break;
    }
    const auto desc=source->GetDesc();
    if(!bytes||desc.SampleDesc.Count!=1||desc.Width<=1029||desc.Height<=253){
      fprintf(file_,"unsupported,%llu,%llu,%u,%llu,%u,0,0,%u,%u,%llu,%u,0,0,0,0,0,0,0\n",
        frame,sequence,phase,shader,count,uint32_t(format),uint32_t(desc.Format),desc.Width,desc.Height);
      fflush(file_);finished_=true;return;
    }
    Slot* slot=nullptr;for(auto& candidate:slots_)if(!candidate.submission){slot=&candidate;break;}
    if(!slot){fprintf(file_,"busy,%llu,%llu,%u,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",frame,sequence,phase);return;}
    if(!slot->buffer){
      D3D12_RESOURCE_DESC buffer{};
      ui::d3d12::util::FillBufferResourceDesc(buffer,points.size()*512,D3D12_RESOURCE_FLAG_NONE);
      if(FAILED(device->CreateCommittedResource(&ui::d3d12::util::kHeapPropertiesReadback,
        D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&slot->buffer)))){
        fprintf(file_,"allocation_failed,%llu,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",frame);
        fflush(file_);finished_=true;return;
      }
    }
    slot->submission=submission;slot->frame=frame;slot->sequence=sequence;slot->shader=shader;
    slot->resource=reinterpret_cast<uintptr_t>(source);slot->phase=phase;slot->count=count;
    slot->format=uint32_t(format);slot->resource_format=uint32_t(desc.Format);slot->bytes=bytes;
    slot->width=uint32_t(desc.Width);slot->height=desc.Height;
    copy(slot->buffer.Get());
  }
  void Poll(uint64_t completed){
    if(!file_)return;
    for(auto& slot:slots_){
      if(!slot.submission||slot.submission>completed)continue;
      D3D12_RANGE range{0,points.size()*512};void* mapped=nullptr;
      if(SUCCEEDED(slot.buffer->Map(0,&range,&mapped))){
        for(uint32_t i=0;i<points.size();++i){
          std::array<uint32_t,4> value{};std::memcpy(value.data(),static_cast<uint8_t*>(mapped)+i*512,slot.bytes);
          fprintf(file_,"sample,%llu,%llu,%u,%llu,%u,%llu,%llu,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",
            slot.frame,slot.sequence,slot.phase,slot.shader,slot.count,slot.submission,slot.resource,
            slot.format,slot.resource_format,slot.width,slot.height,points[i][0],points[i][1],slot.bytes,
            value[0],value[1],value[2],value[3]);++rows_;
        }
        D3D12_RANGE empty{0,0};slot.buffer->Unmap(0,&empty);
      }else fprintf(file_,"map_failed,%llu,%llu,%u,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",slot.frame,slot.sequence,slot.phase);
      slot.submission=0;
    }
    fflush(file_);
  }
  void Shutdown(uint64_t completed){
    Poll(completed);
    if(file_){for(auto& slot:slots_)if(slot.submission)
      fprintf(file_,"incomplete,%llu,%llu,%u,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",slot.frame,slot.sequence,slot.phase);
      fclose(file_);file_=nullptr;}
    finished_=true;for(auto& slot:slots_)slot.buffer.Reset();
  }
 private:
  SkyStageProbe(){
    const auto* requested=_wgetenv(L"OPENH3M_SKY_STAGE_PROBE_DIR");if(!requested||!*requested)return;
    std::error_code ec;
    auto root=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);if(ec)return;
    auto dir=std::filesystem::canonical(requested,ec);if(ec||dir==root)return;
    auto relative=dir.lexically_relative(root);if(relative.empty()||relative.is_absolute())return;
    for(auto& part:relative)if(part==L"..")return;
    directory_=dir;
  }
  std::filesystem::path directory_;
  std::array<Slot,128> slots_;
  FILE* file_=nullptr;bool finished_=false;
  uint64_t first_frame_=0,rows_=0;
  std::chrono::steady_clock::time_point start_;
};
}
