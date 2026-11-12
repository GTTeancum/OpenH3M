#include "forge_original.h"
#include <windows.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <bit>

// Alignment does not call scene-data queries. Fail explicitly if that changes.
namespace h4_forge_original {
#define UNEXPECTED(name) void name(PPCContext&,uint8_t*) { throw std::runtime_error(#name " unexpectedly called"); }
UNEXPECTED(sub_821F2050)
UNEXPECTED(sub_82582610)
UNEXPECTED(sub_82582A68)
UNEXPECTED(sub_82937F50)
UNEXPECTED(sub_8293A3B0)
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
  constexpr uint32_t tls=0x10000,state=0x20000,src=0x30000,dst=0x30100,q=0x30200,pos=0x30300;
  word(base,tls,tls+0x1000);word(base,tls+0x101c,state);
  real(base,state+0x1b40,1);identity(base,state+0x1b44);
  identity(base,src+8);identity(base,dst+0x3c);
  real(base,src+0x2c,1);real(base,src+0x30,2);real(base,src+0x34,3);
  for(int test=0;test<3;++test){
   identity(base,dst+0x3c);
   identity(base,state+0x1b44);
   if(test==1){real(base,state+0x1b44,0);real(base,state+0x1b48,1);real(base,state+0x1b50,-1);real(base,state+0x1b54,0);}
   if(test==1){real(base,dst+0x3c,0);real(base,dst+0x40,1);real(base,dst+0x48,-1);real(base,dst+0x4c,0);}
   if(test==2){real(base,dst+0x3c,-1);real(base,dst+0x4c,-1);}
   real(base,dst+0x60,10+test);real(base,dst+0x64,20);real(base,dst+0x68,30);
   PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=tls;
   ctx.r3.u32=0;ctx.r4.u32=src;ctx.r5.u32=dst;ctx.r6.u32=q;ctx.r7.u32=pos;
   h4_forge_original::sub_82582AD0(ctx,base);
   float x=get(base,q),y=get(base,q+4),z=get(base,q+8),w=get(base,q+12);
   float norm=x*x+y*y+z*z+w*w;
   if(ctx.r1.u32!=0x180000)throw std::runtime_error("guest stack was not restored");
   const float expectedZ=test==1?std::sqrt(0.5f):0.f;
   const float expectedW=test==1?std::sqrt(0.5f):1.f;
   if(std::abs(x)>0.0001||std::abs(y)>0.0001||std::abs(z-expectedZ)>0.0001||std::abs(w-expectedW)>0.0001)
    throw std::runtime_error("held rotation was not preserved");
   // Independent quaternion application: output transform must put the held
   // object's local marker exactly onto the destination marker.
   float v[3]={1,2,3};
   float cross[3]={y*3-z*2,z-x*3,x*2-y};
   float cross2[3]={y*cross[2]-z*cross[1],z*cross[0]-x*cross[2],x*cross[1]-y*cross[0]};
   if(!std::isfinite(norm)||std::abs(norm-1)>0.0001)throw std::runtime_error("non-unit alignment quaternion");
   for(int i=0;i<3;++i){
    float actual=get(base,pos+i*4)+v[i]+2*w*cross[i]+2*cross2[i];
    if(!std::isfinite(actual)||std::abs(actual-get(base,dst+0x60+i*4))>0.0001)throw std::runtime_error("marker alignment mismatch");
   }
   std::cout<<"PASS original alignment "<<test<<" q="<<x<<","<<y<<","<<z<<","<<w<<" position="<<get(base,pos)<<","<<get(base,pos+4)<<","<<get(base,pos+8)<<"\n";
  }
  VirtualFree(base,0,MEM_RELEASE);return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
