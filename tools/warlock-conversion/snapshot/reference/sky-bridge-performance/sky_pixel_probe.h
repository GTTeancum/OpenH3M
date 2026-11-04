#pragma once
// Native numeric GPU readback only: 144 isolated texels, no image or UI capture.
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <filesystem>

namespace rex::graphics::d3d12 {
class SkyPixelProbe {
 public:
  static SkyPixelProbe& Get() { static SkyPixelProbe instance; return instance; }
  static SkyPixelProbe& GetPresented() { static SkyPixelProbe instance(true); return instance; }
  uint32_t SampleX(uint32_t column,uint32_t width) const {
    return std::min(width-1,uint32_t((region_[0]+(column+.5)*(region_[2]-region_[0])/16)*width));
  }
  uint32_t SampleY(uint32_t row,uint32_t height) const {
    return std::min(height-1,uint32_t((region_[1]+(row+.5)*(region_[3]-region_[1])/9)*height));
  }
  struct Slot {
    Microsoft::WRL::ComPtr<ID3D12Resource> buffer;
    uint64_t submission=0, frame=0;
    uint32_t width=0, height=0, format=0, swizzle=0;
  };
  template<typename Copy>
  void Record(ID3D12Device* device, ID3D12Resource* source, DXGI_FORMAT format,
              uint32_t swizzle, uint32_t width, uint32_t height, uint64_t frame,
              uint64_t submission, uint64_t completed, Copy copy) {
    if (directory_.empty()) return;
    Poll(completed);
    if (finished_) return;
    const auto now=std::chrono::steady_clock::now();
    if (!file_) {
      if (now<poll_) return;
      poll_=now+std::chrono::seconds(1);
      std::error_code ec;
      if (!std::filesystem::exists(directory_/"arm",ec)) return;
      file_=_wfopen((directory_/filename_).c_str(),L"wx");
      if (!file_) { finished_=true; return; }
      fprintf(file_,"event,frame,submission,format,swizzle,width,height,x,y,packed_pixel\n");
      first_frame_=frame;start_=now;
    }
    if (frame-first_frame_>=300 || now-start_>=std::chrono::seconds(15)) {
      fprintf(file_,"end,%llu,%llu,0,0,0,0,0,0,0\n",frame,submission);
      fflush(file_);finished_=true;return;
    }
    const auto desc=source->GetDesc();
    if (!width || !height || desc.SampleDesc.Count!=1 ||
        (format!=DXGI_FORMAT_R8G8B8A8_UNORM && format!=DXGI_FORMAT_B8G8R8A8_UNORM &&
         format!=DXGI_FORMAT_R10G10B10A2_UNORM)) {
      fprintf(file_,"unsupported,%llu,%llu,%u,%u,%u,%u,0,0,0\n",frame,submission,uint32_t(format),swizzle,width,height);
      fflush(file_);finished_=true;return;
    }
    Slot* slot=nullptr;
    for (auto& candidate:slots_) if (!candidate.submission) {slot=&candidate;break;}
    if (!slot) {fprintf(file_,"busy,%llu,%llu,0,0,0,0,0,0,0\n",frame,submission);return;}
    if (!slot->buffer) {
      D3D12_RESOURCE_DESC buffer_desc{};
      ui::d3d12::util::FillBufferResourceDesc(buffer_desc,144*512,D3D12_RESOURCE_FLAG_NONE);
      if (FAILED(device->CreateCommittedResource(&ui::d3d12::util::kHeapPropertiesReadback,
          D3D12_HEAP_FLAG_NONE,&buffer_desc,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,
          IID_PPV_ARGS(&slot->buffer)))) {
        fprintf(file_,"allocation_failed,%llu,%llu,0,0,0,0,0,0,0\n",frame,submission);
        fflush(file_);finished_=true;return;
      }
    }
    slot->submission=submission;slot->frame=frame;slot->width=width;slot->height=height;
    slot->format=uint32_t(format);slot->swizzle=swizzle;
    copy(slot->buffer.Get());
  }
  void Poll(uint64_t completed) {
    if (!file_) return;
    for (auto& slot:slots_) {
      if (!slot.submission || slot.submission>completed) continue;
      D3D12_RANGE range{0,144*512};void* mapped=nullptr;
      if (SUCCEEDED(slot.buffer->Map(0,&range,&mapped))) {
        for (uint32_t row=0;row<9;++row) for (uint32_t col=0;col<16;++col) {
          uint32_t value;std::memcpy(&value,static_cast<uint8_t*>(mapped)+(row*16+col)*512,4);
          fprintf(file_,"sample,%llu,%llu,%u,%u,%u,%u,%u,%u,%u\n",slot.frame,slot.submission,
            slot.format,slot.swizzle,slot.width,slot.height,SampleX(col,slot.width),
            SampleY(row,slot.height),value);
        }
        D3D12_RANGE written{0,0};slot.buffer->Unmap(0,&written);
      } else fprintf(file_,"map_failed,%llu,%llu,0,0,0,0,0,0,0\n",slot.frame,slot.submission);
      slot.submission=0;
    }
    fflush(file_);
  }
  void Shutdown(uint64_t completed) {
    Poll(completed);
    if (file_) {
      for (auto& slot:slots_) if (slot.submission)
        fprintf(file_,"incomplete,%llu,%llu,0,0,0,0,0,0,0\n",slot.frame,slot.submission);
      fclose(file_);file_=nullptr;
    }
    finished_=true;
    // Called only after the command processor's existing shutdown GPU wait.
    for (auto& slot:slots_) slot.buffer.Reset();
  }
 private:
  explicit SkyPixelProbe(bool presented=false) {
    if(presented){
      const auto* enabled=std::getenv("OPENH3M_SKY_PIXEL_PROBE_PRESENTED");
      if(!enabled||std::strcmp(enabled,"1"))return;
      filename_=L"presented.csv";
    }
    const auto* requested=_wgetenv(L"OPENH3M_SKY_PIXEL_PROBE_DIR");
    if (!requested || !*requested) return;
    std::error_code ec;
    auto root=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);
    if (ec) return;
    auto dir=std::filesystem::canonical(requested,ec);
    if (ec || dir==root) return;
    auto relative=dir.lexically_relative(root);
    if (relative.empty() || relative.is_absolute()) return;
    for (auto& part:relative) if (part==L"..") return;
    directory_=dir;
    if (const auto* region=std::getenv("OPENH3M_SKY_PIXEL_PROBE_REGION")) {
      double left,top,right,bottom;char extra;
      if (std::sscanf(region,"%lf,%lf,%lf,%lf%c",&left,&top,&right,&bottom,&extra)!=4 ||
          !(left>=0&&top>=0&&right<=1&&bottom<=1&&left<right&&top<bottom)) {
        directory_.clear();return;
      }
      region_={left,top,right,bottom};
    }
  }
  std::filesystem::path directory_;
  const wchar_t* filename_=L"pixels.csv";
  std::array<double,4> region_{0,0,1,1};
  std::array<Slot,8> slots_;
  FILE* file_=nullptr;
  uint64_t first_frame_=0;
  bool finished_=false;
  std::chrono::steady_clock::time_point start_,poll_;
};
} // namespace rex::graphics::d3d12
