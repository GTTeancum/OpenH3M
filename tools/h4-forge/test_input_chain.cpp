#include "forge_original.h"
#include <windows.h>
#include <bit>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
static unsigned updates;
static void put(uint8_t* base,uint32_t a,float f){REX_STORE_U32(a,std::bit_cast<uint32_t>(f));}
static float get(uint8_t* base,uint32_t a){return std::bit_cast<float>(REX_LOAD_U32(a));}
namespace h3_input {
void sub_821EC0E0(PPCContext&,uint8_t*);
void sub_820A91C8(PPCContext& c,uint8_t* base){for(unsigned i=0;i<3;++i)put(base,c.r5.u32+i*4,i==0?1:0);}
void sub_825A4760(PPCContext& c,uint8_t* base){std::memset(base+c.r3.u32,c.r4.u8,c.r5.u32);}
void sub_820B8768(PPCContext& c,uint8_t*){if(c.r3.u32!=2||c.r4.u32!=0x30000)throw std::runtime_error("unit notification arguments");++updates;}
}
namespace h4_input {
static unsigned alignCalls,visibilityCalls;
static uint32_t previousCandidate;
static bool localPlayer;
void sub_8244EED8(PPCContext&,uint8_t*);
void sub_82582250(PPCContext& c,uint8_t* base){
 // Controlled candidate service: alignment-ready result, datum7.
 std::memset(base+c.r5.u32,0,240);REX_STORE_U32(c.r5.u32+116,7);c.r3.u32=2;
}
void sub_82582AD0(PPCContext& c,uint8_t* base){
 ++alignCalls;for(unsigned i=0;i<4;++i)put(base,c.r6.u32+i*4,i==3?1.f:0.f);
 for(unsigned i=0;i<3;++i)put(base,c.r7.u32+i*4,101.f+i);
}
void sub_822ED938(PPCContext& c,uint8_t*){c.r3.u32=localPlayer;}
void sub_825826B0(PPCContext& c,uint8_t*){
 // Original setter captures the previous candidate before storing the new one.
 if(c.r3.u32!=0||c.r4.u32!=2||c.r5.u32!=previousCandidate)throw std::runtime_error("visibility arguments");
 ++visibilityCalls;
}
void sub_82582178(PPCContext&,uint8_t*);
void sub_82361880(PPCContext&,uint8_t*);
void sub_823619F8(PPCContext&,uint8_t*);
void sub_82B33550(PPCContext& c,uint8_t* base){std::memset(base+c.r3.u32,c.r4.u8,c.r5.u32);}
void sub_8221D060(PPCContext& c,uint8_t* base){for(unsigned i=0;i<3;++i)put(base,c.r6.u32+4*i,i==0?1.f:0.f);}
void sub_8230DE48(PPCContext& c,uint8_t*){c.r3.u32=0;} // Ordinary session mode.
void sub_82219580(PPCContext&,uint8_t*){} // Unrelated action extension.
void sub_822C8308(PPCContext& c,uint8_t*){c.r3.u32=0;} // Unit capability query.
void sub_829896E0(PPCContext&,uint8_t*){throw std::runtime_error("unexpected action animation branch");}
void sub_822562A8(PPCContext&,uint8_t*);
void sub_82251B38(PPCContext& c,uint8_t* base){
 // Simulated identity object basis; the original unit writer performs the transform.
 std::memset(base+c.r4.u32,0,52);
 put(base,c.r4.u32,1.f);put(base,c.r4.u32+4,1.f);
 put(base,c.r4.u32+20,1.f);put(base,c.r4.u32+36,1.f);
}
void sub_822513B8(PPCContext& c,uint8_t*){if(c.r3.u32!=2)throw std::runtime_error("H4 notification datum");}
#define UNEXPECTED(name) void name(PPCContext&,uint8_t*){throw std::runtime_error("unexpected AI branch: " #name);}
UNEXPECTED(sub_82256DC8) UNEXPECTED(sub_82265C30) UNEXPECTED(sub_82265E28)
UNEXPECTED(sub_8226E178) UNEXPECTED(sub_8228ACE8) UNEXPECTED(sub_8229C9F0)
UNEXPECTED(sub_8229D0F0) UNEXPECTED(sub_82A73EA8)
#undef UNEXPECTED
void sub_82271460(PPCContext& c,uint8_t*){c.r3.u32=0;} // No equipment override.
void sub_8224DE10(PPCContext&,uint8_t*){throw std::runtime_error("unexpected equipment branch");}
void sub_822B3FF0(PPCContext&,uint8_t*){throw std::runtime_error("unexpected vehicle control branch");}
void sub_82340E60(PPCContext&,uint8_t*){throw std::runtime_error("unexpected config lookup");}
}
static uint8_t* memory(const char* path){
 auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ULL,MEM_RESERVE,PAGE_NOACCESS));
 if(!base||!VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE)||!VirtualAlloc(base+0x82000000,0x2f40000,MEM_COMMIT,PAGE_READWRITE))throw std::runtime_error("allocation");
 std::ifstream image(path,std::ios::binary|std::ios::ate);auto size=image.tellg();image.seekg(0);
 if(size<=0||size>0x2f40000||!image.read(reinterpret_cast<char*>(base+0x82000000),size))throw std::runtime_error("image");
 return base;
}
int main(){try{
 auto h3=memory("work/advanced-forge/guest-image.bin");auto h4=memory("work/h4-forge-research/h4-image.bin");
 for(auto base:{h3,h4}){
  REX_STORE_U32(0x10000,0x11000);REX_STORE_U32(0x21000+68,0x40000);REX_STORE_U32(0x40000+2*16+12,0x50000);
 }
 {auto base=h3;REX_STORE_U32(0x11000+168,0x21000);}
 {auto base=h4;REX_STORE_U32(0x11000+4432,0x21000);REX_STORE_U32(0x11000+24,0x20000);REX_STORE_U32(0x20000+68,0x30000);REX_STORE_U32(0x30000+36,2);REX_STORE_U32(0x8405d340,0);}
 unsigned cases=0,h4Cases=0,h4Chains=0;
 // Original processor and control selector; unattached monitor, absent equipment override.
 for(float x:{-1.f,-.5f,0.f,.5f,1.f})for(float y:{-1.f,-.5f,0.f,.5f,1.f})
 for(unsigned flags=0;flags<4;++flags)for(bool xyEnabled:{false,true})
 for(float initialZ:{-.25f,0.f,.25f}){
  auto base=h4;std::memset(base+0x60000,0,128);
  REX_STORE_U16(0x50000+44,65535);REX_STORE_U16(0x60000+52,flags);
  put(base,0x30000+2096,xyEnabled?1.f:0.f);
  put(base,0x61000,x);put(base,0x61004,y);put(base,0x61008,initialZ);
  PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;
  c.r3.u32=0;c.r4.u32=2;c.r5.u32=0x60000;c.r6.u32=0x61000;c.lr=789;
  h4_input::sub_82361880(c,base);
  float z=initialZ+float(bool(flags&1))-float(bool(flags&2));
  if(get(base,0x61000)!=(xyEnabled?x:0.f)||get(base,0x61004)!=(xyEnabled?y:0.f)||get(base,0x61008)!=z||c.lr!=789||c.r1.u32!=0x180000)
   throw std::runtime_error("H4 original monitor input processor mismatch");
  ++h4Cases;
  // Both no-AI and assigned-human-with-AI-datum cases must bypass smoothing.
  for(bool aiDatumPresent:{false,true}){
   REX_STORE_U32(0x11000+4440,0x22000);REX_STORE_U32(0x22000+68,0x70000);
   REX_STORE_U32(0x70000+2*4704+72,0xffffffff);
   REX_STORE_U32(0x50000+1156,aiDatumPresent?2:0xffffffff);
   REX_STORE_U32(0x50000+1180,0);
   std::memset(base+0x62000,0,160);
   std::memcpy(base+0x62000+32,base+0x61000,12);
   for(unsigned i=0;i<3;++i)put(base,0x50000+1348+i*4,7.f);
   c={};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;
   c.r3.u32=2;c.r4.u32=0x62000;c.lr=790;
   h4_input::sub_822562A8(c,base);
   if(c.lr!=790||c.r1.u32!=0x180000)throw std::runtime_error("H4 writer frame");
   for(unsigned i=0;i<3;++i){
    float expected=get(base,0x61000+i*4);
    if(get(base,0x50000+1348+i*4)!=expected||get(base,0x50000+1372+i*4)!=expected||get(base,0x50000+1384+i*4)!=expected)
     throw std::runtime_error("H4 writer control/history/world vector mismatch");
   }
   c={};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=0;
   h4_input::sub_82582178(c,base);
   float vx=xyEnabled?x:0.f,vy=xyEnabled?y:0.f;
   if(bool(c.r3.u8)!=(std::sqrt(vx*vx+vy*vy+z*z)>.5f))throw std::runtime_error("H4 full control-to-gate chain");
   ++h4Chains;
  }
 }
 std::cout<<"PASS "<<h4Cases<<" original H4 monitor processor/selector cases; equipment override simulated absent.\n";
 std::cout<<"PASS "<<h4Chains<<" H4 processor -> explicit packet triplet -> original unit writer -> original magnet gate cases; identity basis and world notifications simulated.\n";
 unsigned producerCases=0;
 for(float x:{-1.f,-.5f,0.f,.5f,1.f})for(float y:{-1.f,-.5f,0.f,.5f,1.f})
 for(unsigned flags=0;flags<4;++flags)for(bool xyEnabled:{false,true})for(unsigned actionMode=0;actionMode<3;++actionMode)
 for(unsigned phase=0;phase<3;++phase){
  auto base=h4;std::memset(base+0x60000,0,256);
  REX_STORE_U32(0x50000+36,0xffffffff);REX_STORE_U16(0x50000+44,65535);
  REX_STORE_U32(0x50000+1156,0xffffffff);REX_STORE_U32(0x50000+1180,0);
  REX_STORE_U32(0x60000+80,0xffffffff);REX_STORE_U8(0x60000+232,actionMode);
  REX_STORE_U16(0x30000+1160,9);put(base,0x30000+2096,xyEnabled?1.f:0.f);
  float vx=phase==1?0.f:x,vy=phase==1?0.f:y;unsigned f=phase==1?0:flags;
  put(base,0x60000+28,vx);put(base,0x60000+32,vy);REX_STORE_U16(0x60000+52,f);
  PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;
  c.r3.u32=0;c.r4.u32=2;c.r5.u32=0x60000;c.lr=791;
  h4_input::sub_823619F8(c,base);
  float vz=float(bool(f&1))-float(bool(f&2));if(!xyEnabled)vx=vy=0;
  if(get(base,0x50000+1348)!=vx||get(base,0x50000+1352)!=vy||get(base,0x50000+1356)!=vz||c.lr!=791||c.r1.u32!=0x180000)
   throw std::runtime_error("H4 enclosing producer control chain");
  if(REX_LOAD_U16(0x30000+1160)!=(actionMode==2?1:actionMode==1?0:9))throw std::runtime_error("H4 action mode state");
  c={};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=0;
  h4_input::sub_82582178(c,base);
  if(bool(c.r3.u8)!=(std::sqrt(vx*vx+vy*vy+vz*vz)>.5f))throw std::runtime_error("H4 enclosing producer gate");
  const bool moving=bool(c.r3.u8);
  // Execute the original caller/visibility setter too. Candidate lookup and
  // alignment geometry are controlled services, not original-world claims.
  REX_STORE_U32(0x11000+28,0x80000);
  constexpr uint32_t editor=0x80000+6892,transform=0x90000;
  REX_STORE_U32(editor,2);if(phase==0)REX_STORE_U32(editor+4,0xffffffff);REX_STORE_U8(editor+82,1);
  h4_input::previousCandidate=REX_LOAD_U32(editor+4);
  std::memset(base+transform,0x5a,52);
  h4_input::alignCalls=h4_input::visibilityCalls=0;h4_input::localPlayer=actionMode!=0;
  c={};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;
  c.r3.u32=0;c.r4.u32=2;c.r5.u32=editor;c.r6.u32=transform;c.lr=792;
  h4_input::sub_8244EED8(c,base);
  if(c.lr!=792||c.r1.u32!=0x180000||h4_input::alignCalls!=unsigned(!moving)||REX_LOAD_U32(editor+4)!=7||h4_input::visibilityCalls!=unsigned(h4_input::localPlayer))
   throw std::runtime_error("H4 original magnet caller state");
  if(moving){
   for(unsigned i=0;i<52;++i)if(base[transform+i]!=0x5a)throw std::runtime_error("movement-suppressed pose overwritten");
  }else{
   for(unsigned i=0;i<3;++i)if(get(base,transform+40+4*i)!=101.f+i)throw std::runtime_error("aligned position missing");
   for(unsigned i=0;i<9;++i)if(get(base,transform+4+4*i)!=(i%4==0?1.f:0.f))throw std::runtime_error("original quaternion matrix conversion");
  }
  ++producerCases;
 }
 std::cout<<"PASS "<<producerCases<<" original H4 input chain -> magnet caller/gate/visibility setter cases; movement preserves requested pose and selected candidate, stopping enables alignment. Selection/alignment geometry and peripheral services simulated.\n";
 for(float x:{-1.f,-.5f,0.f,.5f,1.f})for(float y:{-1.f,-.5f,0.f,.5f,1.f})for(unsigned flags=0;flags<4;++flags){
  // Repeated movement -> stop -> same movement checks that no previous gate result sticks.
  for(unsigned phase=0;phase<3;++phase){
   auto base=h3;std::memset(base+0x60000,0,128);
   const float vx=phase==1?0:x,vy=phase==1?0:y;const unsigned f=phase==1?0:flags;
   put(base,0x60000+20,vx);put(base,0x60000+24,vy);REX_STORE_U16(0x60000+40,f);
   PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=0;c.r4.u32=2;c.r5.u32=0x60000;c.lr=123;
   updates=0;h3_input::sub_821EC0E0(c,base);
   const float vz=float(bool(f&1))-float(bool(f&2));
   if(get(base,0x50000+496)!=vx||get(base,0x50000+500)!=vy||get(base,0x50000+504)!=vz||updates!=1||c.r1.u32!=0x180000||c.lr!=123)throw std::runtime_error("H3 producer/write mismatch");
   // Adapter boundary copies only the proven control triplet, not either game's unit structure.
   std::memcpy(h4+0x50000+1348,h3+0x50000+496,12);
   c={};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.r3.u32=0;c.lr=456;
   h4_input::sub_82582178(c,h4);
   const bool expected=std::sqrt(vx*vx+vy*vy+vz*vz)>.5f;
   if(bool(c.r3.u8)!=expected||c.r1.u32!=0x180000||c.lr!=456)throw std::runtime_error("H4 detachment gate mismatch");
   ++cases;
  }
 }
 std::cout<<"PASS "<<cases<<" original H3 producer/writer -> mapped triplet -> original H4 movement-gate cases; moving/stopped/resumed and vertical cancellation. Orientation conversion and world notification simulated; no native snap sequence.\n";
 VirtualFree(h3,0,MEM_RELEASE);VirtualFree(h4,0,MEM_RELEASE);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
