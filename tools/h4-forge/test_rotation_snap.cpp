#include "forge_original.h"
#include <windows.h>
#include <bit>
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
namespace h4_forge_original {
void sub_82451A38(PPCContext&, uint8_t*);
#define UNEXPECTED(n) void n(PPCContext&,uint8_t*) { throw std::runtime_error(#n " unexpected boundary"); }
UNEXPECTED(sub_821F2050) UNEXPECTED(sub_82582610) UNEXPECTED(sub_82582A68)
UNEXPECTED(sub_82937F50) UNEXPECTED(sub_8293A3B0) UNEXPECTED(sub_825827B0)
UNEXPECTED(sub_82582950) UNEXPECTED(sub_82271460) UNEXPECTED(sub_822714E0)
UNEXPECTED(sub_825812D0)
}
static void put(uint8_t* base,uint32_t a,float f) { REX_STORE_U32(a,std::bit_cast<uint32_t>(f)); }
static float get(uint8_t* base,uint32_t a) { return std::bit_cast<float>(REX_LOAD_U32(a)); }
int main(int argc,char**argv) {
 try {
  if(argc!=2)throw std::runtime_error("image required");
  auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
  if(!base || !VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE) ||
     !VirtualAlloc(base+0x82000000,0x2f40000,MEM_COMMIT,PAGE_READWRITE))
   throw std::runtime_error("guest allocation failed");
  std::ifstream input(argv[1],std::ios::binary);
  if(!input.read(reinterpret_cast<char*>(base+0x82000000),0x2f38000))throw std::runtime_error("image read failed");
  constexpr uint32_t actual=0x30000,expected=0x30100,angles=0x30200;
  const float rad=get(base,0x82128a20);
  auto basis=[&](uint32_t dest,const float* value) {
   for(int i=0;i<3;++i)put(base,angles+4*i,value[i]);
   PPCContext c{};c.r1.u32=0x180000;c.r3.u32=dest+4;c.r4.u32=dest+28;c.r5.u32=angles;
   h4_forge_original::sub_8232F9B8(c,base);
   if(c.r1.u32!=0x180000)throw std::runtime_error("basis stack imbalance");
  };
  int count=0;
  for(int degrees:{90,45,30,15,5}) {
   float step=degrees*rad;
   for(int axis=0;axis<3;++axis)for(float fraction:{-1.49f,-1.01f,-0.51f,-0.49f,0.f,0.49f,0.51f,1.01f,1.49f}) {
    // Keep pitch within its Euler principal interval; 90-degree mode still
    // exercises both sides of the half-step without a representation wrap.
    if(axis==1 && std::abs(fraction*degrees)>=80)continue;
    float a[3]={},e[3]={};a[axis]=fraction*step;
    e[axis]=std::trunc(fraction+(fraction>=0?0.5f:-0.5f))*step;
    basis(actual,a);basis(expected,e);
    put(base,actual,1.7f);
    for(int i=0;i<3;++i)put(base,actual+40+4*i,11.f+i);
    PPCContext c{};c.r1.u32=0x180000;c.r3.u32=actual;c.f1.f64=step;
    h4_forge_original::sub_82451A38(c,base);
    if(c.r1.u32!=0x180000)throw std::runtime_error("quantizer stack imbalance");
    for(int offset:{4,8,12,28,32,36}) {
     float got=get(base,actual+offset),want=get(base,expected+offset);
     if(!std::isfinite(got)||std::abs(got-want)>0.0002f) {
      std::cerr<<"mode="<<degrees<<" axis="<<axis<<" fraction="<<fraction<<" offset="<<offset<<" got="<<got<<" expected="<<want<<"\n";
      throw std::runtime_error("rotation rounding mismatch");
     }
    }
    if(get(base,actual)!=1.7f)throw std::runtime_error("scale changed");
    for(int i=0;i<3;++i)if(get(base,actual+40+4*i)!=11.f+i)throw std::runtime_error("position changed");
    ++count;
   }
  }
  std::cout<<"PASS "<<count<<" original quantizer cases: five modes, three axes, signed near-half-step inputs; scale/position preserved. Conversion helpers reused, not independently verified.\n";
  VirtualFree(base,0,MEM_RELEASE);
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
