#include "forge_original.h"
#include <windows.h>
#include <cstring>
#include <iostream>
#include <stdexcept>
namespace h4_activation {void sub_82CD55F0(PPCContext&,uint8_t*);}
namespace h3_activation {void sub_82651968(PPCContext&,uint8_t*);}
static constexpr uint32_t body=0x30000,island=0x31000,world=0x32000;
static unsigned stage,motionOffset;
static void wake(PPCContext& c){
 if(stage++!=0||c.r3.u32!=world||c.r4.u32!=island)throw std::runtime_error("activation wake arguments/order");
}
static void setup(PPCContext& c){
 if(stage++!=1||c.r3.u32!=body+motionOffset||c.r4.u32!=11||c.r5.u32!=22||c.r6.u32!=33)
  throw std::runtime_error("activation motion arguments/order");
}
namespace h4_activation {
void sub_82CE1B98(PPCContext& c,uint8_t*){wake(c);}
void sub_824A5118(PPCContext& c,uint8_t*){setup(c);}
}
namespace h3_activation {
void sub_8265B720(PPCContext& c,uint8_t*){wake(c);}
void sub_8226B190(PPCContext& c,uint8_t*){setup(c);}
}
int main(){try{
 auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
 if(!base)throw std::runtime_error("allocation");
 unsigned cases=0;
 for(bool h4:{false,true})for(unsigned state=0;state<4;++state)for(unsigned type=0;type<9;++type)for(bool hasWorld:{false,true}){
  std::memset(base+body,0,0x3000);stage=0;
  const auto islandOffset=h4?200:144,islandFlags=h4?38:40,typeOffset=h4?232:168;
  const auto worldFields=h4?813:733;motionOffset=h4?224:160;
  REX_STORE_U32(body+islandOffset,island);REX_STORE_U32(body+8,hasWorld?world:0);
  REX_STORE_U8(island+islandFlags,state<<4);REX_STORE_U8(body+typeOffset,type);
  REX_STORE_U16(body+typeOffset+2,0x1234);REX_STORE_U16(body+typeOffset+4,0x5678);
  REX_STORE_U8(world+worldFields,11);REX_STORE_U8(world+worldFields+1,22);REX_STORE_U8(world+worldFields+2,33);
  PPCContext c{};c.r1.u32=0x180000;c.r3.u32=body;c.r31.u32=0x12345678;c.lr=0x87654321;
  if(h4)h4_activation::sub_82CD55F0(c,base);else h3_activation::sub_82651968(c,base);
  const bool active=state==0&&type!=(h4?5u:7u)&&hasWorld;
  if(stage!=(active?2u:0u)||REX_LOAD_U16(body+typeOffset+2)!=(active?0:0x1234)||
     REX_LOAD_U16(body+typeOffset+4)!=(active?0:0x5678)||c.r1.u32!=0x180000||
     c.r31.u32!=0x12345678||c.lr!=0x87654321)throw std::runtime_error("activation gate/state mismatch");
  ++cases;
 }
 std::cout<<"PASS "<<cases<<" original H3/H4 activation cases; native body layouts, motion-type differences and callback order checked. World wake callbacks simulated.\n";
 VirtualFree(base,0,MEM_RELEASE);
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
