#include "forge_original.h"
#include <windows.h>
#include <bit>
#include <cmath>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
static constexpr uint32_t tls=0x11000,game=0x20000,editor=game+6892,object=0x50000,variant=0x60000;
static bool eligible=true,resolveObject=true;static unsigned sessionType=0,deletes=0,mismatches=0;static bool restorePose,forceFixed,localPlayer; static unsigned restores,variantWrites,releaseDynamic; static int fixedCall=-1; static unsigned axis,poseCalls;static float multiplier=5,maximum=22;
static void put(uint8_t* base,uint32_t a,float f){REX_STORE_U32(a,std::bit_cast<uint32_t>(f));}
static float get(uint8_t* base,uint32_t a){return std::bit_cast<float>(REX_LOAD_U32(a));}
static unsigned editInputGate=0;
static bool rotationApplied=false;
namespace grab_test {
void sub_8244A7D0(PPCContext&,uint8_t*);
void sub_8244B518(PPCContext&,uint8_t*);
void sub_8244A6A8(PPCContext&,uint8_t*);
void sub_822C5470(PPCContext&,uint8_t*);
void sub_8224A558(PPCContext& c,uint8_t* base){if(c.r4.u32!=0||c.r5.u32!=256)throw std::runtime_error("packet clear extent");std::memset(base+c.r3.u32,0,256);}
void sub_82368CE0(PPCContext&,uint8_t*);void sub_82452738(PPCContext&,uint8_t*);
void sub_82232AC8(PPCContext&,uint8_t*);
void sub_8246B098(PPCContext& c,uint8_t*){c.r3.u32=42;} // Monitor tag lookup remains controlled.
void sub_82451500(PPCContext&,uint8_t*);void sub_82450E10(PPCContext&,uint8_t*);void sub_82449ED8(PPCContext&,uint8_t*);
// Explicit fixture boundaries. The selected branch uses an unparented scenery
// object, local/non-local identity and a valid physics handle. No actual world executes.
void sub_823C1E28(PPCContext& c,uint8_t* base){std::memset(base+c.r3.u32,0,76);}
void sub_823C2020(PPCContext& c,uint8_t*){c.r3.u32=variant;}
void sub_823C5C28(PPCContext&,uint8_t*){}
void sub_82271460(PPCContext& c,uint8_t*){if(c.r3.u32!=2)throw std::runtime_error("resolve wrong object");c.r3.u32=resolveObject?object:0;}
void sub_8230DE48(PPCContext& c,uint8_t*){c.r3.u32=sessionType;}
void sub_82451DA8(PPCContext& c,uint8_t*){c.r3.u32=eligible;}
void sub_823C5DD0(PPCContext& c,uint8_t* base){
 if(REX_LOAD_U16(c.r5.u32+62)!=64)throw std::runtime_error("release variant physics flags");++variantWrites;
}
void sub_8220BD58(PPCContext& c,uint8_t*){if(c.r3.u32!=2)throw std::runtime_error("release body target");fixedCall=c.r4.u32;}
void sub_8244F300(PPCContext&,uint8_t*){++releaseDynamic;}
void sub_82939170(PPCContext& c,uint8_t*){if(c.r3.u32!=3)throw std::runtime_error("unit detach target");}
void sub_8281EF50(PPCContext& c,uint8_t* base){
 if(c.r3.u32!=2||c.r4.u32!=editor+324||c.r5.u32!=editor+288||c.r6.u32!=editor+312||REX_LOAD_U32(editor)!=2)
  throw std::runtime_error("restore arguments or ordering");++restores;
}
void sub_827FB1A8(PPCContext&,uint8_t*){++mismatches;}
void sub_82450CD8(PPCContext& c,uint8_t* base){if(c.r3.u32!=0||c.r4.u32!=2||REX_LOAD_U32(editor)!=0xffffffff)throw std::runtime_error("delete arguments/order");++deletes;}
void sub_822BE858(PPCContext& c,uint8_t*){c.r3.u32=0xffffffff;}
void sub_8298E798(PPCContext& c,uint8_t*){c.r3.u32=0;}
void sub_8244F838(PPCContext&,uint8_t*){}
void sub_8225EA20(PPCContext& c,uint8_t* base){std::memset(base+c.r4.u32,0,16);}
void sub_822ED938(PPCContext& c,uint8_t*){c.r3.u32=localPlayer;}
void sub_82505DE8(PPCContext& c,uint8_t*){c.r3.u32=0xffffffff;}
void sub_822E8E20(PPCContext& c,uint8_t*){c.r3.u32=0xffffffff;}
void sub_825826B0(PPCContext&,uint8_t*){}
void sub_8312D878(PPCContext&,uint8_t*){}
void sub_822FF770(PPCContext&,uint8_t*){}
void sub_8244F5D8(PPCContext&,uint8_t*){}
void sub_8244A180(PPCContext& c,uint8_t*){c.r3.u32=1;}
void sub_8244A2A0(PPCContext&,uint8_t*){}
void sub_82452820(PPCContext& c,uint8_t* base){
 ++poseCalls;std::memset(base+c.r4.u32,0,52);put(base,c.r4.u32,1);
 put(base,c.r4.u32+4,1);put(base,c.r4.u32+20,1);put(base,c.r4.u32+36,1);
}
void sub_82282580(PPCContext&,uint8_t*){} // Fixture pose is already within bounds.
void sub_82260B58(PPCContext& c,uint8_t* base){
 for(unsigned i=0;i<3;++i)put(base,c.r4.u32+i*4,c.r3.u32==2?float(i+10):0.f);
}
void sub_82243068(PPCContext& c,uint8_t* base){for(unsigned i=0;i<3;++i)put(base,c.r4.u32+i*4,i==axis?1.f:0.f);}
void sub_82452C28(PPCContext& c,uint8_t*){c.f1.f64=multiplier;}
void sub_82452BB8(PPCContext& c,uint8_t*){c.f1.f64=maximum;}
void sub_82452AD8(PPCContext& c,uint8_t*){c.f1.f64=7.5;}
#define UNEXPECTED(name) void name(PPCContext&,uint8_t*){throw std::runtime_error("uncovered branch: " #name);}

UNEXPECTED(sub_82936B78)
UNEXPECTED(sub_829449D0) UNEXPECTED(sub_8295D1A8)
UNEXPECTED(sub_8297E5F8)
}
int main(){try{
 auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ULL,MEM_RESERVE,PAGE_NOACCESS));
 if(!base||!VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE)||!VirtualAlloc(base+0x82000000,0x2f40000,MEM_COMMIT,PAGE_READWRITE))throw std::runtime_error("allocation");
 std::ifstream image("work/h4-forge-research/h4-image.bin",std::ios::binary);
 if(!image.read(reinterpret_cast<char*>(base+0x82000000),0x2f38000))throw std::runtime_error("image");
 REX_STORE_U32(0x10000,tls);REX_STORE_U32(tls+28,game);
 REX_STORE_U32(tls+24,0x30000);REX_STORE_U32(0x30000+68,0x31000);REX_STORE_U32(0x31000+36,3);
 REX_STORE_U32(tls+4432,0x40000);REX_STORE_U32(0x40000+68,0x41000);REX_STORE_U32(0x41000+2*16+12,object);
 REX_STORE_U32(object+36,0xffffffff);REX_STORE_U16(object+62,0);REX_STORE_U8(object+178,2);REX_STORE_U32(object+240,0);
 REX_STORE_U32(0x83625160,0x70000);REX_STORE_U32(0x70000+68,0x71000);REX_STORE_U32(0x71000+52,1);
 REX_STORE_U32(0x833f7ea0,0x72000);REX_STORE_U32(0x833f7e98,0x72010);
 unsigned cases=0;
 for(bool restore:{false,true})for(bool fixed:{false,true})for(bool local:{false,true})for(axis=0;axis<3;++axis)for(float radius:{.1f,1.f,4.f,10.f,20.f})for(float distance:{-2.f,0.f,3.f,12.f,30.f})for(bool compensate:{false,true}){
  restorePose=restore;forceFixed=fixed;localPlayer=local;std::memset(base+editor,0,336);REX_STORE_U32(editor,0xffffffff);put(base,object+76,radius);
  REX_STORE_U8(editor+82,1);REX_STORE_U32(editor+224,4);put(base,editor+268,.75f);
  REX_STORE_U8(0x31000+1888,compensate);put(base,0x31000+1892,2);
  auto invoke=[&](bool release){
   PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=0x12345678;
   if(release){
    restores=variantWrites=releaseDynamic=0;fixedCall=-1;REX_STORE_U8(editor+280,restorePose);
    c.r3.u32=0;c.r4.u32=2;c.r5.u32=forceFixed;grab_test::sub_82451500(c,base);
    if(restores!=unsigned(restorePose)||variantWrites!=unsigned(forceFixed)||fixedCall!=int(forceFixed)||releaseDynamic!=unsigned(!forceFixed))
      throw std::runtime_error("release restore/physics branch mismatch");
   }
   else {c.r3.u32=0;c.r4.u32=2;grab_test::sub_82450E10(c,base);}
   if(c.r1.u32!=0x180000||c.lr!=0x12345678)throw std::runtime_error("register restoration");
   if(REX_LOAD_U8(editor+82)!=1||REX_LOAD_U32(editor+224)!=4||get(base,editor+268)!=.75f)throw std::runtime_error("editor preferences lost");
  };
  for(unsigned grab=0;grab<2;++grab){
   const float requested=distance+grab*2.f;
   for(unsigned i=0;i<3;++i)put(base,editor+44+i*4,i==axis?requested:100.f);
   poseCalls=0;invoke(false);
   const float lo=std::max(radius*1.25f,radius+.4f),hi=std::min(multiplier*lo,maximum);
   const float expected=std::min(std::max(requested-(compensate?.6f:0.f),lo),hi);
   if(std::abs(get(base,editor+28)-expected)>1e-4f||REX_LOAD_U32(editor)!=2||poseCalls!=1)throw std::runtime_error("grab distance/state mismatch");
   for(unsigned i=0;i<3;++i)if(get(base,editor+68+i*4)!=float(i+10))throw std::runtime_error("grab position snapshot");
   invoke(true);
   if(REX_LOAD_U32(editor)!=0xffffffff||get(base,editor+28)!=7.5f)throw std::runtime_error("release reset mismatch");
  }
  ++cases;
 }
 unsigned rejectionCases=0;
 for(unsigned mode=0;mode<6;++mode){
  // Invalid placement is deleted in ordinary sessions, retained in session4;
  // stale release datum and failed object resolution leave the held state intact.
  sessionType=mode==1?4:0;eligible=mode>=2;resolveObject=mode!=4;
  deletes=mismatches=variantWrites=releaseDynamic=restores=0;fixedCall=-1;
  REX_STORE_U32(editor,2);REX_STORE_U8(editor+280,0);
  PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=123;
  c.r3.u32=0;c.r4.u32=mode==3?99:2;c.r5.u32=0;
  if(mode==5)REX_STORE_U32(object+36,123); // Parent attached: skip root physics changes.
  grab_test::sub_82451500(c,base);
  bool held=mode==3||mode==4;
  if(REX_LOAD_U32(editor)!=(held?2u:0xffffffffu)||deletes!=unsigned(mode==0)||mismatches!=unsigned(mode==3)||
     variantWrites||restores||fixedCall!=((mode==1||mode==2)?0:-1)||releaseDynamic!=unsigned(mode==1||mode==2)||
     c.r1.u32!=0x180000||c.lr!=123)throw std::runtime_error("release rejection/parent branch");
  REX_STORE_U32(object+36,0xffffffff);++rejectionCases;
 }
 std::cout<<"PASS "<<rejectionCases<<" release rejection/session/parent cases; callbacks simulated.\n";
 std::cout<<"PASS "<<cases<<" original grab/release/regrab sequences (2400 grabs); projection, size clamp, compensation, retained preferences, pose-restore ordering and release physics choices checked. World/config services simulated; local/non-local unparented scenery, no selected monitor or replication recipients.\n";



 unsigned resetCases=0;
 for(unsigned alignment:{0u,4u,8u,12u})for(unsigned poison:{0x55u,0xaau,0xffu}){
  uint32_t packet=0x88010+alignment;std::memset(base+packet-16,poison,288);
  PPCContext c{};c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=1252;c.r3.u32=packet;
  grab_test::sub_822C5470(c,base);
  if(c.r1.u32!=0x180000||c.lr!=1252||REX_LOAD_U32(packet)!=0||REX_LOAD_U8(packet+4)!=255||REX_LOAD_U64(packet+8)!=0||REX_LOAD_U32(packet+64)!=0)throw std::runtime_error("packet reset identity/actions");
  for(unsigned offset:{28u,32u,44u,48u,56u,60u})if(get(base,packet+offset)!=0.f)throw std::runtime_error("packet reset analog values");
  for(unsigned offset:{68u,72u,76u})if(REX_LOAD_U16(packet+offset)!=65535)throw std::runtime_error("packet reset invalid short");
  for(unsigned offset:{70u,71u,74u})if(REX_LOAD_U8(packet+offset)!=255)throw std::runtime_error("packet reset invalid byte");
  for(unsigned offset:{80u,88u,92u,104u,116u,128u})if(REX_LOAD_U32(packet+offset)!=0xffffffff)throw std::runtime_error("packet reset invalid reference");
  for(unsigned i=0;i<16;++i)if(REX_LOAD_U8(packet-16+i)!=poison||REX_LOAD_U8(packet+256+i)!=poison)throw std::runtime_error("packet reset escaped buffer");
  ++resetCases;
 }
 std::cout<<"PASS "<<resetCases<<" original action-packet resets: analog/action clearing, invalid reference defaults, alignment and buffer boundaries; memory-clear primitive controlled.\n";
 auto setupEditGate=[&](){
  REX_STORE_U32(game+50364,1);REX_STORE_U32(tls+48,0x85000);std::memset(base+0x85000,0,128);
  REX_STORE_U8(0x85000,1);REX_STORE_U32(0x85000+24,4);REX_STORE_U32(0x85000+64,1);
  REX_STORE_U32(editor+20,1);REX_STORE_U32(editor,2);REX_STORE_U32(0x31000+36,3);
  REX_STORE_U32(0x31000+4,0);REX_STORE_U32(0x31000+1104,0);REX_STORE_U8(0x31000+1084,0);
  REX_STORE_U32(0x41000+3*16+12,0x86000);REX_STORE_U32(0x86000+8,42);
 };
 unsigned nativeGateCases=0;
 for(unsigned mode=0;mode<17;++mode){
  setupEditGate();bool expected=mode==0||mode==13||mode==14||mode==16;uint32_t playerId=0;
  switch(mode){
   case 1:playerId=0xffffffff;break;
   case 2:REX_STORE_U32(game+50364,0);break;
   case 3:REX_STORE_U32(game+50364,6);break;
   case 4:REX_STORE_U32(tls+48,0);break;
   case 5:REX_STORE_U8(0x85000,0);break;
   case 6:REX_STORE_U32(0x85000+24,1);break;
   case 7:REX_STORE_U32(0x85000+64,0);break;
   case 8:REX_STORE_U32(editor+20,0);break;
   case 9:REX_STORE_U32(0x31000+36,0xffffffff);break;
   case 10:REX_STORE_U32(0x86000+8,41);break;
   case 11:REX_STORE_U32(0x31000+4,8);break;
   case 12:REX_STORE_U32(editor+20,2);break;
   case 13:REX_STORE_U8(0x85000,0);REX_STORE_U8(0x85000+1,1);break;
   case 14:REX_STORE_U32(game+50364,5);break;
   case 15:REX_STORE_U32(0x85000+24,3);break;
   case 16:REX_STORE_U32(editor,0xffffffff);break;
  }
  REX_STORE_U32(0x87000,99);PPCContext c{};c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=1251;c.r3.u32=playerId;c.r4.u32=0x87000;
  grab_test::sub_82232AC8(c,base);
  if(bool(c.r3.u32)!=expected||REX_LOAD_U32(0x87000)!=(expected?(mode==16?0xffffffff:2):99)||c.r1.u32!=0x180000||c.lr!=1251){std::cerr<<"gate mode="<<mode<<" result="<<c.r3.u32<<"\n";throw std::runtime_error("original edit eligibility");}++nativeGateCases;
 }
 std::cout<<"PASS "<<nativeGateCases<<" original edit eligibility cases: session, mode, player, monitor tag, held output and rejection preservation. Monitor tag lookup controlled.\n";

 unsigned decayCases=0;
 for(bool active:{false,true})for(rotationApplied=false;;rotationApplied=true){
  for(bool forced:{false,true})for(float prior:{0.f,.2f})for(float dt:{.016f,.05f,.1f}){
   setupEditGate();REX_STORE_U32(tls+88,0x89000);put(base,0x89000+8,dt);
   REX_STORE_U8(0x8407effb,forced);REX_STORE_U8(0x31000+1888,active);
   put(base,0x31000+1896,.25f);put(base,0x31000+1900,.5f);put(base,0x31000+1904,-.75f);
   put(base,editor+40,prior);REX_STORE_U8(editor+81,2);
   REX_STORE_U32(0x89100,0);REX_STORE_U32(0x89104,editor);
   REX_STORE_U32(editor,rotationApplied?2:0xffffffff);REX_STORE_U64(object+256,0x100);REX_STORE_U32(object+240,0);
   REX_STORE_U32(0x71000+48,0x90000);REX_STORE_U32(0x71000+52,1);REX_STORE_U32(0x71000+16,0);REX_STORE_U32(0x90000+52,0x91000);REX_STORE_U8(0x91000+232,1);
   put(base,0x86000+1260,1);put(base,0x86000+1264,0);put(base,0x86000+1268,0);
   for(unsigned i=0;i<13;++i)put(base,editor+84+i*4,0);
   put(base,editor+84,1);put(base,editor+88,1);put(base,editor+104,1);put(base,editor+120,1);
   put(base,editor+124,11);put(base,editor+128,12);put(base,editor+132,13);
   PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=1253;c.r3.u32=0x89100;
   PPCContext gate=c;gate.r3.u32=2;grab_test::sub_8244A6A8(gate,base);
   grab_test::sub_8244A7D0(c,base);
   float expected=prior==0&&(forced||(active&&rotationApplied))?dt*5:prior;
   if(std::abs(get(base,editor+40)-expected)>1e-6||REX_LOAD_U8(editor+81)!=(2|(active&&rotationApplied))||c.lr!=1253||c.r1.u32!=0x180000){std::cerr<<"active="<<active<<" applied="<<rotationApplied<<" forced="<<forced<<" prior="<<prior<<" dt="<<dt<<" decay="<<get(base,editor+40)<<" expected="<<expected<<" gate="<<gate.r3.u32<<" type="<<unsigned(REX_LOAD_U8(object+178))<<" f1="<<c.f1.f64<<" flag="<<unsigned(REX_LOAD_U8(editor+81))<<"\n";throw std::runtime_error("camera offset decay initialization");}

   float angle=active&&rotationApplied?std::sqrt(.3125f*.3125f+2.8125f*2.8125f+1.25f*1.25f)*dt:0.f;
   float trace=get(base,editor+88)+get(base,editor+104)+get(base,editor+120);
   if(std::abs(trace-(1+2*std::cos(angle)))>1e-4f||get(base,editor+84)!=1||get(base,editor+124)!=11||get(base,editor+128)!=12||get(base,editor+132)!=13)throw std::runtime_error("original rotation angle/translation");
   for(unsigned i=0;i<3;++i)for(unsigned j=0;j<3;++j){float dot=0;for(unsigned k=0;k<3;++k)dot+=get(base,editor+88+i*12+k*4)*get(base,editor+88+j*12+k*4);if(std::abs(dot-(i==j?1.f:0.f))>1e-4f)throw std::runtime_error("original rotation orthonormality");}

   const float rawAxis[3]={-.3125f,-2.8125f,-1.25f};float norm=std::sqrt(.3125f*.3125f+2.8125f*2.8125f+1.25f*1.25f);
   for(unsigned column=0;column<3;++column)for(unsigned row=0;row<3;++row){
    float u[3]={rawAxis[0]/norm,rawAxis[1]/norm,rawAxis[2]/norm};float cross=0;
    if(row==(column+1)%3)cross=u[(column+2)%3];
    if(row==(column+2)%3)cross=-u[(column+1)%3];
    float expectedComponent=(row==column?std::cos(angle):0.f)+cross*std::sin(angle)+u[row]*u[column]*(1-std::cos(angle));
    if(std::abs(get(base,editor+88+column*12+row*4)-expectedComponent)>1e-4f)throw std::runtime_error("original rotation signed axis basis");
   }
   ++decayCases;
  }
  if(rotationApplied)break;
 }
 REX_STORE_U8(0x8407effb,0);
 std::cout<<"PASS "<<decayCases<<" original rotation-input/offset-decay transitions: active/applied/forced gates, sticky flag and preserved nonzero decay. Original rotation transform/math execute; signed-axis Rodrigues basis, orthonormality, scale and translation checked.\n";

 unsigned rotationCases=0;
 const float rotationInputs[][3]={{0,0,0},{1,0,0},{-.5f,0,0},{0,1,0},{0,0,1},{.5f,-.75f,-.25f},{.5f,0,.5f},{.001f,0,0}};
 for(unsigned viewAxis=0;viewAxis<3;++viewAxis)for(float viewSign:{-1.f,1.f})for(auto& input:rotationInputs)for(float dt:{0.f,.00001f,.016f,.05f})for(bool initialYaw:{false,true}){
  setupEditGate();put(base,0x89000+8,dt);REX_STORE_U32(tls+88,0x89000);
  float view[3]={};view[viewAxis]=viewSign;
  float lateral[3]={-view[1],view[0],0};
  float axisVector[3];for(unsigned i=0;i<3;++i){
   put(base,0x86000+1260+i*4,view[i]);
   axisVector[i]=5*(input[1]*std::abs(input[1])*lateral[i]+input[2]*std::abs(input[2])*view[i]-(i==2?input[0]*std::abs(input[0]):0));
  }
  float norm=std::sqrt(axisVector[0]*axisVector[0]+axisVector[1]*axisVector[1]+axisVector[2]*axisVector[2]);
  float angle=(norm<.0001f?0:norm)*dt;bool changed=angle>.0001f;if(!changed)angle=0;
  float initial[3][3]={{1,0,0},{0,1,0},{0,0,1}};
  if(initialYaw){initial[0][0]=0;initial[0][1]=1;initial[1][0]=-1;initial[1][1]=0;}
  put(base,editor+84,1);for(unsigned col=0;col<3;++col)for(unsigned row=0;row<3;++row)put(base,editor+88+col*12+row*4,initial[col][row]);
  put(base,editor+124,11);put(base,editor+128,12);put(base,editor+132,13);
  PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=1254;c.r3.u32=editor;c.r4.u32=0x86000;c.f1.f64=input[0];c.f2.f64=input[1];c.f3.f64=input[2];
  grab_test::sub_8244B518(c,base);
  if(bool(c.r3.u32)!=changed||c.r1.u32!=0x180000||c.lr!=1254||get(base,editor+84)!=1||get(base,editor+124)!=11||get(base,editor+128)!=12||get(base,editor+132)!=13)throw std::runtime_error("rotation view/threshold/state");
  float u[3]={};if(norm>0)for(unsigned i=0;i<3;++i)u[i]=axisVector[i]/norm;
  for(unsigned col=0;col<3;++col){
   float dot=0;for(unsigned i=0;i<3;++i)dot+=u[i]*initial[col][i];
   for(unsigned row=0;row<3;++row){unsigned a=(row+1)%3,b=(row+2)%3;float cross=u[a]*initial[col][b]-u[b]*initial[col][a];float expected=initial[col][row]*std::cos(angle)+cross*std::sin(angle)+u[row]*dot*(1-std::cos(angle));
    if(std::abs(get(base,editor+88+col*12+row*4)-expected)>1e-4f)throw std::runtime_error("rotation view/combined-input composition");
   }
  }++rotationCases;
 }
 std::cout<<"PASS "<<rotationCases<<" original analog rotations: six view directions, vertical degeneracy/cancellation, signed and combined inputs, tiny/zero angles, identity/yaw initial poses. Independent Rodrigues composition; synthetic physics eligibility.\n";
 unsigned inputCases=0;
 for(editInputGate=0;editInputGate<3;++editInputGate)for(float trigger:{0.f,.1f,.11f,1.f})for(float x:{-1.f,0.f,.5f,1.f})for(float y:{-1.f,0.f,.5f,1.f})for(bool rotate:{false,true}){
  setupEditGate();if(editInputGate==1)REX_STORE_U32(game+50364,0);if(editInputGate==2)REX_STORE_U32(editor,0xffffffff);
  constexpr uint32_t input=0x80000,player=0x31000;
  std::memset(base+input,0,64);put(base,input+28,x);put(base,input+32,y);put(base,input+56,trigger);REX_STORE_U8(input+40,rotate);
  put(base,input+44,x);put(base,input+48,y);
  for(unsigned offset:{1892u,1896u,1900u,1904u})put(base,player+offset,99.f);
  REX_STORE_U8(player+1888,1);put(base,object+76,1.f);put(base,editor+28,3.f);
  bool enabled=editInputGate==0&&trigger>.1f;
  float selected=std::abs(x)>std::abs(y)?x:0.f;
  for(unsigned tick=0;tick<2;++tick){
   PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=1250;c.r3.u32=0;c.r4.u32=input;
   grab_test::sub_82368CE0(c,base);
   if(bool(REX_LOAD_U8(player+1888))!=enabled||c.r1.u32!=0x180000||c.lr!=1250)throw std::runtime_error("edit input gate/frame");
   if(enabled){
    if(get(base,player+1892)!=(tick?0.f:selected)||get(base,player+1896)!=(tick?0.f:(std::abs(x)>std::abs(y)?0.f:y))||get(base,input+28)!=0.f||get(base,input+32)!=0.f)throw std::runtime_error("edit input consumption");
    float rx=rotate?(std::abs(x)>std::abs(y)?x:0.f):99.f;
    float ry=rotate?(std::abs(x)>std::abs(y)?0.f:y):99.f;
    if(get(base,player+1900)!=rx||get(base,player+1904)!=ry)throw std::runtime_error("rotation dominant-axis selection");
   }else if(get(base,input+28)!=x||get(base,input+32)!=y||get(base,player+1892)!=99.f)throw std::runtime_error("inactive input mutation");
   c.r3.u32=0;c.r4.u32=2;c.r5.u32=editor+28;
   grab_test::sub_82452738(c,base);
   float expected=3.f-(enabled?selected*.3f:0.f);
   if(std::abs(get(base,editor+28)-expected)>1e-5f||c.r1.u32!=0x180000||c.lr!=1250)throw std::runtime_error("input to retained-distance clamp");
   ++inputCases;
  }
 }
 std::cout<<"PASS "<<inputCases<<" original edit-input to distance-clamp steps: gate/threshold, dominant-axis ties, signed input, consumption and repeated update. Original eligibility executes; monitor tag lookup/config services controlled.\n";
 VirtualFree(base,0,MEM_RELEASE);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
