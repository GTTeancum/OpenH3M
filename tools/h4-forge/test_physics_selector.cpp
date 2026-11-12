#include "forge_original.h"
#include <windows.h>
#include <iostream>
#include <stdexcept>
static bool held,keyframed,special;
namespace h4_forge_original {
void sub_8244A180(PPCContext&,uint8_t*);
// Explicit data-query boundaries. These do not implement selector behavior.
void sub_82449B18(PPCContext& c,uint8_t*) { c.r3.u32=held?0:0xffffffff; }
void sub_82469630(PPCContext& c,uint8_t*) { c.r3.u32=keyframed; }
void sub_8244A5F0(PPCContext& c,uint8_t*) { c.r3.u32=special; }
void sub_823C2020(PPCContext& c,uint8_t*) { c.r3.u32=0x50000; }
}
int main() {
 try {
  auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
  if(!base)throw std::runtime_error("memory allocation failed");
  REX_STORE_U32(0x10000,0x11000);
  REX_STORE_U32(0x11000+4432,0x20000);
  REX_STORE_U32(0x20000+68,0x30000);
  REX_STORE_U32(0x30000+16+12,0x40000);
  REX_STORE_U16(0x40000+62,0);
  int count=0;
  for(int flags:{0,64,192})for(int h=0;h<2;++h)for(int k=0;k<2;++k)for(int s=0;s<2;++s) {
   held=h;keyframed=k;special=s;
   REX_STORE_U16(0x50000+5356+62,flags);
   PPCContext c{};c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=1;
   h4_forge_original::sub_8244A180(c,base);
   unsigned expected=flags==0?(held||special?1:0):(held?(flags==192?2:1):(keyframed?0:3));
   if(c.r3.u32!=expected || c.r1.u32!=0x180000) {
    std::cerr<<"flags="<<flags<<" held="<<h<<" keyframed="<<k<<" special="<<s<<" actual="<<c.r3.u32<<" expected="<<expected<<"\n";
    throw std::runtime_error("selector mismatch");
   }
   ++count;
  }
  REX_STORE_U16(0x40000+62,0xffff);
  PPCContext c{};c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=1;
  h4_forge_original::sub_8244A180(c,base);
  if(c.r3.u32!=0)throw std::runtime_error("non-variant object selector mismatch");
  std::cout<<"PASS "<<count<<" original selector combinations plus non-variant object. World predicates supplied; physics application and native collision untested.\n";
  VirtualFree(base,0,MEM_RELEASE);
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
