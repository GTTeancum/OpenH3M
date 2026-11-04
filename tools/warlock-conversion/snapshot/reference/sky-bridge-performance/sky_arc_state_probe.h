#pragma once
// Bounded numeric GPU particle-state readback; no images or guest-state writes.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <vector>

namespace rex::graphics::d3d12 {
class SkyArcStateProbe {
 public:
  static SkyArcStateProbe& Get(){static SkyArcStateProbe p;return p;}
  struct Slot {
    Microsoft::WRL::ComPtr<ID3D12Resource> buffer;
    uint64_t submission=0,frame=0,sequence=0;
    uint32_t address=0,size=0,first=0,count=0;
  };
  template<typename Copy>
  void Record(ID3D12Device* device,uint64_t frame,uint64_t sequence,uint64_t shader,
              uint32_t base,uint32_t available,uint32_t vertex_offset,uint32_t vertices,
              uint64_t submission,uint64_t completed,Copy copy){
    if(directory_.empty()||failed_||!sequence||shader!=16104069050768599808ull)return;
    if(!file_){
      file_=_wfopen((directory_/"arc-states.csv").c_str(),L"wx");
      if(!file_){failed_=true;return;}
      fprintf(file_,"event,frame,sequence,submission,address,first,count,bytes,data\n");
    }
    Poll(completed);
    if(++records_>16384){failed_=true;fprintf(file_,"capacity,0,0,0,0,0,0,0,\n");return;}
    const uint64_t offset=uint64_t(vertex_offset/4)*80,size=uint64_t(vertices/4)*80;
    if(vertex_offset%4||vertices%4||!size||size>4096||offset+size>available||uint64_t(base)+offset+size>0x20000000){
      fprintf(file_,"range,%llu,%llu,0,%u,%u,%u,%llu,\n",frame,sequence,base,vertex_offset/4,vertices/4,size);return;
    }
    Slot* slot=nullptr;
    for(auto& candidate:slots_)if(!candidate.submission){slot=&candidate;break;}
    if(!slot){fprintf(file_,"busy,%llu,%llu,0,0,0,0,0,\n",frame,sequence);return;}
    if(!slot->buffer){
      D3D12_HEAP_PROPERTIES heap{};heap.Type=D3D12_HEAP_TYPE_READBACK;heap.CreationNodeMask=heap.VisibleNodeMask=1;
      D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;desc.Width=4096;
      desc.Height=1;desc.DepthOrArraySize=1;desc.MipLevels=1;desc.SampleDesc.Count=1;desc.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
      if(FAILED(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,
                  nullptr,IID_PPV_ARGS(&slot->buffer)))){failed_=true;fprintf(file_,"allocate_failed,0,0,0,0,0,0,0,\n");return;}
    }
    slot->frame=frame;slot->sequence=sequence;slot->address=uint32_t(base+offset);
    slot->size=uint32_t(size);slot->first=vertex_offset/4;slot->count=vertices/4;slot->submission=submission;
    copy(slot->buffer.Get(),slot->address,slot->size);
  }
  void Poll(uint64_t completed){
    if(!file_)return;
    for(auto& slot:slots_){
      if(!slot.submission||slot.submission>completed)continue;
      D3D12_RANGE range{0,slot.size};void* mapped=nullptr;
      if(FAILED(slot.buffer->Map(0,&range,&mapped))){failed_=true;fprintf(file_,"map_failed,0,0,0,0,0,0,0,\n");return;}
      fprintf(file_,"sample,%llu,%llu,%llu,%u,%u,%u,%u,",slot.frame,slot.sequence,slot.submission,
              slot.address,slot.first,slot.count,slot.size);
      const auto* bytes=static_cast<const uint8_t*>(mapped);
      for(uint32_t i=0;i<slot.size;++i)fprintf(file_,"%02x",bytes[i]);
      fprintf(file_,"\n");D3D12_RANGE written{0,0};slot.buffer->Unmap(0,&written);slot.submission=0;
    }
    fflush(file_);
  }
  void Shutdown(uint64_t completed){
    if(!file_)return;Poll(completed);
    for(const auto& slot:slots_)if(slot.submission)fprintf(file_,"pending,%llu,%llu,%llu,0,0,0,0,\n",slot.frame,slot.sequence,slot.submission);
    fprintf(file_,"end,0,0,0,0,0,0,0,\n");fclose(file_);file_=nullptr;
  }
 private:
  SkyArcStateProbe(){
    const auto* on=std::getenv("OPENH3M_SKY_TRACE_ARC");const auto* path=_wgetenv(L"OPENH3M_SKY_TRACE_DIR");
    if(!on||std::strcmp(on,"1")||!path||!*path)return;
    std::error_code ec;auto dir=std::filesystem::canonical(path,ec);if(ec)return;
    const auto base=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);if(ec)return;
    const auto rel=dir.lexically_relative(base);if(rel.empty()||rel.is_absolute()||*rel.begin()==L"..")return;
    directory_=dir;
  }
  std::filesystem::path directory_;FILE* file_=nullptr;bool failed_=false;uint32_t records_=0;
  std::array<Slot,512> slots_;
};
}
