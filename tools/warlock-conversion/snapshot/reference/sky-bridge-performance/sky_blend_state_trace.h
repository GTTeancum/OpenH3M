#pragma once
// Bounded, opt-in native material/blend witnesses. Never changes guest state.
#include <rex/hook.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <mutex>
#include <windows.h>

extern "C" void __imp__sub_82465478(PPCContext&, uint8_t*);
extern "C" void __imp__sub_821A6088(PPCContext&, uint8_t*);
extern "C" void __imp__sub_82178C10(PPCContext&, uint8_t*);
extern "C" void __imp__sub_8215FC78(PPCContext&, uint8_t*);

namespace sky_blend_state_trace {
inline bool Read(uint8_t* base,uint32_t at,void* dst,size_t size) {
  if(at<0x10000||uint64_t(at)+size>0xc0000000ull)return false;
  SIZE_T count=0;
  return ReadProcessMemory(GetCurrentProcess(),base+at,dst,size,&count)&&count==size;
}
inline uint32_t Word(uint8_t* base,uint32_t at,bool& ok) {
  uint32_t v=0;const bool good=Read(base,at,&v,4);ok&=good;
  return good?std::byteswap(v):0xffffffff;
}
struct Material {
  uint32_t pointer=0,post=0,stage=0,caller=0,flags=0,valid=0;
  std::array<uint32_t,33> words{};
};
inline thread_local Material current;
class Trace {
 public:
  static Trace& Get(){static Trace trace;return trace;}
  ~Trace(){if(file_)std::fclose(file_);}
  void Frame(){if(!directory_.empty())++frame_;}
  bool Enabled() {
    if(directory_.empty()||finished_.load())return false;
    std::lock_guard lock(mutex_);
    const auto now=std::chrono::steady_clock::now();
    if(!file_){
      if(now<poll_)return false;
      poll_=now+std::chrono::seconds(1);
      std::error_code ec;
      if(!std::filesystem::exists(directory_/L"arm",ec))return false;
      file_=_wfopen((directory_/L"native-blend.bin").c_str(),L"wbx");
      if(!file_){finished_=true;return false;}
      setvbuf(file_,nullptr,_IOFBF,1024*1024);
      LARGE_INTEGER frequency;QueryPerformanceFrequency(&frequency);
      const uint32_t header[]{0x424c5953,1,72*4,100000,
        uint32_t(frequency.QuadPart),uint32_t(uint64_t(frequency.QuadPart)>>32),15,0};
      if(std::fwrite(header,sizeof(header),1,file_)!=1){finished_=true;return false;}
      start_=now;
    }
    if(now-start_>=std::chrono::seconds(15)||sequence_>=100000){
      std::fflush(file_);finished_=true;return false;
    }
    return true;
  }
  Material Capture(const PPCContext& ctx,uint8_t* base) {
    Material m;m.pointer=ctx.r3.u32;m.stage=ctx.r6.u32;m.caller=uint32_t(ctx.lr);
    bool ok=true;m.post=Word(base,m.pointer+44,ok);
    uint8_t flags[2]{};ok&=Read(base,m.pointer+52,flags,2);
    m.flags=uint32_t(flags[0])*256+flags[1];
    ok&=Read(base,m.post,m.words.data(),sizeof(m.words));
    for(auto& word:m.words)word=std::byteswap(word);
    m.valid=ok;return m;
  }
  void Record(uint32_t event,const PPCContext& ctx,uint8_t* base,
              uint32_t device=0) {
    if(!Enabled())return;
    std::array<uint32_t,72> row{};
    LARGE_INTEGER ticks;QueryPerformanceCounter(&ticks);
    row[0]=event;row[2]=uint32_t(ticks.QuadPart);
    row[3]=uint32_t(uint64_t(ticks.QuadPart)>>32);row[4]=GetCurrentThreadId();
    row[5]=frame_.load();row[6]=uint32_t(ctx.lr);row[7]=ctx.r1.u32;
    const uint32_t registers[]{ctx.r3.u32,ctx.r4.u32,ctx.r5.u32,ctx.r6.u32,
      ctx.r7.u32,ctx.r8.u32,ctx.r9.u32,ctx.r10.u32,ctx.r26.u32,ctx.r27.u32,
      ctx.r28.u32,ctx.r29.u32,ctx.r30.u32,ctx.r31.u32};
    std::copy(std::begin(registers),std::end(registers),row.begin()+8);
    row[22]=current.pointer;row[23]=current.post;row[24]=current.stage;
    row[25]=current.caller;row[26]=current.valid;
    bool ok=true;
    if(!device)device=Word(base,0x828e66f0,ok);
    row[27]=device;row[28]=Word(base,device+10552,ok);
    row[29]=Word(base,device+11840,ok);row[30]=Word(base,device+11844,ok);
    row[31]=Word(base,0x8283f624,ok);
    uint8_t bypass=0;ok&=Read(base,0x828e6889,&bypass,1);row[32]=bypass;
    row[33]=current.flags;row[34]=current.words[3];
    row[35]=current.words[26];row[36]=current.words[27];row[37]=ok;
    std::copy(current.words.begin(),current.words.end(),row.begin()+38);
    row[71]=uint32_t(ctx.r4.u64>>32);
    std::lock_guard lock(mutex_);
    if(finished_.load()||sequence_>=100000)return;
    row[1]=++sequence_;
    if(std::fwrite(row.data(),sizeof(row),1,file_)!=1)finished_=true;
    if(sequence_%1024==0)std::fflush(file_);
  }
 private:
  Trace(){
    const auto* requested=_wgetenv(L"OPENH3M_SKY_BLEND_TRACE_DIR");
    if(!requested||!*requested)return;
    std::error_code ec;
    const auto root=std::filesystem::canonical(L"C:/X360/ISOs/H3M/.local/OpenH3M-source/work/sky-bridge",ec);
    if(ec)return;
    const auto path=std::filesystem::canonical(requested,ec);
    if(ec||path==root)return;
    const auto relative=path.lexically_relative(root);
    if(relative.empty()||relative.is_absolute())return;
    for(const auto& part:relative)if(part==L"..")return;
    directory_=path;
  }
  std::filesystem::path directory_;FILE* file_=nullptr;std::mutex mutex_;
  std::atomic<bool> finished_{false};std::atomic<uint32_t> frame_{0};
  uint32_t sequence_=0;
  std::chrono::steady_clock::time_point start_{},poll_{};
};
}
REX_HOOK_RAW(sub_82465478){
  using namespace sky_blend_state_trace;
  auto& trace=Trace::Get();const auto previous=current;
  if(trace.Enabled()){
    current=trace.Capture(ctx,base);
    const bool selected=current.valid&&(current.words[3]&65535)==225;
    if(selected)trace.Record(1,ctx,base);
    __imp__sub_82465478(ctx,base);
    if(selected)trace.Record(2,ctx,base);
  }else __imp__sub_82465478(ctx,base);
  current=previous;
}
REX_HOOK_RAW(sub_821A6088){
  auto& trace=sky_blend_state_trace::Trace::Get();const auto device=ctx.r3.u32;
  trace.Record(3,ctx,base,device);__imp__sub_821A6088(ctx,base);
  trace.Record(4,ctx,base,device);
}
REX_HOOK_RAW(sub_82178C10){
  auto& trace=sky_blend_state_trace::Trace::Get();const auto device=ctx.r3.u32;
  trace.Record(5,ctx,base,device);__imp__sub_82178C10(ctx,base);
  trace.Record(6,ctx,base,device);
}
REX_HOOK_RAW(sub_8215FC78){
  using namespace sky_blend_state_trace;
  auto& trace=Trace::Get();
  if(ctx.r5.u32!=0x2200||!(ctx.r4.u64&(1ull<<62))||!trace.Enabled()){
    __imp__sub_8215FC78(ctx,base);return;
  }
  // This native flush writes contiguous type-0 state packets from r6,
  // selecting registers with the full 64-bit r4 mask. Device+48 is its
  // last-written command address. Preserve arguments for the after witness.
  const PPCContext entry=ctx;const auto previous=current;current={};
  current.post=ctx.r6.u32;current.stage=ctx.r5.u32;current.caller=uint32_t(ctx.lr);
  bool ok=true;current.flags=Word(base,ctx.r3.u32+48,ok);
  ok&=Read(base,current.post,current.words.data(),sizeof(current.words));
  for(auto& word:current.words)word=std::byteswap(word);
  current.valid=ok;trace.Record(7,entry,base,entry.r3.u32);
  __imp__sub_8215FC78(ctx,base);
  current.flags=Word(base,entry.r3.u32+48,ok);current.valid=ok;
  trace.Record(8,entry,base,entry.r3.u32);current=previous;
}
