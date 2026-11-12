#include "forge_original.h"
#include <windows.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <bit>
#include <cmath>

// Data-only fixture adapters. Selection/scoring/alignment stay in original code.
static float targetDistance=0.1f;
namespace h4_forge_original {
#define UNEXPECTED(name) void name(PPCContext&,uint8_t*) { throw std::runtime_error(#name " unexpectedly called"); }
UNEXPECTED(sub_82582950)
UNEXPECTED(sub_825827B0)
UNEXPECTED(sub_82271460)
UNEXPECTED(sub_822714E0)
UNEXPECTED(sub_825812D0)
#undef UNEXPECTED
void sub_821F2050(PPCContext& ctx,uint8_t* base) {
 // This fixture has exactly one nearby eligible object.
 REX_STORE_U32(ctx.r8.u32,1);ctx.r3.u32=1;
}
void sub_82582A68(PPCContext& ctx,uint8_t*) {ctx.r3.u32=0x193;}
void sub_82937F50(PPCContext& ctx,uint8_t*) {ctx.r3.u32=1;}
void sub_8293A3B0(PPCContext& ctx,uint8_t* base) {
 float x=ctx.r3.u32==1?targetDistance:0;
 REX_STORE_U32(ctx.r4.u32,std::bit_cast<uint32_t>(x));
 REX_STORE_U32(ctx.r4.u32+4,0);REX_STORE_U32(ctx.r4.u32+8,0);
}
void sub_82582610(PPCContext& ctx,uint8_t* base) {
 uint32_t out=ctx.r4.u32;bool target=ctx.r3.u32==1;
 std::memset(base+out,0,112);
 // Two rigid-transform records in the original marker ABI, local and world.
 for(uint32_t matrix:{out+8,out+0x3c})
  for(int i=0;i<9;++i)REX_STORE_U32(matrix+i*4,std::bit_cast<uint32_t>(i%4==0?1.f:0.f));
 REX_STORE_U32(out+4,std::bit_cast<uint32_t>(1.f));
 REX_STORE_U32(out+0x38,std::bit_cast<uint32_t>(1.f));
 REX_STORE_U32(out+0x60,std::bit_cast<uint32_t>(target?targetDistance:0.f));
 ctx.r3.u32=1;
}
}
static void word(uint8_t* base,uint32_t a,uint32_t v) { REX_STORE_U32(a,v); }
static void real(uint8_t* base,uint32_t a,float v) { word(base,a,std::bit_cast<uint32_t>(v)); }
static float get(uint8_t* base,uint32_t a) { return std::bit_cast<float>(REX_LOAD_U32(a)); }
static void identity(uint8_t* base,uint32_t a) { for(int i=0;i<9;++i)real(base,a+i*4,i%4==0?1.f:0.f); }
int main(int argc,char** argv) {
 try {
  if(argc!=2)throw std::runtime_error("decoded image path required");
  auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
  if(!base)throw std::runtime_error("guest reservation failed");
  if(!VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE) ||
     !VirtualAlloc(base+0x82000000,0x2f40000,MEM_COMMIT,PAGE_READWRITE))throw std::runtime_error("guest commit failed");
  std::ifstream image(argv[1],std::ios::binary);
  if(!image.read(reinterpret_cast<char*>(base+0x82000000),0x2f38000))throw std::runtime_error("image read failed");
  for(uint32_t addr:{0x835b0000u,0x84050000u,0x84200000u})
   if(!VirtualAlloc(base+addr,0x10000,MEM_COMMIT,PAGE_READWRITE))throw std::runtime_error("global commit failed");
  constexpr uint32_t tls=0x10000,state=0x20000,out=0x30000;
  word(base,tls,tls+0x1000);word(base,tls+0x101c,state);
  word(base,tls+0x1000+0x1150,0x40000);word(base,0x40044,0x41000);
  word(base,0x4100c,0x42000);word(base,0x4101c,0x42100);
  real(base,0x4204c,1);real(base,0x4214c,1);
  word(base,state+0x1aec,0);word(base,state+0x1bf8,2);
  real(base,state+0x1b40,1);identity(base,state+0x1b44);
  // Original tag lookup reads this minimal tag table and original Forge globals.
  word(base,0x8405d340,0x50000);word(base,0x501ec,0x666f7267);word(base,0x501f8,0);
  word(base,0x8420ff20,0x60000);word(base,0x835b6a50,0x51000);
  word(base,0x9fff8,1);word(base,0x9fffc,0x666f7267);word(base,0x51004,0x52000);
  std::ifstream config("work/h4-forge-research/isolated/forge-globals.bin",std::ios::binary);
  if(!config.read(reinterpret_cast<char*>(base+0x52000),0x50))throw std::runtime_error("original forge globals required");
  for(int test=0;test<2;++test){
   targetDistance=test==0?0.1f:3.f;
   real(base,0x42140,targetDistance);
   PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=tls;
   ctx.r3.u32=0;ctx.r4.u32=0;ctx.r5.u32=out;
   h4_forge_original::sub_82582250(ctx,base);
   std::cout<<"original selection distance="<<targetDistance<<" result="<<ctx.r3.u32<<" candidate="<<REX_LOAD_U32(out+0x74)<<"\n";
   if(ctx.r1.u32!=0x180000)throw std::runtime_error("guest stack was not restored");
   if(test==0&&(ctx.r3.u32!=2||REX_LOAD_U32(out+0x74)!=1))throw std::runtime_error("near marker not selected");
   if(test==1&&ctx.r3.u32==2)throw std::runtime_error("out-of-range marker snapped");
  }
  // Diagnostic: distinguish original pair acceptance from geometry collision.
  // These markers are synthetic; this does not validate the installed pack.
  for(int degrees:{0,90,180}) {
   constexpr uint32_t held=0x60000,target=0x60100,distance=0x60200,q=0x60300,pos=0x60400;
   std::memset(base+held,0,0x500);
   for(uint32_t marker:{held,target}) {
    real(base,marker+4,1);real(base,marker+0x38,1);
    identity(base,marker+8);identity(base,marker+0x3c);
   }
   const float radians=degrees*3.14159265358979323846f/180.f;
   const float c=std::cos(radians),s=std::sin(radians);
   real(base,target+0x3c,c);real(base,target+0x40,s);
   real(base,target+0x48,-s);real(base,target+0x4c,c);
   real(base,target+0x60,.1f);
   PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=tls;
   ctx.r3.u32=0;ctx.r4.u32=held;ctx.r5.u32=target;ctx.r6.u32=distance;
   h4_forge_original::sub_82582E38(ctx,base);
   const auto accepted=ctx.r3.u32;
   ctx.r3.u32=0;ctx.r4.u32=held;ctx.r5.u32=target;ctx.r6.u32=q;ctx.r7.u32=pos;
   h4_forge_original::sub_82582AD0(ctx,base);
   std::cout<<"pair target_yaw="<<degrees<<" accepted="<<accepted
            <<" distance_squared="<<get(base,distance)<<" rotation="
            <<get(base,q)<<","<<get(base,q+4)<<","<<get(base,q+8)<<","<<get(base,q+12)
            <<" position="<<get(base,pos)<<","<<get(base,pos+4)<<","<<get(base,pos+8)<<"\n";
   if(ctx.r1.u32!=0x180000)throw std::runtime_error("pair diagnostic stack not restored");
  }
  VirtualFree(base,0,MEM_RELEASE);return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
