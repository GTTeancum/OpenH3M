#include "forge_original.h"
#include <windows.h>
#include <bit>
#include <cmath>
#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
static constexpr uint32_t body=0x30000,target=0x31000,gains=0x32000,table=0x33000;
static unsigned linearCalls,angularCalls,relocations,activations;
static unsigned orientationCalls;
static float expectedHeading[3];
static int snapAxis;
static float snapSign;
static float sceneMarkerDistance=.1f;
static bool sceneHasCandidate=true;
static bool integrateHeldBody=false;
static unsigned selectionCalls;
static bool cameraFixture;
static bool monitorWorldHit;
static float worldFraction=.25f,worldLimit=1.f;
static unsigned cameraRayCalls;
static int selectedCameraRay=-1;
static std::array<std::array<float,6>,7> cameraSegments;
static float cameraHeldPosition[3];
static void put(uint8_t* base,uint32_t a,float f){REX_STORE_U32(a,std::bit_cast<uint32_t>(f));}
static float get(uint8_t* base,uint32_t a){return std::bit_cast<float>(REX_LOAD_U32(a));}
namespace h4_forge_original {
void sub_82C01FB8(PPCContext&,uint8_t*);
void sub_83292E30(PPCContext&,uint8_t*);
void sub_83292E50(PPCContext&,uint8_t*);
void sub_82C023E8(PPCContext&,uint8_t*);
void sub_8249B418(PPCContext&,uint8_t*);
void sub_82452930(PPCContext&,uint8_t*);
void sub_8244A8D8(PPCContext&,uint8_t*);
void sub_824BEA10(PPCContext&,uint8_t*);
void sub_824BEAD0(PPCContext&,uint8_t*);
void sub_8244B338(PPCContext&,uint8_t*);
void sub_8244AF48(PPCContext&,uint8_t*);
void sub_82416640(PPCContext&,uint8_t*);
void sub_822528D8(PPCContext&,uint8_t*);
void sub_822B83C0(PPCContext& c,uint8_t* base){if(c.r5.u32!=8198)throw std::runtime_error("unexpected shape metadata type");REX_STORE_U64(c.r3.u32,2);}
void sub_82271460(PPCContext& c,uint8_t*){c.r3.u32=c.r3.u32==2?0xa0000:c.r3.u32==3?0xa1000:0;}
void sub_8224DED0(PPCContext&,uint8_t*){throw std::runtime_error("uncovered category3 exception");}

void sub_824F5F78(PPCContext&,uint8_t*);
void sub_82415970(PPCContext& c,uint8_t*){cameraRayCalls=0;c.r3.u32=monitorWorldHit?1:0;}
void sub_82417550(PPCContext& c,uint8_t* base){
 uint32_t query=c.r3.u32,result=c.r4.u32;
 if(REX_LOAD_U64(query+4)!=0x100900000000ULL||REX_LOAD_U32(query)!=27||REX_LOAD_U8(query+292)!=2||REX_LOAD_U32(query+36)!=2||REX_LOAD_U32(query+40)!=3)
  throw std::runtime_error("original camera ray descriptor/filter list");
 unsigned ray=cameraRayCalls++;
 if(ray>=cameraSegments.size())throw std::runtime_error("unexpected extra camera ray");
 for(unsigned i=0;i<3;++i){cameraSegments[ray][i]=get(base,query+12+i*4);cameraSegments[ray][3+i]=get(base,query+24+i*4);}
 float fraction=selectedCameraRay>=0?(ray==unsigned(selectedCameraRay)?worldFraction:1.f):(ray==0?worldLimit:worldFraction);
 put(base,result+4,fraction);
 for(unsigned i=0;i<3;++i){float start=get(base,query+12+i*4),end=get(base,query+24+i*4);put(base,result+8+i*4,start+fraction*(end-start));}
 c.r3.u32=fraction<1?1:0;
}
void sub_824BEB50(PPCContext&,uint8_t*);
void sub_8226CD10(PPCContext& c,uint8_t*){
 if(!cameraFixture||c.r3.u32!=0x91010||c.f1.f64<0||c.f1.f64>1){std::cerr<<"curve pointer="<<std::hex<<c.r3.u32<<std::dec<<" input="<<c.f1.f64<<"\n";throw std::runtime_error("camera curve arguments");}
 c.f1.f64=.25; // Controlled curve result; original camera math remains unchanged.
}
void sub_82260CF0(PPCContext&,uint8_t*);
void sub_82260F08(PPCContext& c,uint8_t*){if(c.r3.u32!=4)throw std::runtime_error("physics gate argument");c.r3.u32=1;}
void sub_823C2020(PPCContext& c,uint8_t*){c.r3.u32=0x60000;}
void sub_82451BA8(PPCContext& c,uint8_t*){c.r3.u32=0;}
void sub_82235650(PPCContext& c,uint8_t*){c.r3.u32=0;}
void sub_822ED938(PPCContext& c,uint8_t*){c.r3.u32=0;}
void sub_821F2050(PPCContext& c,uint8_t* base){REX_STORE_U32(c.r8.u32,7);c.r3.u32=sceneHasCandidate?1:0;++selectionCalls;}
void sub_82582A68(PPCContext& c,uint8_t*){c.r3.u32=0x193;}
void sub_82937F50(PPCContext& c,uint8_t*){c.r3.u32=1;}
void sub_8293A3B0(PPCContext& c,uint8_t* base){
 if(cameraFixture){for(unsigned i=0;i<3;++i)put(base,c.r4.u32+i*4,cameraHeldPosition[i]);return;}
 for(unsigned i=0;i<3;++i)put(base,c.r4.u32+i*4,c.r3.u32==7?(i==unsigned(snapAxis)?snapSign*sceneMarkerDistance:0.f):(integrateHeldBody?get(base,body+288+i*4):0.f));
}
void sub_82582610(PPCContext& c,uint8_t* base){
 // Synthetic scene markers; selection, scoring, pair validation and alignment are original.
 uint32_t out=c.r4.u32;bool destination=c.r3.u32==7;
 std::memset(base+out,0,112);put(base,out+4,1);put(base,out+56,1);
 for(uint32_t matrix:{out+8,out+60})for(unsigned i=0;i<9;++i)put(base,matrix+i*4,i%4==0?1.f:0.f);
 if(destination)put(base,out+96+snapAxis*4,snapSign*sceneMarkerDistance);
 else if(integrateHeldBody)for(unsigned i=0;i<3;++i)put(base,out+96+i*4,get(base,body+288+i*4));
 c.r3.u32=1;
}
void sub_82340E60(PPCContext& c,uint8_t*){c.r3.u32=0x53000;}
#define UNEXPECTED(name) void name(PPCContext&,uint8_t*){throw std::runtime_error("uncovered placement service: " #name);}
UNEXPECTED(sub_822AD348) UNEXPECTED(sub_82451A38)
UNEXPECTED(sub_825826B0)
UNEXPECTED(sub_8281F450) UNEXPECTED(sub_822633F0)
UNEXPECTED(sub_8281F4E0) UNEXPECTED(sub_823FC348) UNEXPECTED(sub_82260F70)
#undef UNEXPECTED
void sub_822AAB18(PPCContext& c,uint8_t* base){
 if(c.r3.u32!=2||c.r5.u32!=0x45000+112)throw std::runtime_error("orientation notification arguments");
 for(unsigned i=0;i<3;++i){
  if(std::abs(get(base,c.r4.u32+i*4)-float(i+1))>1e-5f||std::abs(get(base,c.r5.u32+i*4)-expectedHeading[i])>1e-5f)
   throw std::runtime_error("old/new orientation notification values");
 }
 ++orientationCalls;
}
void sub_82CD55F0(PPCContext& c,uint8_t*) {
 if(c.r3.u32!=body)throw std::runtime_error("wrong activation body");++activations;
}
void sub_82CD40A8(PPCContext& c,uint8_t* base) {
 if(c.r3.u32!=body)throw std::runtime_error("wrong relocation body");
 std::memcpy(base+body+288,base+c.r4.u32,16);
 std::memcpy(base+body+352,base+c.r5.u32,16);++relocations;
}
void controller_dispatch(PPCContext& c,uint8_t* base,uint32_t address){
 if(address==0x108){REX_STORE_U8(c.r3.u32,1);return;}
 if(c.r3.u32!=body+224)throw std::runtime_error("wrong motion receiver");
 uint32_t offset;
 if(address==0x100){offset=432;++linearCalls;}
 else if(address==0x104){offset=448;++angularCalls;}
 else throw std::runtime_error("unexpected callback");
 std::memcpy(base+body+offset,base+c.r4.u32,16);
}
}
namespace h3_collision {
void sub_820AF170(PPCContext&,uint8_t*);
void sub_82629000(PPCContext&,uint8_t*);
void sub_82662340(PPCContext&,uint8_t*);
void sub_82662350(PPCContext&,uint8_t*);
static constexpr uint32_t h3body=0x120000,h3table=0x121000;
static unsigned linear,angular,wakes,relocated;
void sub_82651968(PPCContext& c,uint8_t*){if(c.r3.u32!=h3body)throw std::runtime_error("H3 controller wake body");++wakes;}
void sub_8265FD48(PPCContext& c,uint8_t* base){
 if(c.r3.u32!=h3body)throw std::runtime_error("H3 controller relocation body");
 std::memcpy(base+h3body+224,base+c.r4.u32,16);std::memcpy(base+h3body+288,base+c.r5.u32,16);++relocated;
}
void controller_dispatch(PPCContext& c,uint8_t* base,uint32_t address){
 if(c.r3.u32!=h3body+160)throw std::runtime_error("H3 motion receiver");
 if(address==0x200){++linear;sub_82662340(c,base);}
 else if(address==0x204){++angular;sub_82662350(c,base);}
 else throw std::runtime_error("H3 motion callback");
}
}
static bool ownershipPlayerValid=true;
namespace h4_ownership {
void sub_822ED938(PPCContext&,uint8_t*);
void sub_822714E0(PPCContext& c,uint8_t* base){
 if(c.r3.u32!=0xd0000||(c.r4.u32&65535)>=16)throw std::runtime_error("ownership player lookup arguments");
 c.r3.u32=ownershipPlayerValid?REX_LOAD_U32(c.r3.u32+68)+(c.r4.u32&65535)*4144:0;
}
}
namespace h3_ownership {void sub_821F0688(PPCContext&,uint8_t*);}
int main(){try{
 auto base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ULL,MEM_RESERVE,PAGE_NOACCESS));
 if(!base||!VirtualAlloc(base,0x200000,MEM_COMMIT,PAGE_READWRITE)||
    !VirtualAlloc(base+0x82000000,0x2f40000,MEM_COMMIT,PAGE_READWRITE))throw std::runtime_error("allocation");
 std::ifstream image("work/h4-forge-research/h4-image.bin",std::ios::binary);
 if(!image.read(reinterpret_cast<char*>(base+0x82000000),0x2f38000))throw std::runtime_error("image");
 {PPCContext init{};init.r1.u32=0x180000;h4_forge_original::sub_83292E30(init,base);h4_forge_original::sub_83292E50(init,base);
 if(REX_LOAD_U64(0x845548b8)!=0x100900000000ULL)throw std::runtime_error("original monitor collision mask initialization");}

 unsigned cases=0;
 for(int axis=0;axis<3;++axis)for(float speed:{-5.f,0.f,5.f})for(float dt:{.1f,.2f}){
  std::memset(base+body,0,0x4000);linearCalls=angularCalls=relocations=activations=0;
  REX_STORE_U32(body+224,table);REX_STORE_U32(table+64,0x100);REX_STORE_U32(table+68,0x104);
  put(base,body+352+12,1);put(base,target+16+12,1);
  for(int i=0;i<4;++i){put(base,gains+i*4,1/dt);put(base,gains+16+i*4,1/dt);
   put(base,gains+32+i*4,1/dt);put(base,gains+48+i*4,1/dt);}
  put(base,gains+64,2);put(base,gains+68,2);put(base,gains+72,4);
  put(base,target+32+axis*4,speed);
  PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r3.u32=target;c.r4.u32=gains;c.r7.u32=body;c.f1.f64=dt;
  h4_forge_original::sub_82C01FB8(c,base);
  const float expected=speed==0?0:std::copysign(2*dt,speed);
  if(std::abs(get(base,body+432+axis*4)-expected)>1e-5f||relocations||angularCalls||
     linearCalls!=unsigned(speed!=0)||c.r1.u32!=0x180000)throw std::runtime_error("controller correction mismatch");
  for(int i=0;i<3;++i)if(i!=axis&&get(base,body+432+i*4)!=0)throw std::runtime_error("cross-axis correction");
  ++cases;
 }
 // Separate large-error branch, with callbacks retaining their observed order.
 put(base,target,10);put(base,gains+72,1);relocations=0;
 PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r3.u32=target;c.r4.u32=gains;c.r7.u32=body;c.f1.f64=.2;
 h4_forge_original::sub_82C01FB8(c,base);
 if(relocations!=1||get(base,body+288)!=10)throw std::runtime_error("relocation branch");
 auto reset=[&](){
  std::memset(base+body,0,0x4000);linearCalls=angularCalls=relocations=activations=0;
  REX_STORE_U32(body+224,table);REX_STORE_U32(table+64,0x100);REX_STORE_U32(table+68,0x104);
  put(base,body+364,1);put(base,target+28,1);
  for(int i=0;i<16;++i)put(base,gains+i*4,5);
  put(base,gains+64,2);put(base,gains+68,2);put(base,gains+72,4);
 };
 auto run=[&](){
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;
  ctx.r3.u32=target;ctx.r4.u32=gains;ctx.r7.u32=body;ctx.f1.f64=.2f;
  h4_forge_original::sub_82C01FB8(ctx,base);
  if(ctx.r1.u32!=0x180000)throw std::runtime_error("controller stack");
 };
 unsigned rotationCases=0;
 for(int axis=0;axis<3;++axis)for(float angle:{-.5f,-.01f,.01f,.5f})for(float sign:{-1.f,1.f}){
  reset();put(base,target+16+axis*4,sign*std::sin(angle/2));put(base,target+28,sign*std::cos(angle/2));
  run();const float expected=std::clamp(10*std::sin(angle/2),-.4f,.4f);
  if(std::abs(get(base,body+448+axis*4)-expected)>1e-5f||linearCalls||angularCalls!=1||relocations||activations!=1)
   throw std::runtime_error("angular correction or quaternion sign mismatch");
  for(int i=0;i<3;++i)if(i!=axis&&get(base,body+448+i*4)!=0)throw std::runtime_error("cross-axis angular correction");
  ++rotationCases;
 }
 reset();put(base,body+432,5);
 for(unsigned tick=1;tick<=14;++tick){
  run();const float expected=std::max(0.f,5-.4f*tick);
  if(std::abs(get(base,body+432)-expected)>1e-5f||angularCalls||relocations)throw std::runtime_error("velocity braking sequence");
 }
 const auto stoppedCalls=linearCalls;run();
 if(linearCalls!=stoppedCalls)throw std::runtime_error("settled callback suppression");
 reset();put(base,body+432,3);put(base,target+32,3);run();
 if(linearCalls||angularCalls||get(base,body+432)!=3)throw std::runtime_error("matching velocity preservation");
 // Read the actual callback tolerance, exercising both sides without guessing it.
 const float epsilon=get(base,0x82000e04);
 if(!(epsilon>0&&epsilon<.01f))throw std::runtime_error("unexpected tolerance constant");
 reset();put(base,target+32,epsilon*.5f);run();
 if(linearCalls)throw std::runtime_error("sub-tolerance callback");
 reset();put(base,target+32,epsilon*2);run();
 if(linearCalls!=1)throw std::runtime_error("above-tolerance callback missing");
 unsigned builderCases=0;
 for(int axis=0;axis<3;++axis)for(float delta:{-.01f,1.f})for(float angle:{-.01f,.5f})for(float sign:{-1.f,1.f}){
  reset();constexpr uint32_t desired=0x34000,rotation=0x34100;
  std::memset(base+desired,0,0x200);
  put(base,desired+axis*4,delta);put(base,rotation+axis*4,sign*std::sin(angle/2));
  put(base,rotation+12,sign*std::cos(angle/2));
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;
  ctx.r3.u32=target;ctx.r4.u32=body+288;ctx.r5.u32=body+352;
  ctx.r6.u32=desired;ctx.r7.u32=rotation;ctx.f1.f64=5;
  h4_forge_original::sub_82C023E8(ctx,base);
  if(ctx.r1.u32!=0x180000||std::abs(get(base,target+32+axis*4)-delta*5)>1e-5f||
     std::abs(get(base,target+48+axis*4)-angle*5)>1e-3f)
   throw std::runtime_error("original target-builder velocity mismatch");
  if(get(base,target)!=0||get(base,target+28)!=1)throw std::runtime_error("builder must retain current transform");
  run();
  if(std::abs(get(base,body+432+axis*4)-std::clamp(delta*5,-.4f,.4f))>1e-5f||
     std::abs(get(base,body+448+axis*4)-std::clamp(angle*5,-.4f,.4f))>1e-3f||relocations)
   throw std::runtime_error("builder/controller chain mismatch");
  ++builderCases;
 }
 std::cout<<"PASS "<<cases<<" linear cases, "<<rotationCases<<" angular/sign cases, "<<builderCases<<" original target-builder/controller chains, relocation, 15-step braking/settling, matching velocity and two tolerance cases. Motion callbacks simulated; no collision-world or native Forge parity claim.\n";
 unsigned submissionCases=0;
 for(bool resolveObject:{false,true})for(unsigned index:{0u,1u})for(int axis=0;axis<3;++axis)
 for(float delta:{-1.f,0.f,.01f,1.f})for(float dt:{.1f,.2f}){
  reset();constexpr uint32_t instance=0x40000,records=0x41000,pose=0x42000,object=0x45000;
  std::memset(base+instance,0,0x6000);
  REX_STORE_U32(instance+48,records);REX_STORE_U32(instance+20,2);
  REX_STORE_U32(records+52,0x46000);REX_STORE_U32(records+60+52,0x46000);
  REX_STORE_U32(records+index*60+52,body);
  REX_STORE_U32(0x10000,0x11000);REX_STORE_U32(0x11000+4432,0x12000);
  REX_STORE_U32(0x12000+68,0x13000);REX_STORE_U32(0x13000+2*16+12,object);
  REX_STORE_U8(0x13000+2*16+4,1);REX_STORE_U32(object-12,2);
  REX_STORE_U32(object+240,0);REX_STORE_U32(0x83625160,0x14000);REX_STORE_U32(0x14000+68,instance);
  REX_STORE_U8(instance+24,index);REX_STORE_U32(instance+52,2);
  REX_STORE_U64(object+256,0x100000005ULL);
  put(base,pose,1);for(int i=0;i<9;++i)put(base,pose+4+i*4,i%4==0?1.f:0.f);
  for(int i=0;i<3;++i){put(base,body+288+i*4,float(i+2));put(base,pose+40+i*4,float(i+2)+(i==axis?delta:0));}
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
  ctx.r3.u32=instance;ctx.r4.u32=index;ctx.r5.u32=pose;ctx.f1.f64=dt;ctx.lr=1234;
  if(resolveObject){ctx.r3.u32=2;ctx.r4.u32=pose;h4_forge_original::sub_82452930(ctx,base);}
  else h4_forge_original::sub_8249B418(ctx,base);
  const float limit=get(base,0x82128a34)*dt; // Original constant table base +84.
  for(int i=0;i<3;++i){
   float desired=i==axis?delta/dt:0.f;
   if(std::abs(get(base,body+432+i*4)-std::clamp(desired,-limit,limit))>1e-4f||get(base,body+288+i*4)!=float(i+2))
    throw std::runtime_error("original physics submission velocity/position");
  }
  if(relocations||angularCalls||linearCalls!=unsigned(delta!=0)||ctx.lr!=1234||ctx.r1.u32!=0x180000||REX_LOAD_U64(object+256)!=0x140000005ULL)
   throw std::runtime_error("original physics submission body/flags/frame");
  ++submissionCases;
 }
 std::cout<<"PASS "<<submissionCases<<" original physics-instance submission chains, body indices0/1, signed translation and owner flag preservation. World callbacks simulated.\n";
 for(unsigned invalid=0;invalid<5;++invalid){
  reset();REX_STORE_U32(0x45000+240,invalid==0?0xffffffff:0);
  REX_STORE_U32(0x14000+68,invalid==1?0:0x40000);
  REX_STORE_U8(0x40000+24,invalid==2?255:invalid==3?2:127);
  REX_STORE_U64(0x45000+256,0x100000005ULL);
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
  ctx.r3.u32=2;ctx.r4.u32=0x42000;ctx.f1.f64=.2f;ctx.lr=1235;
  h4_forge_original::sub_82452930(ctx,base);
  if(linearCalls||angularCalls||activations||relocations||ctx.r1.u32!=0x180000||ctx.lr!=1235||REX_LOAD_U64(0x45000+256)!=0x100000005ULL)
   throw std::runtime_error("invalid physics resolver changed world");
 }
 std::cout<<"PASS 5 original resolver rejection cases: missing physics, null instance, negative/equal-count/out-of-range body indices.\n";
 unsigned orientationCases=0;
 for(unsigned type:{0u,1u})for(unsigned flaggedBody:{0u,1u,2u})
 for(unsigned direction=0;direction<4;++direction){
  reset();orientationCalls=0;std::memset(base+0x40000,0,0x6000);
  REX_STORE_U32(0x14000+68,0x40000);REX_STORE_U32(0x45000+240,0);REX_STORE_U32(0x45000-12,2);
  REX_STORE_U8(0x13000+2*16+4,type);REX_STORE_U32(0x40000+48,0x41000);
  REX_STORE_U32(0x40000+20,2);REX_STORE_U32(0x40000+52,2);REX_STORE_U32(0x41000+52,body);
  if(flaggedBody)REX_STORE_U8(0x41000+(flaggedBody-1)*60+56,1);
  const float yaw=direction==1?1.57079632679f:direction==2?-1.f:0.f;
  const float cp=direction==3?0.f:.8f,sp=direction==3?1.f:.6f;
  const float cy=std::cos(yaw),sy=std::sin(yaw);
  const float basis[9]={cp*cy,cp*sy,sp,-sy,cy,0,-sp*cy,-sp*sy,cp};
  put(base,0x42000,1);for(unsigned i=0;i<9;++i)put(base,0x42004+i*4,basis[i]);
  for(unsigned i=0;i<3;++i)put(base,0x45000+112+i*4,float(i+1));
  expectedHeading[0]=direction==3?1.f:cy;expectedHeading[1]=direction==3?0.f:sy;expectedHeading[2]=0;
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
  ctx.r3.u32=2;ctx.r4.u32=0x42000;ctx.f1.f64=.2f;ctx.lr=1236;
  h4_forge_original::sub_82452930(ctx,base);
  bool special=type==0&&flaggedBody!=0;
  if(orientationCalls!=unsigned(special)||ctx.lr!=1236||ctx.r1.u32!=0x180000)throw std::runtime_error("special orientation eligibility");
  if(special){
   if(angularCalls||linearCalls||relocations)throw std::runtime_error("special body must receive identity orientation");
   for(unsigned i=0;i<3;++i){
    // Resolver stores helper forward and UP, skipping the intermediate side vector.
    if(std::abs(get(base,0x45000+124+4*i)-(i==2?1.f:0.f))>1e-5f)throw std::runtime_error("special orientation up vector");
   }
  }
  ++orientationCases;
 }
 std::cout<<"PASS "<<orientationCases<<" original special-orientation cases; type/body-flag gates, horizontal heading, vertical fallback and identity physics basis. Orientation notification simulated and inspected.\n";
 unsigned placementTicks=0;
 for(unsigned sceneMotion=0;sceneMotion<3;++sceneMotion)for(bool magnets:{false,true})for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f}){
  if(sceneMotion==2&&!magnets)continue;
  const bool integrated=sceneMotion!=0,movingTarget=sceneMotion==2;
  integrateHeldBody=integrated;
  reset();std::memset(base+0x40000,0,0x60000);
  REX_STORE_U32(0x14000+68,0x40000);REX_STORE_U32(0x45000+240,0);REX_STORE_U32(0x45000-12,2);
  REX_STORE_U8(0x13000+2*16+4,1);REX_STORE_U32(0x40000+48,0x41000);
  REX_STORE_U32(0x40000+20,2);REX_STORE_U32(0x40000+52,1);REX_STORE_U32(0x41000+52,body);
  REX_STORE_U32(0x13000+3*16+12,0x47000);
  REX_STORE_U32(0x45000+36,0xffffffff);REX_STORE_U32(0x47000+36,0xffffffff);
  REX_STORE_U32(0x11000+24,0x15000);REX_STORE_U32(0x15000+68,0x48000);REX_STORE_U32(0x48000+36,3);
  REX_STORE_U32(0x11000+88,0x49000);put(base,0x49000+8,.05f);REX_STORE_U32(0x49000+12,1);
  REX_STORE_U32(0x835b6a50,0x4a000);REX_STORE_U32(0x4a000+4,0x4b000);put(base,0x4b000+1428,1);
  put(base,0x47000+1212,1);put(base,0x47000+1348+axis*4,sign);
  REX_STORE_U32(0x11000+28,0x70000);constexpr uint32_t editor=0x70000+6892,context=0x80000;
  REX_STORE_U32(context,0);REX_STORE_U32(context+4,editor);REX_STORE_U32(editor,2);
  REX_STORE_U8(editor+82,magnets);REX_STORE_U32(editor+268,2);REX_STORE_U32(0x8405d340,1);
  std::ifstream config("work/h4-forge-research/isolated/forge-globals.bin",std::ios::binary);
  if(!config.read(reinterpret_cast<char*>(base+0x53000),80))throw std::runtime_error("forge globals image");
  REX_STORE_U32(0x13000+7*16+12,0x4c000);put(base,0x45000+76,1);put(base,0x4c000+76,1);
  put(base,0x4c000+64+axis*4,sign*.1f);
  snapAxis=axis;snapSign=sign;sceneMarkerDistance=.1f;sceneHasCandidate=true;selectionCalls=0;
  put(base,editor+84,1);for(unsigned i=0;i<9;++i)put(base,editor+88+4*i,i%4==0?1.f:0.f);
  for(unsigned i=0;i<3;++i){put(base,0x60000+696+i*8,-100);put(base,0x60000+700+i*8,100);}
  for(unsigned tick=1;tick<=(magnets?9u:4u);++tick){
   if(movingTarget)sceneMarkerDistance=.1f+.02f*float(tick);
   bool stopped=magnets?(tick==3||tick>=5):tick==4;
   put(base,0x47000+1348+axis*4,stopped?0:sign);
   if(magnets&&tick==6)REX_STORE_U8(editor+82,0);
   if(magnets&&tick==7){REX_STORE_U8(editor+82,1);sceneMarkerDistance=3.f;}
   if(magnets&&tick==8)sceneHasCandidate=false;
   if(magnets&&tick==9){sceneMarkerDistance=movingTarget?.28f:.1f;sceneHasCandidate=true;}
   put(base,0x4c000+64+axis*4,sign*sceneMarkerDistance);
   PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=context;ctx.lr=1237;
   h4_forge_original::sub_8244A8D8(ctx,base);
   const float expected=sign*(magnets?(tick==1?.2f:tick<=3?.4f:.5f):std::min(.2f*float(tick),.5f));
   const float submitted=magnets&&(tick==3||tick==5||tick==9)?sign*sceneMarkerDistance:expected;
   const float priorPosition=get(base,body+288+axis*4);
   if(std::abs(get(base,editor+124+axis*4)-expected)>1e-5f||std::abs(get(base,body+432+axis*4)-(submitted-priorPosition)/.2f)>1e-4f||ctx.lr!=1237||ctx.r1.u32!=0x180000||REX_LOAD_U32(editor+4)!=(magnets&&(tick<6||tick==7||tick==9)?7u:0xffffffffu))
    {std::cerr<<"tick="<<tick<<" magnets="<<magnets<<" axis="<<axis<<" editor="<<get(base,editor+124+axis*4)<<" velocity="<<get(base,body+432+axis*4)<<" expected_submission="<<submitted<<" candidate="<<REX_LOAD_U32(editor+4)<<"\n";throw std::runtime_error("persistent placement target/controller chain");}
   if(angularCalls||relocations)throw std::runtime_error("unexpected placement rotation/relocation");
   if(integrated)for(unsigned i=0;i<3;++i){
    float next=get(base,body+288+i*4)+.05f*get(base,body+432+i*4);
    put(base,body+288+i*4,next);put(base,0x45000+64+i*4,next);
   }
   ++placementTicks;
  }
  if(selectionCalls!=(magnets?8u:0u))throw std::runtime_error("magnet selection cadence");
 }
 integrateHeldBody=false;
 std::cout<<"PASS "<<placementTicks<<" original held-update ticks through bounds/limit, magnet gate/alignment, object resolver and physics controller; accumulation, stop/snap, resume/unsnap, disable, candidate loss/reacquisition checked. 78 stationary-body, 78 integrated-body and 54 integrated-body/moving-target ticks. Synthetic collision-free world, not native physics parity.\n";
 unsigned cameraCases=0;cameraFixture=true;
 for(int directionAxis=0;directionAxis<3;++directionAxis)for(float directionSign:{-1.f,1.f})
 for(float distance:{2.f,7.5f,22.f})for(float offsetScale:{0.f,2.f}){
  constexpr uint32_t editor=0x70000+6892,description=0x80000,out=0x81000,forward=0x81100;
  std::memset(base+editor,0,336);std::memset(base+description,0,32);
  REX_STORE_U32(editor,2);REX_STORE_U32(description+4,3);REX_STORE_U32(description+16,0);
  REX_STORE_U32(0x8405d340,0x90000);REX_STORE_U32(0x90000+256,0x91000);
  put(base,0x4b000+32,2);put(base,editor+28,distance);put(base,editor+36,offsetScale);
  const float offset[3]={.5f,-.25f,1.f};float facing[3]={},right[3]={},up[3]={};
  facing[directionAxis]=directionSign;
  right[0]=facing[1];right[1]=-facing[0];if(directionAxis==2)right[0]=1;
  up[0]=right[1]*facing[2]-right[2]*facing[1];up[1]=right[2]*facing[0]-right[0]*facing[2];up[2]=right[0]*facing[1]-right[1]*facing[0];
  for(unsigned i=0;i<3;++i){cameraHeldPosition[i]=float(10*(i+1));put(base,editor+56+i*4,offset[i]);put(base,0x47000+1212+i*4,facing[i]);}
  for(bool backoff:{false,true}){
   PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
   ctx.r3.u32=description;ctx.r4.u32=out;ctx.r5.u32=forward;ctx.r6.u32=0;ctx.lr=1238;
   if(backoff)h4_forge_original::sub_824BEA10(ctx,base);else h4_forge_original::sub_824BEAD0(ctx,base);
   for(unsigned i=0;i<3;++i){
    const float expected=cameraHeldPosition[i]+offsetScale*offset[i]+.5f*up[i]-(backoff?distance*facing[i]:0.f);
    if(std::abs(get(base,out+i*4)-expected)>1e-4f||(backoff&&get(base,forward+i*4)!=facing[i]))throw std::runtime_error("original camera point/backoff");
   }
   if(ctx.lr!=1238||ctx.r1.u32!=0x180000||(backoff&&ctx.f1.f64!=distance))throw std::runtime_error("camera frame/distance return");
   ++cameraCases;
  }
 }
 std::cout<<"PASS "<<cameraCases<<" original camera point/backoff cases; held offsets, six directions and grab distances2/7.5/22. Curve result and held-position query controlled; optional correction path excluded.\n";
 unsigned correctionCases=0;
 for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f})
 for(float retained:{2.f,7.5f})for(float excess:{-1.f,0.f,.5f,1.f,1.25f,3.f}){
  constexpr uint32_t editor=0x70000+6892,context=0x80000,out=0x81000;
  REX_STORE_U32(context,0);REX_STORE_U32(context+4,editor);
  put(base,editor+36,0);put(base,editor+32,retained);put(base,0x4b000+32,0);
  for(unsigned i=0;i<3;++i){
   put(base,0x47000+1212+i*4,i==0?1.f:0.f);
   put(base,0x47000+100+i*4,cameraHeldPosition[i]+(int(i)==axis?sign*(retained+excess):0.f));
   put(base,out+i*4,99.f);
  }
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
  ctx.r3.u32=context;ctx.r4.u32=out;ctx.lr=1239;
  h4_forge_original::sub_8244B338(ctx,base);
  for(unsigned i=0;i<3;++i){float expected=int(i)==axis&&excess>1.f?sign*excess:0.f;
   if(std::abs(get(base,out+i*4)-expected)>1e-4f)throw std::runtime_error("original camera/monitor correction threshold");}
  if(ctx.lr!=1239||ctx.r1.u32!=0x180000)throw std::runtime_error("camera correction frame");
  ++correctionCases;
 }
 std::cout<<"PASS "<<correctionCases<<" original camera-to-monitor correction cases, including strict one-unit threshold and output reset. Curve/scene inputs controlled.\n";

 unsigned velocityCases=0;
 for(int mode=0;mode<3;++mode)for(bool fixed:{false,true})for(int outputs=0;outputs<4;++outputs)for(bool parent:{false,true}){
  constexpr uint32_t object=0x45000,parentObject=0x47000,linear=0x81000,angular=0x81100;
  uint32_t resolved=parent?parentObject:object;
  REX_STORE_U32(object+36,parent?3:0xffffffff);REX_STORE_U32(parentObject+36,0xffffffff);
  REX_STORE_U64(object+256,0);REX_STORE_U64(parentObject+256,0);
  REX_STORE_U64(resolved+256,mode==2?0x400:0);
  REX_STORE_U32(0x11000+784,mode==1?1:0);
  REX_STORE_U32(resolved+240,0);REX_STORE_U8(0x40000+24,0);REX_STORE_U32(0x40000+52,1);
  REX_STORE_U32(0x40000+48,0x41000);REX_STORE_U32(0x41000+52,body);REX_STORE_U8(body+232,fixed?5:1);
  for(unsigned i=0;i<3;++i){put(base,resolved+136+i*4,float(i+1));put(base,resolved+148+i*4,-float(i+1));
   put(base,body+432+i*4,float(10+i));put(base,body+448+i*4,-float(10+i));put(base,linear+i*4,99);put(base,angular+i*4,99);}
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1240;
  ctx.r3.u32=2;ctx.r4.u32=outputs&1?linear:0;ctx.r5.u32=outputs&2?angular:0;ctx.f1.f64=.125;
  h4_forge_original::sub_82260CF0(ctx,base);
  for(unsigned i=0;i<3;++i){float expected=mode==2||(mode==1&&fixed)?0.f:float((mode==1?10:1)+i);
   if(get(base,linear+i*4)!=(outputs&1?expected:99.f)||get(base,angular+i*4)!=(outputs&2?-expected:99.f))throw std::runtime_error("original velocity source selection");}
  if(ctx.r1.u32!=0x180000||ctx.lr!=1240||ctx.f1.f64!=.125)throw std::runtime_error("velocity query frame/f1 preservation");
  ++velocityCases;
 }
 std::cout<<"PASS "<<velocityCases<<" original velocity-query cases: fallback, physics, forced zero, fixed body, nullable outputs and parent traversal. Physics eligibility gate controlled; f1 preserved.\n";

 unsigned predictionCases=0;
 for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f})for(float speed:{0.f,.004f,.008f,.016f,2.f})
 for(float dt:{.125f,.5f})for(float gap:{0.f,.0005f,.05f,2.f})for(int wrapper=0;wrapper<3;++wrapper){
  constexpr uint32_t editor=0x70000+6892,description=0x80000,point=0x81000,out=0x81100,forward=0x81200,object=0x45000;
  std::memset(base+editor,0,336);std::memset(base+description,0,32);
  REX_STORE_U32(editor,2);REX_STORE_U32(description+4,3);REX_STORE_U32(description+16,0);
  REX_STORE_U32(object+36,0xffffffff);REX_STORE_U32(object+240,0xffffffff);REX_STORE_U64(object+256,0);
  REX_STORE_U32(0x11000+784,0);REX_STORE_U32(0x11000+88,0x49000);put(base,0x49000+8,dt);
  put(base,editor+28,7.5f);put(base,0x4b000+32,0);
  for(unsigned i=0;i<3;++i){
   cameraHeldPosition[i]=float(10*(i+1));put(base,point+i*4,cameraHeldPosition[i]);put(base,out+i*4,99);
   put(base,object+100+i*4,0);put(base,object+136+i*4,int(i)==axis?sign*speed:0);put(base,object+148+i*4,0);
   put(base,editor+8+i*4,int(i)==axis?gap:0);put(base,0x47000+1212+i*4,i==0?1.f:0.f);
  }
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1241;
  ctx.r3.u32=description;ctx.r4.u32=wrapper?out:point;ctx.r5.u32=forward;ctx.r6.u32=wrapper?1:out;ctx.f1.f64=dt;
  if(wrapper==0)h4_forge_original::sub_824BEB50(ctx,base);
  else if(wrapper==1)h4_forge_original::sub_824BEAD0(ctx,base);
  else h4_forge_original::sub_824BEA10(ctx,base);
  float predicted=speed*dt;float distance=wrapper!=1&&predicted>.001f?std::min(predicted,gap):0.f;
  for(unsigned i=0;i<3;++i){float expected=cameraHeldPosition[i]+(int(i)==axis?sign*distance:0)-(wrapper==2&&i==0?7.5f:0);
   if(std::abs(get(base,out+i*4)-expected)>1e-5f){std::cerr<<"prediction axis="<<axis<<" speed="<<speed<<" dt="<<dt<<" gap="<<gap<<" wrapper="<<wrapper<<" actual="<<get(base,out+i*4)<<" expected="<<expected<<"\n";throw std::runtime_error("original linear camera prediction");}}
  if(ctx.r1.u32!=0x180000||ctx.lr!=1241)throw std::runtime_error("prediction frame");++predictionCases;
 }
 std::cout<<"PASS "<<predictionCases<<" original linear camera-prediction cases, direct, mode1 backoff and forced-mode0 point wrapper: signed axes, threshold, retained-position cap, time intervals and backoff. No physics instance; angular prediction excluded.\n";

 unsigned angularPredictionCases=0;
 for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f})for(float rate:{0.f,.6f,3.14159265f})
 for(float dt:{.125f,.5f})for(bool yaw:{false,true})for(bool linearMotion:{false,true})for(bool wrapper:{false,true}){
  constexpr uint32_t editor=0x70000+6892,description=0x80000,point=0x81000,out=0x81100,forward=0x81200,object=0x45000;
  std::memset(base+editor,0,336);std::memset(base+description,0,32);
  REX_STORE_U32(editor,2);REX_STORE_U32(description+4,3);REX_STORE_U32(description+16,0);
  REX_STORE_U32(object+36,0xffffffff);REX_STORE_U32(object+240,0);REX_STORE_U32(object+304,0xffffffff);REX_STORE_U64(object+256,0);
  REX_STORE_U32(0x40000+16,0);REX_STORE_U32(0x40000+52,1);REX_STORE_U32(0x40000+48,0x41000);REX_STORE_U32(0x41000+52,body);
  REX_STORE_U32(0x11000+784,0);REX_STORE_U32(0x11000+88,0x49000);put(base,0x49000+8,dt);
  put(base,editor+28,7.5f);put(base,editor+8,2);put(base,0x4b000+32,0);
  const float fwd[3]={yaw?0.f:1.f,yaw?1.f:0.f,0};
  for(unsigned i=0;i<3;++i){cameraHeldPosition[i]=float(10*(i+1));put(base,point+i*4,cameraHeldPosition[i]);
   put(base,object+100+i*4,0);put(base,object+136+i*4,linearMotion&&i==0?.4f:0);put(base,object+148+i*4,int(i)==axis?sign*rate:0);
   put(base,object+112+i*4,fwd[i]);put(base,object+124+i*4,i==2?1.f:0);put(base,body+368+i*4,float(i+1));
   put(base,0x47000+1212+i*4,i==0?1.f:0.f);}
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1242;
  ctx.r3.u32=description;ctx.r4.u32=wrapper?out:point;ctx.r5.u32=forward;ctx.r6.u32=wrapper?1:out;ctx.f1.f64=dt;
  if(wrapper)h4_forge_original::sub_824BEA10(ctx,base);else h4_forge_original::sub_824BEB50(ctx,base);
  const float p[3]={yaw?-2.f:1.f,yaw?1.f:2.f,3.f};float unit[3]={};unit[axis]=sign;
  float cross[3]={unit[1]*p[2]-unit[2]*p[1],unit[2]*p[0]-unit[0]*p[2],unit[0]*p[1]-unit[1]*p[0]};
  float angle=rate*dt,co=std::cos(angle),si=std::sin(angle),dot=unit[axis]*p[axis];
  for(unsigned i=0;i<3;++i){float rotated=p[i]*co+cross[i]*si+unit[i]*dot*(1-co);
   float expected=cameraHeldPosition[i]+rotated-p[i]+(linearMotion&&i==0?.4f*dt:0)-(wrapper&&i==0?7.5f:0);
   if(std::abs(get(base,out+i*4)-expected)>2e-5f){std::cerr<<"angular prediction axis="<<axis<<" sign="<<sign<<" rate="<<rate<<" yaw="<<yaw<<" actual="<<get(base,out+i*4)<<" expected="<<expected<<"\n";throw std::runtime_error("original angular prediction");}}
  if(ctx.r1.u32!=0x180000||ctx.lr!=1242)throw std::runtime_error("angular prediction frame");++angularPredictionCases;
 }
 std::cout<<"PASS "<<angularPredictionCases<<" original angular camera-prediction cases: signed axes, zero/nonzero rates, two orientations, time intervals, combined linear correction and mode1 backoff. Synthetic world data; alternate orientation/physics-point branch excluded.\n";

 unsigned monitorCases=0;
 for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f})for(float distance:{0.f,.5f,2.f,3.f,10.f})for(int contact=0;contact<3;++contact)for(bool worldHit:{false,true}){
  monitorWorldHit=worldHit;
  reset();constexpr uint32_t editor=0x70000+6892,context=0x80000,held=0x45000,monitor=0x47000;
  std::memset(base+editor,0,336);REX_STORE_U32(context,0);REX_STORE_U32(context+4,editor);REX_STORE_U32(editor,2);
  REX_STORE_U32(held+36,0xffffffff);REX_STORE_U32(held+240,0xffffffff);REX_STORE_U64(held+256,0);
  REX_STORE_U32(monitor+36,0xffffffff);REX_STORE_U32(monitor-12,3);REX_STORE_U32(monitor+240,0);
  REX_STORE_U64(monitor+256,contact?0x100000:0);REX_STORE_U8(0x13000+3*16+4,1);
  REX_STORE_U32(0x40000+20,3);REX_STORE_U32(0x40000+52,1);REX_STORE_U8(0x40000+24,0);
  REX_STORE_U32(0x40000+48,0x41000);REX_STORE_U32(0x41000+52,body);
  REX_STORE_U32(0x11000+160,0x92000);REX_STORE_U32(0x92000+116,0xffffffff);
  REX_STORE_U32(0x11000+784,0);put(base,0x49000+8,.05f);put(base,editor+28,7.5f);put(base,0x4b000+32,0);
  for(unsigned i=0;i<3;++i){cameraHeldPosition[i]=(i==0?7.5f:0)+(int(i)==axis?sign*distance:0);
   put(base,held+136+i*4,0);put(base,held+148+i*4,0);put(base,monitor+100+i*4,0);put(base,monitor+1212+i*4,i==0?1.f:0);
   put(base,0x48000+152+i*4,int(i)==axis?(contact==1?-sign:sign):0);}
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1243;ctx.r3.u32=context;
  h4_forge_original::sub_8244AF48(ctx,base);
  float move=contact==1?0:sign*std::min(distance,2.f),separationSq=0;
  if(cameraRayCalls!=(worldHit?7u:0u))throw std::runtime_error("camera seven-ray query count");
  float fraction=worldHit?.5f*.05f*.05f*.25f*get(base,0x821289e0+168):0;
  for(unsigned i=0;i<3;++i){float desired=int(i)==axis?move:0;float expectedVelocity=desired/.05f;float limit=get(base,0x82128a34)*.05f;
   if(std::abs(get(base,body+432+i*4)-std::clamp(expectedVelocity,-limit,limit))>1e-4f)throw std::runtime_error("monitor displacement/contact controller");
   float difference=cameraHeldPosition[i]-(i==0?7.5f*fraction:0)-desired;separationSq+=difference*difference;}
  if(std::abs(get(base,editor+228)-fraction)>1e-6f||
     (worldHit&&(REX_LOAD_U32(editor+256)!=2||REX_LOAD_U32(editor+260)!=3||REX_LOAD_U8(editor+252)!=1||std::abs(get(base,editor+232)-.3125f)>1e-6f)))
   throw std::runtime_error("monitor smoothing state/held-unit identity");
  float retained=std::min(std::sqrt(separationSq),7.5f*(1-fraction));
  if(std::abs(get(base,editor+32)-retained)>1e-4f||REX_LOAD_U8(editor+80)!=unsigned(worldHit)||ctx.r1.u32!=0x180000||ctx.lr!=1243)
   throw std::runtime_error("monitor retained distance/frame");
  ++monitorCases;
 }
 std::cout<<"PASS "<<monitorCases<<" original coupled monitor updates through camera and physics submission: displacement cap, inward/outward normal handling and retained distance. World hit/miss and original distance smoothing; geometry query controlled, local-view sink excluded, synthetic stationary body.\n";

 unsigned cacheTicks=0;
 for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f})for(int ray=0;ray<7;++ray){
  constexpr uint32_t config=0x94000,state=0x94100,start=0x94200,end=0x94300,out=0x94400,upper=0x94404;
  std::memset(base+config,0,32);std::memset(base+state,0,40);REX_STORE_U32(state+28,2);REX_STORE_U32(state+32,3);
  selectedCameraRay=ray;
  for(unsigned tick=0;tick<7;++tick){
   float from=tick==2?.5f:tick==3?3.f:0.f;
   float length=tick==5?1.f:tick==6?0.f:10.f;
   worldFraction=tick==0?.25f:tick==4?.6f:1.f;cameraRayCalls=0;
   for(unsigned i=0;i<3;++i){put(base,start+i*4,int(i)==axis?sign*from:0);put(base,end+i*4,int(i)==axis?sign*(from+length):0);}
   put(base,out,99);put(base,upper,98);
   PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1244;
   ctx.r3.u32=0x845548b8;ctx.r4.u32=config;ctx.r5.u32=state;ctx.r6.u32=start;ctx.r7.u32=end;ctx.r8.u32=out;ctx.r9.u32=upper;
   h4_forge_original::sub_824F5F78(ctx,base);
   const float expected[]={.25f,.25f,.2f,1.f,.6f,1.f,99.f};
   bool valid=tick<3||tick==4;
   float expectedUpper=tick==6?98.f:ray==0?worldFraction:1.f;
   if(cameraRayCalls!=(tick==6?0u:7u)||std::abs(get(base,out)-expected[tick])>1e-5f||get(base,upper)!=expectedUpper||bool(REX_LOAD_U8(state+24))!=valid)
    {std::cerr<<"cache tick="<<tick<<" ray="<<ray<<" actual="<<get(base,out)<<" valid="<<unsigned(REX_LOAD_U8(state+24))<<"\n";throw std::runtime_error("original obstruction cache lifecycle");}
   if(valid){float position=tick==4?6.f:2.5f;for(unsigned i=0;i<3;++i)if(std::abs(get(base,state+12+i*4)-(int(i)==axis?sign*position:0.f))>1e-5f)throw std::runtime_error("cached world point changed");}
   if(ctx.r1.u32!=0x180000||ctx.lr!=1244)throw std::runtime_error("obstruction query frame");++cacheTicks;
  }
 }
 selectedCameraRay=-1;
 std::cout<<"PASS "<<cacheTicks<<" original obstruction-cache ticks: each ray selected, retained world point, shifted origin, invalidation, reacquisition and degenerate segment. Zero-width cone and controlled ray intersections.\n";

 unsigned coneTicks=0;
 for(int axis=0;axis<3;++axis)for(float sign:{-1.f,1.f})for(float originScale:{0.f,.25f,1.f})for(float angle:{.1f,.3f})for(int ray=0;ray<7;++ray){
  constexpr uint32_t config=0x94000,state=0x94100,start=0x94200,end=0x94300,out=0x94400,upper=0x94404;
  std::memset(base+config,0,32);std::memset(base+state,0,40);
  put(base,config,originScale);put(base,config+4,angle);REX_STORE_U32(state+28,2);REX_STORE_U32(state+32,3);
  selectedCameraRay=ray;std::array<float,3> cached{};
  for(unsigned tick=0;tick<3;++tick){
   worldFraction=tick==0?.25f:1.f;cameraRayCalls=0;
   for(unsigned i=0;i<3;++i){float side=tick==2&&int(i)==(axis+1)%3?20.f:0.f;put(base,start+i*4,side);put(base,end+i*4,side+(int(i)==axis?sign*10.f:0.f));}
   PPCContext c{};c.fpscr.loadFromHost();c.r1.u32=0x180000;c.r13.u32=0x10000;c.lr=1252;
   c.r3.u32=0x845548b8;c.r4.u32=config;c.r5.u32=state;c.r6.u32=start;c.r7.u32=end;c.r8.u32=out;c.r9.u32=upper;
   h4_forge_original::sub_824F5F78(c,base);
   if(cameraRayCalls!=7||c.r1.u32!=0x180000||c.lr!=1252)throw std::runtime_error("cone query frame/count");
   const float radius=10.f*std::sin(angle);
   for(unsigned k=0;k<7;++k){
    float startSq=0,endSq=0;
    for(unsigned i=0;i<3;++i){float a=cameraSegments[k][i]-get(base,start+i*4),b=cameraSegments[k][3+i]-get(base,end+i*4);startSq+=a*a;endSq+=b*b;
     if(int(i)==axis&&(std::abs(a)>1e-5f||std::abs(b)>1e-5f))throw std::runtime_error("cone offset not perpendicular");
     if(std::abs(a-originScale*b)>1e-5f)throw std::runtime_error("cone origin scaling");}
    float expected=k?radius:0.f;
    if(std::abs(std::sqrt(endSq)-expected)>1e-4f||std::abs(std::sqrt(startSq)-originScale*expected)>1e-4f)throw std::runtime_error("cone spread geometry");
   }
   if(tick==0)for(unsigned i=0;i<3;++i)cached[i]=cameraSegments[ray][i]+.25f*(cameraSegments[ray][3+i]-cameraSegments[ray][i]);
   if(std::abs(get(base,out)-(tick<2?.25f:1.f))>1e-5f||get(base,upper)!=(tick==0&&ray==0?.25f:1.f)||bool(REX_LOAD_U8(state+24))!=(tick<2))throw std::runtime_error("cone retained point/invalidation");
   if(tick<2)for(unsigned i=0;i<3;++i)if(std::abs(get(base,state+12+i*4)-cached[i])>1e-5f)throw std::runtime_error("cone cached world point");
   ++coneTicks;
  }
 }
 selectedCameraRay=-1;
 std::cout<<"PASS "<<coneTicks<<" original nonzero-cone steps: six signed axes, three origin scales, two angles, all seven hits, retention and lateral invalidation. Ray endpoints checked against independent sine/perpendicular geometry; intersections controlled.\n";

 unsigned h3FilterCases=0;
 for(unsigned type=0;type<14;++type)for(bool categoryEnabled:{false,true})for(unsigned exclusion=0;exclusion<7;++exclusion)for(bool hidden:{false,true}){
  constexpr uint32_t object=0xa0000,parent=0xa1000,headers=0xa2000,data=0xa3000;
  std::memset(base+object,0,0x4000);REX_STORE_U32(0x11000+168,headers);REX_STORE_U32(headers+68,data);
  REX_STORE_U32(data+2*16+12,object);REX_STORE_U32(data+3*16+12,parent);
  REX_STORE_U8(data+2*16+2,hidden?16:0);REX_STORE_U8(data+2*16+3,type);
  REX_STORE_U32(object+16,3);REX_STORE_U32(parent+16,0xffffffff);REX_STORE_U16(object+582,0xffff);
  PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1245;
  ctx.r3.u32=2;ctx.r4.u32=data+2*16;ctx.r5.u32=object;ctx.r6.u64=categoryEnabled?(1ULL<<(type+1)):0;
  ctx.r7.u32=ctx.r8.u32=ctx.r9.u32=0xffffffff;
  if(exclusion){uint32_t ignored=exclusion<=3?2:3;unsigned slot=(exclusion-1)%3;
   if(slot==0)ctx.r7.u32=ignored;else if(slot==1)ctx.r8.u32=ignored;else ctx.r9.u32=ignored;}
  h3_collision::sub_820AF170(ctx,base);
  bool expected=categoryEnabled&&!hidden&&exclusion==0;
  if(bool(ctx.r3.u32)!=expected||ctx.r1.u32!=0x180000||ctx.lr!=1245)throw std::runtime_error("H3 original collision exclusion/category filter");
  ++h3FilterCases;
 }
 std::cout<<"PASS "<<h3FilterCases<<" original H3 collision filter cases:14 categories, category bit gating, hidden header, all three direct/ancestor exclusions. Seat exception excluded.\n";

 unsigned h4FilterCases=0;
 for(unsigned count=0;count<4;++count)for(unsigned match=0;match<3;++match)for(unsigned exception=0;exception<4;++exception)for(bool objectEnabled:{false,true}){
  constexpr uint32_t context=0xb0000,upstream=0xb1000,vtable=0xb2000,shape=0xb3000,request=0xb4000,out=0xb5000;
  std::memset(base+context,0,0x6000);REX_STORE_U32(context+236,upstream);REX_STORE_U32(upstream+20,vtable);REX_STORE_U32(vtable+4,0x108);
  REX_STORE_U32(context+240,request);REX_STORE_U32(request+4,0x1009);REX_STORE_U32(request+8,objectEnabled?1:0);REX_STORE_U8(request+292,count);
  for(unsigned i=0;i<count;++i)REX_STORE_U32(request+36+i*4,match==0?99:match==1?2:3);
  REX_STORE_U8(shape+24,2);REX_STORE_U8(shape+16,32);
  REX_STORE_U32(0x13000+2*16+12,0xa0000);REX_STORE_U32(0x13000+3*16+12,0xa1000);REX_STORE_U32(0x13000+4*16+12,0xa4000);
  for(unsigned id:{2u,3u}){uint32_t obj=id==2?0xa0000:0xa1000;REX_STORE_U8(0x13000+id*16+4,exception?1:0);REX_STORE_U32(obj+8,0);REX_STORE_U32(obj+32,exception>=2?4:0xffffffff);}
  REX_STORE_U8(0x13000+4*16+4,1);REX_STORE_U32(0xa4000+36,match==2?3:2);REX_STORE_U16(0xa4000+44,0);REX_STORE_U32(0xa4000+28,0xffffffff);
  REX_STORE_U32(0x4b000+1368,0xc0000);REX_STORE_U16(0xc0000+74,exception==3?0:0xffff);REX_STORE_U32(0x4b000+520,0);
  REX_STORE_U32(0xa0000+36,3);REX_STORE_U32(0xa1000+36,0xffffffff);
  PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1246;ctx.r3.u32=out;ctx.r4.u32=context;ctx.r6.u32=shape;
  h4_forge_original::sub_82416640(ctx,base);
  if(bool(REX_LOAD_U8(out))!=(objectEnabled&&(count==0||match==0||exception==3))||ctx.r1.u32!=0x180000||ctx.lr!=1246)throw std::runtime_error("H4 original ancestor exclusion filter");++h4FilterCases;
 }
 std::cout<<"PASS "<<h4FilterCases<<" original H4 collision exclusion cases: zero/one/two/three exclusions, unrelated/direct/ancestor identity. Initialized camera mask versus object-enabled mask; original type/tag/child-seat predicates. Metadata/upstream controlled; category3 exception excluded.\n";

 unsigned cameraMaskCases=0;
 for(unsigned shapeType:{0u,1u,2u,5u}){
  constexpr uint32_t context=0xb0000,shape=0xb3000,request=0xb4000,out=0xb5000;
  REX_STORE_U64(request+4,REX_LOAD_U64(0x845548b8));REX_STORE_U8(shape+24,shapeType);
  PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1247;ctx.r3.u32=out;ctx.r4.u32=context;ctx.r6.u32=shape;
  h4_forge_original::sub_82416640(ctx,base);
  if(bool(REX_LOAD_U8(out))!=(shapeType!=2)||ctx.lr!=1247||ctx.r1.u32!=0x180000)throw std::runtime_error("initialized camera mask shape gate");++cameraMaskCases;
 }
 std::cout<<"PASS "<<cameraMaskCases<<" initialized H4 camera-mask shape gates; type2 object branch rejected before exclusion lookup, other tested shape types accepted by this callback with upstream approval.\n";

 unsigned collectorCases=0;
 for(unsigned shapeType:{0u,2u,5u})for(unsigned depth:{0u,1u,3u}){
  constexpr uint32_t context=0xb0000,shape=0xb3000,hit=0xb5000;
  std::memset(base+context,0,0x6000);put(base,context+4,1.f);
  for(unsigned i=0;i<=depth;++i){uint32_t node=shape+i*0x100;REX_STORE_U32(node+12,i<depth?node+0x100:0);REX_STORE_U32(node+4,100+i);}
  REX_STORE_U8(shape+depth*0x100+24,shapeType);REX_STORE_U8(shape+depth*0x100+16,32);
  float nearest=1.f;unsigned count=0;
  for(float fraction:{.7f,.8f,.4f,.4f,.9f,.1f}){
   for(unsigned i=0;i<4;++i)put(base,hit+i*4,float(collectorCases+i));put(base,hit+16,fraction);
   REX_STORE_U32(hit+20,41);REX_STORE_U32(hit+24,42);REX_STORE_U32(hit+28,43);
   PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1248;
   ctx.r3.u32=context;ctx.r4.u32=shape;ctx.r5.u32=hit;
   bool replace=shapeType!=2&&fraction<nearest;
   uint32_t oldFirst=REX_LOAD_U32(context+16);
   h4_forge_original::sub_822528D8(ctx,base);
   if(shapeType==2){
    if(REX_LOAD_U32(context+384+count*8)!=2||get(base,context+388+count*8)!=fraction)throw std::runtime_error("collector object candidate");++count;
   }else if(replace){
    nearest=fraction;
    for(unsigned i=0;i<4;++i)if(REX_LOAD_U32(context+16+i*4)!=REX_LOAD_U32(hit+i*4))throw std::runtime_error("collector hit vector");
    if(get(base,context+32)!=fraction||REX_LOAD_U32(context+96)!=shape+depth*0x100)throw std::runtime_error("collector geometry root");
    for(unsigned i=0;i<depth;++i)if(REX_LOAD_U32(context+48+i*4)!=100+depth-1-i)throw std::runtime_error("collector parent path order");
    if(REX_LOAD_U32(context+48+depth*4)!=0xffffffff)throw std::runtime_error("collector path terminator");
   }else if(REX_LOAD_U32(context+16)!=oldFirst)throw std::runtime_error("collector replaced equal/far hit");
   if(get(base,context+4)!=nearest||REX_LOAD_U32(context+2432)!=count||ctx.r1.u32!=0x180000||ctx.lr!=1248)throw std::runtime_error("collector state/frame");++collectorCases;
  }
 }

 for(unsigned initialCount:{0u,255u,256u,257u}){
  constexpr uint32_t context=0xb0000,shape=0xb3000,hit=0xb5000;
  std::memset(base+context,0,0x6000);put(base,context+4,1.f);REX_STORE_U8(shape+24,2);REX_STORE_U8(shape+16,32);
  REX_STORE_U32(context+2432,initialCount);put(base,hit+16,.3f);
  PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.lr=1249;ctx.r3.u32=context;ctx.r4.u32=shape;ctx.r5.u32=hit;
  h4_forge_original::sub_822528D8(ctx,base);
  if(REX_LOAD_U32(context+2432)!=initialCount+(initialCount<256)||get(base,context+4)!=1.f||ctx.lr!=1249||ctx.r1.u32!=0x180000)throw std::runtime_error("collector capacity");
  if(initialCount<256&&(REX_LOAD_U32(context+384+initialCount*8)!=2||get(base,context+388+initialCount*8)!=.3f))throw std::runtime_error("collector capacity append");
  ++collectorCases;
 }
 std::cout<<"PASS "<<collectorCases<<" original hit collector steps: separate object candidates, strict nearest geometry, equal-hit retention, parent path ordering and 256-candidate cap. Synthetic shape hierarchy/metadata; no world traversal.\n";
 unsigned ownershipCases=0;
 constexpr uint32_t owner=0xc0000,players=0xd0000,h4players=0xe0000,h3players=0xf1000;
 REX_STORE_U32(0x11000+140,owner);REX_STORE_U32(0x11000+124,owner+256);
 REX_STORE_U32(0x11000+24,players);REX_STORE_U32(0x11000+96,players+256);
 REX_STORE_U32(players+68,h4players);REX_STORE_U32(players+256+68,h3players);
 for(unsigned player=0;player<16;++player)for(bool enabled:{false,true})for(int mismatch=-1;mismatch<6;++mismatch){
  REX_STORE_U8(owner+104,enabled);REX_STORE_U8(owner+256+108,enabled);
  for(unsigned i=0;i<6;++i){
   const uint8_t identity=uint8_t(17+player*11+i*29);
   REX_STORE_U8(owner+105+i,identity);REX_STORE_U8(owner+256+109+i,identity);
   const uint8_t remote=identity^(int(i)==mismatch?128:0);
   REX_STORE_U8(h4players+player*4144+20+i,remote);REX_STORE_U8(h3players+player*880+20+i,remote);
  }
  PPCContext a{},b{};a.r1.u32=b.r1.u32=0x180000;a.r13.u32=b.r13.u32=0x10000;
  a.lr=b.lr=1253;a.r3.u32=b.r3.u32=0x12340000|player;
  h4_ownership::sub_822ED938(a,base);h3_ownership::sub_821F0688(b,base);
  bool expected=enabled&&mismatch==-1;
  if(bool(a.r3.u32)!=expected||bool(b.r3.u32)!=expected||a.r1.u32!=0x180000||b.r1.u32!=0x180000||a.lr!=1253||b.lr!=1253)
   throw std::runtime_error("H3/H4 ownership predicate correspondence");
  ++ownershipCases;
 }
 ownershipPlayerValid=false;REX_STORE_U8(owner+104,1);
 PPCContext missing{};missing.r1.u32=0x180000;missing.r13.u32=0x10000;missing.lr=1254;missing.r3.u32=0;
 h4_ownership::sub_822ED938(missing,base);
 if(missing.r3.u32||missing.r1.u32!=0x180000||missing.lr!=1254)throw std::runtime_error("missing H4 ownership player");
 std::cout<<"PASS "<<ownershipCases<<" original H3/H4 ownership comparisons:16 slots, disabled/enabled local identity, each of six mismatching bytes, plus H4 missing-player rejection. H4 player lookup controlled; no network session executed.\n";
 // Both engines use different constants at overlapping first-page addresses.
 // Switch that page before each original call; remaining H4 image stays intact.
 std::array<uint8_t,4096> h4Constants{},h3Constants{};
 std::memcpy(h4Constants.data(),base+0x82000000,h4Constants.size());
 std::ifstream h3image("work/advanced-forge/guest-image.bin",std::ios::binary);
 if(!h3image.read(reinterpret_cast<char*>(h3Constants.data()),h3Constants.size()))throw std::runtime_error("H3 controller constants");
 unsigned controllerPairs=0,callbackDifferences=0;
 for(unsigned initialState=0;initialState<3;++initialState)for(unsigned axis=0;axis<3;++axis)for(float speed:{-2.f,0.f,2.f})for(float angle:{-.4f,0.f,.4f})for(float dt:{.05f,.2f})for(float error:{0.f,.1f,10.f}){
  reset();std::memset(base+h3_collision::h3body,0,0x2000);
  h3_collision::linear=h3_collision::angular=h3_collision::wakes=h3_collision::relocated=0;
  REX_STORE_U32(h3_collision::h3body+160,h3_collision::h3table);REX_STORE_U32(h3_collision::h3table+60,0x200);REX_STORE_U32(h3_collision::h3table+64,0x204);
  put(base,body+288+axis*4,.2f);put(base,h3_collision::h3body+224+axis*4,.2f);
  put(base,h3_collision::h3body+300,1);
  if(initialState){
   const float initialLinear[3]={.3f,.4f,-.2f},initialAngular[3]={.1f,-.2f,.3f};
   for(unsigned i=0;i<3;++i){
    put(base,body+432+i*4,initialLinear[i]);put(base,h3_collision::h3body+384+i*4,initialLinear[i]);
    put(base,body+448+i*4,initialAngular[i]);put(base,h3_collision::h3body+400+i*4,initialAngular[i]);
   }
   for(unsigned i=0;i<4;++i){float q=(i==3?std::cos(.35f):float(i+1)/std::sqrt(14.f)*std::sin(.35f))*(initialState==2?-1.f:1.f);
    put(base,body+352+i*4,q);put(base,h3_collision::h3body+288+i*4,q);}
  }
  put(base,target+axis*4,.2f+error);put(base,target+16+axis*4,std::sin(angle/2));put(base,target+28,std::cos(angle/2));
  put(base,target+32+axis*4,speed);put(base,target+48+axis*4,speed*.5f);
  PPCContext a{},b{};a.fpscr.loadFromHost();b.fpscr.loadFromHost();a.r1.u32=b.r1.u32=0x180000;a.lr=b.lr=1255;
  a.r3.u32=b.r3.u32=target;a.r4.u32=b.r4.u32=gains;a.r7.u32=body;b.r7.u32=h3_collision::h3body;a.f1.f64=b.f1.f64=dt;
  std::memcpy(base+0x82000000,h4Constants.data(),h4Constants.size());h4_forge_original::sub_82C01FB8(a,base);
  std::memcpy(base+0x82000000,h3Constants.data(),h3Constants.size());h3_collision::sub_82629000(b,base);
  for(unsigned i=0;i<3;++i){
   if(std::abs(get(base,body+432+i*4)-get(base,h3_collision::h3body+384+i*4))>1e-4f||std::abs(get(base,body+448+i*4)-get(base,h3_collision::h3body+400+i*4))>1e-4f||std::abs(get(base,body+288+i*4)-get(base,h3_collision::h3body+224+i*4))>1e-4f)
    {std::cerr<<"pair axis="<<axis<<" speed="<<speed<<" angle="<<angle<<" dt="<<dt<<" error="<<error<<" component="<<i<<" linear="<<get(base,body+432+i*4)<<","<<get(base,h3_collision::h3body+384+i*4)<<" angular="<<get(base,body+448+i*4)<<","<<get(base,h3_collision::h3body+400+i*4)<<" position="<<get(base,body+288+i*4)<<","<<get(base,h3_collision::h3body+224+i*4)<<"\n";throw std::runtime_error("H3/H4 controller numerical divergence");}
  }
  for(unsigned i=0;i<4;++i)if(std::abs(get(base,body+352+i*4)-get(base,h3_collision::h3body+288+i*4))>1e-5f)throw std::runtime_error("controller pair orientation");
  if(relocations!=h3_collision::relocated||a.r1.u32!=0x180000||b.r1.u32!=0x180000||a.lr!=1255||b.lr!=1255)throw std::runtime_error("controller pair relocation/frame");
  if(linearCalls!=h3_collision::linear||angularCalls!=h3_collision::angular||activations!=h3_collision::wakes)++callbackDifferences;
  ++controllerPairs;
 }
 if(!callbackDifferences)throw std::runtime_error("expected controller callback suppression difference absent");
 std::cout<<"PASS "<<controllerPairs<<" paired original H3/H4 controller cases: signed targets, timestep, position error, relocation, nonzero initial velocities and compound orientation with both quaternion signs; "<<callbackDifferences<<" callback-count differences. Synthetic bodies/callbacks; not native collision or sleep parity.\n";
 VirtualFree(base,0,MEM_RELEASE);
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
