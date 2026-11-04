#pragma once
// Opt-in read-only native bitmap descriptor/header witnesses. No guest writes.
#include <rex/hook.h>
#include <array>
#include <bit>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <mutex>
#include <windows.h>

extern "C" void __imp__sub_82298970(PPCContext&, uint8_t*);
extern "C" void __imp__sub_822987A8(PPCContext&, uint8_t*);
extern "C" void __imp__sub_826085A8(PPCContext&, uint8_t*);
extern "C" void __imp__sub_82097828(PPCContext&, uint8_t*);

namespace sky_bitmap_header_trace {
inline bool Read(uint8_t* base, uint32_t at, void* dst, size_t size) {
  if(at<0x10000||uint64_t(at)+size>0xc0000000ull)return false;
  SIZE_T read=0;
  return ReadProcessMemory(GetCurrentProcess(),base+at,dst,size,&read)&&read==size;
}
inline uint32_t Word(const uint8_t* p) {
  uint32_t v;std::memcpy(&v,p,4);return std::byteswap(v);
}
struct Active {uint32_t descriptor=0,header=0;uint64_t sequence=0;};
inline thread_local Active active;
class Trace {
 public:
  static Trace& Get(){static Trace trace;return trace;}
  ~Trace(){if(file_)std::fclose(file_);}
  Active Begin(uint8_t* base,uint32_t wrapper) {
    if(!file_)return {};
    std::array<uint8_t,8> pointers{};
    if(!Read(base,wrapper,pointers.data(),pointers.size()))return {};
    const auto descriptor=Word(pointers.data()),header=Word(pointers.data()+4);
    std::array<uint8_t,52> control{};
    if(!Read(base,descriptor,control.data(),control.size()))return {};
    const uint32_t w=uint32_t(control[40])*256+control[41];
    const uint32_t h=uint32_t(control[42])*256+control[43];
    if(control[46]!=0||control[45]<2)return {};
    if(!((w&&h&&(w<=16||h<=16)&&w<=512&&h<=512)||
         (w==256&&h==256&&Word(control.data()+48)==0x18280186)))return {};
    std::lock_guard lock(mutex_);
    if(sequence_>=400)return {};
    return {descriptor,header,++sequence_};
  }
  void Record(uint8_t* base,const char* event,uint32_t arg4=0,uint32_t arg5=0) {
    if(!active.sequence||!file_)return;
    std::array<uint8_t,52> control{},header{};
    if(!Read(base,active.descriptor,control.data(),control.size())||
       !Read(base,active.header,header.data(),header.size()))return;
    std::lock_guard lock(mutex_);
    if(rows_>=2000)return;
    std::fprintf(file_,"%s,%llu,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u",
      event,active.sequence,active.descriptor,active.header,
      uint32_t(control[40])*256+control[41],uint32_t(control[42])*256+control[43],
      unsigned(control[45]),unsigned(control[47]),Word(control.data()),Word(control.data()+20),
      Word(control.data()+12),Word(control.data()+32),arg4,arg5);
    for(unsigned i=0;i<13;++i)std::fprintf(file_,",%u",Word(header.data()+4*i));
    std::fputc('\n',file_);std::fflush(file_);++rows_;
  }
 private:
  Trace(){
    const auto* requested=_wgetenv(L"OPENH3M_SKY_HEADER_TRACE_DIR");
    if(!requested||!*requested)return;
    std::error_code ec;
    auto root=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);
    if(ec)return;
    auto path=std::filesystem::canonical(requested,ec);
    if(ec||path==root)return;
    auto relative=path.lexically_relative(root);
    if(relative.empty()||relative.is_absolute())return;
    for(auto& part:relative)if(part==L"..")return;
    file_=_wfopen((path/L"bitmap-headers.csv").c_str(),L"wbx");
    if(!file_)return;
    std::fputs("event,sequence,descriptor,header,width,height,levels,split,primary_bytes,secondary_bytes,primary_address,secondary_address,arg4,arg5",file_);
    for(unsigned i=0;i<13;++i)std::fprintf(file_,",word%u",i);
    std::fputc('\n',file_);std::fflush(file_);
  }
  std::mutex mutex_;FILE* file_=nullptr;uint64_t sequence_=0;uint32_t rows_=0;
};
}
REX_HOOK_RAW(sub_82298970){
  using namespace sky_bitmap_header_trace;
  const auto previous=active;
  active=Trace::Get().Begin(base,ctx.r3.u32);
  __imp__sub_82298970(ctx,base);
  Trace::Get().Record(base,"interop_complete");
  active=previous;
}
REX_HOOK_RAW(sub_822987A8){
  const auto r4=ctx.r4.u32,r5=ctx.r5.u32;
  __imp__sub_822987A8(ctx,base);
  sky_bitmap_header_trace::Trace::Get().Record(base,"header_constructed",r4,r5);
}
REX_HOOK_RAW(sub_826085A8){
  const auto r4=ctx.r4.u32,r5=ctx.r5.u32;
  __imp__sub_826085A8(ctx,base);
  sky_bitmap_header_trace::Trace::Get().Record(base,"offset_applied",r4,r5);
}
REX_HOOK_RAW(sub_82097828){
  const auto r4=ctx.r4.u32,r5=ctx.r5.u32;
  __imp__sub_82097828(ctx,base);
  sky_bitmap_header_trace::Trace::Get().Record(base,"addresses_applied",r4,r5);
}
