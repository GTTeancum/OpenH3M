#include "forge_original.h"
#include <windows.h>
#include <iostream>
#include <stdexcept>
#include <cstring>
#include <vector>
#include <utility>
namespace property_test {
void sub_823B5938(PPCContext&,uint8_t*);
void sub_823CACB0(PPCContext&,uint8_t*);
void sub_823CAD80(PPCContext&,uint8_t*);
void sub_822F0788(PPCContext&,uint8_t*);
}
static std::vector<std::pair<unsigned,uint64_t>> slow;
namespace property_test {
void sub_822E6870(PPCContext& c,uint8_t*) {
 // Record the external flush request; do not pretend to execute the bitstream writer.
 slow.emplace_back(c.r5.u32,c.r4.u64);
}
}
int main(){try{
 auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
 if(!base)throw std::runtime_error("allocation");
 unsigned cases=0,slowCases=0;
 using Fn=void(*)(PPCContext&,uint8_t*);
 Fn funcs[]={property_test::sub_823B5938,property_test::sub_823CACB0,property_test::sub_823CAD80,property_test::sub_822F0788};
 for(unsigned kind=0;kind<4;++kind)for(int value=(kind==0||kind==3?-1:0);value<=(kind==0?8:kind==3?7:255);++value){
  unsigned width;uint64_t bits;
  if(kind==0){width=4;bits=value+1;}
  else if(kind==1){width=value==255?1:9;bits=value==255?1:value;}
  else if(kind==2){width=8;bits=(value+1)&255;}
  else {width=value==-1?1:4;bits=value==-1?1:value;}
  for(unsigned used=0;used+width<=64;++used){
   constexpr unsigned stream=0x30000;std::memset(base+stream,0,64);slow.clear();
   const uint64_t prefix=used==0?0:(uint64_t(0x5555555555555555)&(~uint64_t(0)>>(64-used)));
   REX_STORE_U32(stream+48,used);REX_STORE_U32(stream+36,used+128);REX_STORE_U64(stream+40,prefix);
   PPCContext c{};c.r1.u32=0x180000;c.r3.u32=stream;c.r4.u32=value;c.r30.u32=123;c.r31.u32=456;c.lr=789;
   funcs[kind](c,base);
   if(!slow.empty()||REX_LOAD_U32(stream+48)!=used+width||REX_LOAD_U32(stream+36)!=used+128+width||REX_LOAD_U64(stream+40)!=((prefix<<width)|bits)||c.r1.u32!=0x180000||c.r30.u32!=123||c.r31.u32!=456||c.lr!=789)throw std::runtime_error("property encoding/preservation mismatch");
   ++cases;
  }
  // Direct encoders take a single flush path when already full. Compound encoders
  // have sequential writes and require a real flushing implementation, so exclude them.
  if(kind==0||kind==2){
   constexpr unsigned stream=0x30000;std::memset(base+stream,0,64);slow.clear();REX_STORE_U32(stream+48,64);
   PPCContext c{};c.r1.u32=0x180000;c.r3.u32=stream;c.r4.u32=value;funcs[kind](c,base);
   if(slow.size()!=1||slow[0]!=std::pair<unsigned,uint64_t>{width,bits})throw std::runtime_error("flush request mismatch");
   ++slowCases;
  }
 }
 std::cout<<"PASS "<<cases<<" original encoder cases at every fitting buffer alignment; "<<slowCases<<" flush-request cases. Actual flush, decoding and native save/load not tested.\n";
 VirtualFree(base,0,MEM_RELEASE);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
