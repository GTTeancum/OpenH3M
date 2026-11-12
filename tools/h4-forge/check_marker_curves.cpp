// Execute original H4 curve code against private marker functions, without a
// game window, GPU, or host input. Only trusted locally extracted fixtures.
#include "forge_original.h"
#include <windows.h>
#include <bit>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

int main(int argc,char** argv) {try {
  if(argc!=4)throw std::runtime_error("image, input fixture, output CSV required");
  auto* base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
  if(!base)throw std::runtime_error("guest reservation failed");
  struct Release {uint8_t* p;~Release(){VirtualFree(p,0,MEM_RELEASE);}} release{base};
  if(!VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE)||
     !VirtualAlloc(base+0x82000000,0x2f40000,MEM_COMMIT,PAGE_READWRITE))
    throw std::runtime_error("guest commit failed");
  std::ifstream image(argv[1],std::ios::binary),fixture(argv[2],std::ios::binary);
  if(!image.read(reinterpret_cast<char*>(base+0x82000000),0x2f38000))
    throw std::runtime_error("image missing or short");
  auto read=[&](auto& v) {
    if(!fixture.read(reinterpret_cast<char*>(&v),sizeof(v)))throw std::runtime_error("short fixture");
  };
  uint32_t magic,count;read(magic);read(count);
  if(magic!=0x46433448||count>256)throw std::runtime_error("invalid fixture header");
  std::ofstream out(argv[3]);out<<std::setprecision(9)<<"curve,input,range,r,g,b\n";
  for(uint32_t id=0;id<count;++id) {
    uint32_t size;read(size);
    if(size<32||size>4096)throw std::runtime_error("invalid curve extent");
    constexpr uint32_t ref=0x50000,data=0x51000,color=0x53000;
    std::memset(base+data,0,4096);
    if(!fixture.read(reinterpret_cast<char*>(base+data),size))throw std::runtime_error("short curve");
    REX_STORE_U32(ref,size);REX_STORE_U32(ref+12,data);
    for(unsigned range=0;range<=4;++range)for(unsigned step=0;step<=128;++step) {
      PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r3.u32=ref;
      ctx.f1.f64=step/128.;ctx.f2.f64=range/4.;
      float values[3];
      if(base[data+2]) {
        h4_forge_original::sub_82313E90(ctx,base);
        ctx.r3.u32=ref;ctx.r5.u32=color;
        h4_forge_original::sub_8228F2A0(ctx,base);
        for(unsigned i=0;i<3;++i)values[i]=std::bit_cast<float>(REX_LOAD_U32(color+i*4));
      } else {
        h4_forge_original::sub_8226CD10(ctx,base);
        for(float& v:values)v=float(ctx.f1.f64);
      }
      out<<id<<','<<step/128.<<','<<range/4.;
      for(float v:values) {
        if(!std::isfinite(v))throw std::runtime_error("nonfinite curve output");
        out<<','<<v;
      }
      out<<'\n';
    }
  }
  if(fixture.peek()!=EOF||!out)throw std::runtime_error("invalid fixture tail or output failure");
  std::cout<<count<<" original marker curves evaluated at 645 input/range pairs each\n";
  return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
