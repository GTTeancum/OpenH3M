#pragma once
// Native guest-output statistics. Pixel arrays stay in process memory; only
// aggregate counts and a worst-change coordinate per tile are written to disk.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <vector>

namespace rex::graphics::d3d12 {
class SkyRegionProbe {
 public:
  static SkyRegionProbe& Get(){static SkyRegionProbe probe;return probe;}
  static SkyRegionProbe& GetSwapchain(){static SkyRegionProbe probe(true);return probe;}
  struct Slot {
    Microsoft::WRL::ComPtr<ID3D12Resource> buffer;
    uint64_t submission=0,frame=0,capacity=0;
    uint32_t left=0,top=0,width=0,height=0,pitch=0;
    uint32_t format=0,viewport_width=0,viewport_height=0;
    uint64_t recorded_ns=0;
  };
  template<typename Copy>
  void Record(ID3D12Device* device,ID3D12Resource* source,uint32_t width,uint32_t height,
              uint64_t frame,uint64_t submission,uint64_t completed,Copy copy){
    if(directory_.empty())return;
    Poll(completed);if(finished_)return;
    auto now=std::chrono::steady_clock::now();
    if(!file_){
      if(now<poll_)return;
      poll_=now+std::chrono::seconds(1);
      std::error_code ec;if(!std::filesystem::exists(directory_/"arm",ec))return;
      file_=_wfopen((directory_/filename_).c_str(),L"wx");
      if(!file_){finished_=true;return;}
      fprintf(file_,"event,frame,pulse_frame,tile,x,y,width,height,count,mean_max,min_max,max_max,dark_count,fall_count,pulse_count,black_pulse_count,worst_pulse_drop,worst_x,worst_y,worst_before,worst_current,worst_after,recorded_ns,format,viewport_width,viewport_height\n");
      first_frame_=frame;start_=now;
    }
    if(frame-first_frame_>=frame_limit_||now-start_>=std::chrono::seconds(15)){
      Event("end",frame);finished_=true;return;
    }
    const auto desc=source->GetDesc();
    if((desc.Format!=DXGI_FORMAT_R10G10B10A2_UNORM&&desc.Format!=DXGI_FORMAT_R8G8B8A8_UNORM&&
        desc.Format!=DXGI_FORMAT_B8G8R8A8_UNORM)||desc.SampleDesc.Count!=1||
       width<16||height<8||width>4096||height>2160||desc.Width<width||desc.Height<height){
      Event("unsupported",frame);finished_=true;return;
    }
    uint32_t left=uint32_t(std::floor(region_[0]*width));
    uint32_t top=uint32_t(std::floor(region_[1]*height));
    uint32_t right=std::min(width,uint32_t(std::ceil(region_[2]*width)));
    uint32_t bottom=std::min(height,uint32_t(std::ceil(region_[3]*height)));
    if(right-left<8||bottom-top<4){Event("region_too_small",frame);finished_=true;return;}
    Slot* slot=nullptr;for(auto& candidate:slots_)if(!candidate.submission){slot=&candidate;break;}
    if(!slot){Event("busy",frame);return;}
    uint32_t pitch=((right-left)*4+255)&~255u;
    uint64_t bytes=uint64_t(pitch)*(bottom-top);
    if(slot->capacity<bytes){
      slot->buffer.Reset();slot->capacity=0;D3D12_RESOURCE_DESC buffer{};
      ui::d3d12::util::FillBufferResourceDesc(buffer,bytes,D3D12_RESOURCE_FLAG_NONE);
      if(FAILED(device->CreateCommittedResource(&ui::d3d12::util::kHeapPropertiesReadback,
        D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&slot->buffer)))){
        Event("allocation_failed",frame);finished_=true;return;
      }
      slot->capacity=bytes;
    }
    slot->submission=submission;slot->frame=frame;slot->left=left;slot->top=top;
    slot->width=right-left;slot->height=bottom-top;slot->pitch=pitch;
    slot->format=uint32_t(desc.Format);slot->viewport_width=width;slot->viewport_height=height;
    slot->recorded_ns=uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count());
    copy(*slot);
  }
  void Poll(uint64_t completed){
    if(!file_)return;
    std::vector<Slot*> ready;
    for(auto& slot:slots_)if(slot.submission&&slot.submission<=completed)ready.push_back(&slot);
    std::sort(ready.begin(),ready.end(),[](auto* a,auto* b){return a->frame<b->frame;});
    for(auto* slot:ready){
      D3D12_RANGE range{0,size_t(slot->pitch)*slot->height};void* mapped=nullptr;
      if(SUCCEEDED(slot->buffer->Map(0,&range,&mapped))){
        Analyze(*slot,static_cast<const uint8_t*>(mapped));
        D3D12_RANGE empty{0,0};slot->buffer->Unmap(0,&empty);
      }else Event("map_failed",slot->frame);
      slot->submission=0;
    }
    fflush(file_);
  }
  void Shutdown(uint64_t completed){
    Poll(completed);
    if(file_){for(auto& slot:slots_)if(slot.submission)Event("incomplete",slot.frame);
      fclose(file_);file_=nullptr;}
    finished_=true;for(auto& slot:slots_)slot.buffer.Reset();
    previous_.clear();previous2_.clear();
  }
 private:
  struct Tile {
    uint64_t sum=0;uint32_t count=0,minimum=1023,maximum=0,dark=0,fall=0,pulse=0,black=0;
    uint32_t drop=0,x=0,y=0,before=0,current=0,after=0;
  };
  void Analyze(const Slot& slot,const uint8_t* data){
    const std::array<uint32_t,7> shape{slot.left,slot.top,slot.width,slot.height,slot.format,slot.viewport_width,slot.viewport_height};
    bool adjacent=shape==shape_&&previous_frame_+1==slot.frame&&previous_.size()==size_t(slot.width)*slot.height;
    bool pulse_valid=adjacent&&previous2_frame_+1==previous_frame_&&previous2_.size()==previous_.size();
    std::array<Tile,32> tiles{};
    std::vector<uint16_t> current(size_t(slot.width)*slot.height);
    for(uint32_t y=0;y<slot.height;++y)for(uint32_t x=0;x<slot.width;++x){
      uint32_t pixel;std::memcpy(&pixel,data+size_t(y)*slot.pitch+x*4,4);
      uint32_t value=std::max({pixel&1023,(pixel>>10)&1023,(pixel>>20)&1023});
      if(slot.format==DXGI_FORMAT_R8G8B8A8_UNORM||slot.format==DXGI_FORMAT_B8G8R8A8_UNORM){
        uint32_t value8=std::max({pixel&255,(pixel>>8)&255,(pixel>>16)&255});
        value=(value8*1023+127)/255;
      }
      const size_t i=size_t(y)*slot.width+x;current[i]=uint16_t(value);
      auto& tile=tiles[(y*4/slot.height)*8+x*8/slot.width];
      ++tile.count;tile.sum+=value;tile.minimum=std::min(tile.minimum,value);tile.maximum=std::max(tile.maximum,value);
      tile.dark+=value<=10;
      if(adjacent)tile.fall+=previous_[i]>value+51&&value*10<=previous_[i]*7;
      if(pulse_valid){
        uint32_t baseline=std::min<uint32_t>(previous2_[i],value),middle=previous_[i];
        tile.pulse+=baseline>middle+51&&middle*10<=baseline*7;
        tile.black+=baseline>=31&&middle<=10&&middle*100<=baseline*15;
        if(baseline>middle&&baseline-middle>tile.drop){
          tile.drop=baseline-middle;tile.x=slot.left+x;tile.y=slot.top+y;
          tile.before=previous2_[i];tile.current=middle;tile.after=value;
        }
      }
    }
    for(uint32_t i=0;i<tiles.size();++i){
      const auto& tile=tiles[i];uint32_t tx=i%8,ty=i/8;
      uint32_t x0=(tx*slot.width+7)/8,x1=((tx+1)*slot.width+7)/8;
      uint32_t y0=(ty*slot.height+3)/4,y1=((ty+1)*slot.height+3)/4;
      fprintf(file_,"sample,%llu,%lld,%u,%u,%u,%u,%u,%u,%.9f,%.9f,%.9f,%u,%u,%u,%u,%.9f,%u,%u,%.9f,%.9f,%.9f,%llu,%u,%u,%u\n",
        slot.frame,pulse_valid?static_cast<long long>(previous_frame_):-1ll,i,slot.left+x0,slot.top+y0,x1-x0,y1-y0,
        tile.count,double(tile.sum)/tile.count/1023,tile.minimum/1023.,tile.maximum/1023.,
        tile.dark,tile.fall,tile.pulse,tile.black,tile.drop/1023.,tile.x,tile.y,
        tile.before/1023.,tile.current/1023.,tile.after/1023.,slot.recorded_ns,slot.format,slot.viewport_width,slot.viewport_height);
    }
    previous2_=adjacent?std::move(previous_):std::vector<uint16_t>{};
    previous2_frame_=previous_frame_;previous_=std::move(current);previous_frame_=slot.frame;shape_=shape;
  }
  void Event(const char* name,uint64_t frame){
    fprintf(file_,"%s,%llu,-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n",name,frame);fflush(file_);
  }
  explicit SkyRegionProbe(bool swapchain=false){
    if(swapchain){filename_=L"swapchain-region.csv";frame_limit_=900;}
    const auto* requested=_wgetenv(swapchain?L"OPENH3M_SKY_SWAPCHAIN_REGION_PROBE_DIR":L"OPENH3M_SKY_REGION_PROBE_DIR");if(!requested||!*requested)return;
    std::error_code ec;
    auto root=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);if(ec)return;
    auto dir=std::filesystem::canonical(requested,ec);if(ec||dir==root)return;
    auto relative=dir.lexically_relative(root);if(relative.empty()||relative.is_absolute())return;
    for(auto& part:relative)if(part==L"..")return;
    if(const auto* region=std::getenv("OPENH3M_SKY_REGION_PROBE_REGION")){
      double left,top,right,bottom;char extra;
      if(std::sscanf(region,"%lf,%lf,%lf,%lf%c",&left,&top,&right,&bottom,&extra)!=4||
         !(left>=0&&top>=0&&right<=1&&bottom<=1&&left<right&&top<bottom))return;
      region_={left,top,right,bottom};
    }
    directory_=dir;
  }
  std::filesystem::path directory_;
  const wchar_t* filename_=L"region.csv";
  uint32_t frame_limit_=300;
  std::array<double,4> region_{.45,.10,1.,.50};
  std::array<Slot,8> slots_;
  std::array<uint32_t,7> shape_{};
  std::vector<uint16_t> previous_,previous2_;
  FILE* file_=nullptr;bool finished_=false;
  uint64_t first_frame_=0,previous_frame_=0,previous2_frame_=0;
  std::chrono::steady_clock::time_point start_,poll_;
};
}
