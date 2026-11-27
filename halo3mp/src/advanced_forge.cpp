// Spartan Advanced Forge: Halo 3 integration.
//
// The editing behaviour lives in forge/forge_core.cpp, written from the
// clean-room specification tools/h4-forge/ADVANCED-FORGE.md. This file reads
// the Halo 3 world into the core's plain structures, and applies the results
// back through Halo 3's own services (physics bodies, object poses, the map
// variant, menus). It holds no Halo 4 code, data or memory layouts. Saved
// layouts remain ordinary Halo 3 map variants: every editor value here is
// transient and discarded on release.
#include "advanced_forge.h"
#include "pc_video_menu.h"
#include "forge/forge_core.h"
#include "forge/forge_marker_material.h"
#include "forge/forge_native_tick.h"
#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/system/function_dispatcher.h>
#include <rex/logging.h>
#include <rex/ui/imgui_dialog.h>
#include <rex/graphics/command_processor.h>
#include <imgui.h>
#include <algorithm>
#include <cstdio>
#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstring>
#include <functional>
#include <future>
#include <map>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <unordered_map>
#include <vector>

REXCVAR_DEFINE_BOOL(halo3mp_advanced_forge,true,"Halo3MP","Advanced Forge editing on Forge Gulch and Force Cove; false is a diagnostic override");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_trace,"","Halo3MP","Optional private Advanced Forge log tracing (any non-empty value)");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_test_offset,"","Halo3MP","Diagnostic only (requires tracing): on grab, place the piece at dx,dy,dz in the frame of the last dropped piece");

#define AF_IMPORT(name) extern "C" void __imp__##name(PPCContext& __restrict,uint8_t*)
AF_IMPORT(sub_821AA050);AF_IMPORT(sub_822802D0);AF_IMPORT(sub_8232EB28);AF_IMPORT(sub_821CB8D8);
AF_IMPORT(sub_821CBB88);AF_IMPORT(sub_820A9E58);AF_IMPORT(sub_820AA480);AF_IMPORT(sub_820AF448);
AF_IMPORT(sub_820AF170);AF_IMPORT(sub_820AD3E0);AF_IMPORT(sub_820AE5C0);AF_IMPORT(sub_820EA138);
AF_IMPORT(sub_820AF6D0);AF_IMPORT(sub_820AF7B0);AF_IMPORT(sub_820AFA98);AF_IMPORT(sub_820AC960);
AF_IMPORT(sub_820F29C8);AF_IMPORT(sub_820AFCF8);AF_IMPORT(sub_8211DE00);AF_IMPORT(sub_820F2A78);
AF_IMPORT(sub_82651968);AF_IMPORT(sub_8265FD48);AF_IMPORT(sub_822385C8);AF_IMPORT(sub_820FFAB0);
AF_IMPORT(sub_820D8FA0);AF_IMPORT(sub_820B1928);AF_IMPORT(sub_820B04B0);AF_IMPORT(sub_820F6550);
AF_IMPORT(sub_820B06A0);AF_IMPORT(sub_82267DD8);AF_IMPORT(sub_8227EB28);AF_IMPORT(sub_820B0B60);
AF_IMPORT(sub_82284078);AF_IMPORT(sub_8232E8B8);AF_IMPORT(sub_821F04C0);

namespace advanced_forge {
namespace {
using forge::Vec3;
using V=forge::Vec3;
constexpr uint32_t kNone=forge::kNone;

std::atomic<bool> enabled=true;
bool failed=false;
std::atomic<rex::graphics::CommandProcessor*> markerRenderer=nullptr;
std::shared_future<std::shared_ptr<const rex::graphics::SceneMarkerMaterial>> markerMaterial;

bool Ptr(uint32_t a){return a>=0x10000&&a<0xc0000000;}
uint32_t U(uint8_t* b,uint32_t a){uint32_t v;std::memcpy(&v,b+a,4);return std::byteswap(v);}
uint16_t H(uint8_t* b,uint32_t a){uint16_t v;std::memcpy(&v,b+a,2);return std::byteswap(v);}
float F(uint8_t* b,uint32_t a){return std::bit_cast<float>(U(b,a));}
V Vec(uint8_t* b,uint32_t a){return {F(b,a),F(b,a+4),F(b,a+8)};}
void PutU(uint8_t* b,uint32_t a,uint32_t v){v=std::byteswap(v);std::memcpy(b+a,&v,4);}
void PutF(uint8_t* b,uint32_t a,float f){PutU(b,a,std::bit_cast<uint32_t>(f));}
void PutVec(uint8_t* b,uint32_t a,const V& v){for(unsigned i=0;i<3;++i)PutF(b,a+i*4,v[i]);}
bool Tracing(){return !REXCVAR_GET(halo3mp_advanced_forge_trace).empty();}
void CheckFinite(const V& v,const char* what){for(float f:v)if(!std::isfinite(f))throw std::runtime_error(what);}

// Reserve a guest stack frame below the caller's for native out-parameters.
struct Frame {
 PPCContext call;uint32_t at;
 Frame(PPCContext& ctx,uint8_t* base,uint32_t bytes):call(ctx){
  if(ctx.r1.u32<0x5000||ctx.r1.u32>=0xc0000000)throw std::runtime_error("Invalid native stack");
  call.r1.u32-=bytes;PutU(base,call.r1.u32,ctx.r1.u32);at=call.r1.u32+0x60;
 }
};

// ------------------------------------------------------------------ markers to draw
struct VisibleAnchor {V position{};uint32_t datum=kNone;float seed=0,shown=0;};
struct AnchorView {
 uint32_t player=kNone;
 std::vector<VisibleAnchor> anchors;
 std::chrono::steady_clock::time_point updated;
 float time=0;
};
std::mutex anchorMutex;
std::array<AnchorView,4> anchorViews;
struct AnchorViewport {
 uint32_t renderView=0;
 std::array<float,4> rect{0.f,0.f,1.f,1.f};
 std::chrono::steady_clock::time_point updated;
 bool valid=false;
};
std::array<AnchorViewport,4> anchorViewports;
void ClearAnchorWorld(){
 {
  std::lock_guard lock(anchorMutex);
  for(auto& view:anchorViews)view=AnchorView{};
  for(auto& viewport:anchorViewports)viewport=AnchorViewport{};
 }
 if(auto* renderer=markerRenderer.load())renderer->DiscardQueuedSceneMarkers();
}
void ClearPlayerAnchors(uint32_t player){std::lock_guard lock(anchorMutex);for(auto& view:anchorViews)if(view.player==player)view.anchors.clear();}

bool LocalForge(uint8_t* base,uint32_t game){
 // Same mode gates as retail 8227E810: local simulation of the sandbox engine.
 return Ptr(game)&&U(base,game+0x10)==2&&(U(base,game+0x238)&65535)==5&&base[game+0x14]==1;
}
// Halo 3 object flags (object+172).
constexpr uint32_t kFrozen=1u<<6,kConnected=1u<<7,kAtRest=1u<<9,kContact=1u<<19,kForceDynamic=1u<<20;

struct PhysicsObject {
 uint32_t pointer=0,tag=0,original=0;
 forge::PhysicsMode authoredMode=forge::PhysicsMode::Normal;
 std::optional<forge::PhysicsMode> mode;
 bool releasedPhysics=false;   // the last physics transition came from our release
 bool keyframedOverride=false; // keyframed request for Halo 3's body constructor
 uint32_t settlePlayer=kNone;  // releasing player, for the settle validity rule
};
std::unordered_map<uint32_t,PhysicsObject> physicsObjects;
struct ControllerAttachmentState {uint32_t object=0,instance=0;};
std::unordered_map<uint32_t,ControllerAttachmentState> controllerAttachments;
uint32_t physicsEngine=0,physicsHeaders=0,physicsMap=0,physicsTick=0;
bool restoringPhysics=false;
std::vector<uint32_t> settledInvalid;  // deleted after Halo 3's deferred update
uint32_t lastReleased=kNone;          // diagnostic placement reference
thread_local std::optional<uint32_t> completedMonitorExitPlayer;
thread_local std::optional<uint32_t> nativePhasedReleaseDatum;

struct NativeEditorSlot {
 uint32_t player=kNone;
 std::optional<forge::Editor> editor;
 forge::InputState input;
 bool ownsMonitorContact=false;
 uint32_t contactMonitor=kNone;
 std::map<uint32_t,float> shown;  // objects showing magnet markers -> time shown
};
std::array<NativeEditorSlot,16> nativeEditors;
// Raw controller state per controller, as the game last read it (XInputGetState).
std::array<std::optional<forge::RawSticks>,4> rawSticks;
void ClearNativeEditors(){for(auto& slot:nativeEditors)slot=NativeEditorSlot{};}

struct NativeGrabTransaction {uint32_t player,datum;bool selected=false;std::string error;};
thread_local NativeGrabTransaction* nativeGrabTransaction=nullptr;
struct NativeGrabTransactionScope {
 NativeGrabTransaction* prior=nativeGrabTransaction;
 explicit NativeGrabTransactionScope(NativeGrabTransaction* value){nativeGrabTransaction=value;}
 ~NativeGrabTransactionScope(){nativeGrabTransaction=prior;}
};
struct NativeCreatePlacement {uint32_t tag,player;bool hasPoint;std::optional<float> radius;};
thread_local NativeCreatePlacement* nativeCreatePlacement=nullptr;
struct NativeCreatePlacementScope {
 NativeCreatePlacement* prior=nativeCreatePlacement;
 explicit NativeCreatePlacementScope(NativeCreatePlacement* value){nativeCreatePlacement=value;}
 ~NativeCreatePlacementScope(){nativeCreatePlacement=prior;}
};
struct NativeDetachAttachment {
 uint32_t datum,object,parent;
 int node;
 bool deferVelocity=false;
 bool rebuildAfterUnlink=false,physicsReset=false;
 std::optional<std::array<V,2>> fallbackVelocity;
};
thread_local NativeDetachAttachment* nativeDetachAttachment=nullptr;
thread_local const std::vector<uint32_t>* selectionRayExclusions=nullptr;
struct SelectionRayExclusionScope {
 explicit SelectionRayExclusionScope(const std::vector<uint32_t>& exclusions){
  if(selectionRayExclusions||exclusions.size()>65)throw std::runtime_error("Invalid or nested Forge selection exclusions");
  selectionRayExclusions=&exclusions;
 }
 ~SelectionRayExclusionScope(){selectionRayExclusions=nullptr;}
};

// Player contact normal: player lifetime, not per hold.
struct NativePlayerContact {uint32_t player=kNone,pool=0,record=0;V normal{};bool normalKnown=false;};
std::array<NativePlayerContact,16> nativePlayerContacts;
void ClearNativePlayerContacts(){nativePlayerContacts={};ClearNativeEditors();}
NativePlayerContact* PlayerContact(uint8_t* base,uint32_t tls,uint32_t player,bool requireNormal){
 if(!Ptr(tls)||player==kNone||(player&65535)>=nativePlayerContacts.size())return nullptr;
 const auto pool=U(base,tls+96),table=Ptr(pool)?U(base,pool+68):0;
 const uint64_t record=uint64_t(table)+(player&65535)*880ull;
 if(!Ptr(table)||record+880>=0xc0000000ULL||H(base,uint32_t(record))!=(player>>16))return nullptr;
 if(U(base,uint32_t(record)+4)&2)return nullptr;  // departed player
 auto& state=nativePlayerContacts[player&65535];
 if(state.player!=player||state.pool!=pool||state.record!=record){
  if(requireNormal)return nullptr;
  state={player,pool,uint32_t(record),V{},false};
 }
 if(requireNormal&&!state.normalKnown)return nullptr;
 return &state;
}
struct NativeContactObservation {uint32_t player=kNone,tls=0;std::optional<V> normal;};
thread_local NativeContactObservation* nativeContactObservation=nullptr;
std::optional<NativeContactObservation> ObserveNativeContact(PPCContext& ctx,uint8_t* base){
 if(ctx.lr!=0x820F584C)return {};
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))return {};
 const auto pool=U(base,tls+0xa8),headers=Ptr(pool)?U(base,pool+68):0,datum=ctx.r3.u32;
 if(!Ptr(headers)||datum==kNone)return {};
 const uint64_t header=uint64_t(headers)+(datum&65535)*16ull;
 if(header+16>=0xc0000000ULL||H(base,uint32_t(header))!=(datum>>16)||base[header+3]!=0)return {};
 const auto object=U(base,uint32_t(header)+12);
 if(!Ptr(object)||U(base,object+16)!=kNone)return {};
 const auto player=U(base,object+380);
 auto* state=PlayerContact(base,tls,player,false);
 if(!state||ctx.r4.u32!=state->record+64||U(base,state->record+40)!=datum)return {};
 return NativeContactObservation{player,tls,{}};
}
void InitializeNativePlayerContact(PPCContext& ctx,uint8_t* base,uint32_t player){
 if(player==kNone||(player&65535)>=nativePlayerContacts.size())return;
 const auto tls=U(base,ctx.r13.u32),pool=Ptr(tls)?U(base,tls+96):0;
 const auto table=Ptr(pool)?U(base,pool+68):0;
 const uint64_t record=uint64_t(table)+(player&65535)*880ull;
 if(!Ptr(table)||record+880>=0xc0000000ULL||H(base,uint32_t(record))!=(player>>16))
  throw std::runtime_error("Invalid completed native player allocation");
 auto& slot=nativeEditors[player&65535];
 slot=NativeEditorSlot{};slot.player=player;
 nativePlayerContacts[player&65535]={player,pool,uint32_t(record),V{},true};
}

// ------------------------------------------------------------------ Halo 3 object access
uint32_t ObjectPointer(uint8_t* base,uint32_t headers,uint32_t datum){
 if(datum==kNone||!Ptr(headers))return 0;
 const auto header=headers+(datum&65535)*16;
 if(H(base,header)!=datum>>16)return 0;
 const auto object=U(base,header+12);
 return Ptr(object)?object:0;
}
uint8_t ObjectType(uint8_t* base,uint32_t datum){return base[physicsHeaders+(datum&65535)*16+3];}
// Halo 3 scenery (6) and crates (10) use the Advanced Forge lifecycle.
bool SceneryType(uint8_t type){return type==6||type==10;}
uint32_t TagDefinition(uint8_t* base,uint32_t datum){
 if(datum==kNone)return 0;
 const auto table=U(base,0x827f0f8c);
 if(!Ptr(table))return 0;
 const auto definition=U(base,table+(datum&65535)*8+4);
 return Ptr(definition)?definition:0;
}
uint32_t PhysicsModel(uint8_t* base,uint32_t object){
 const auto definition=TagDefinition(base,U(base,object));
 const auto model=definition?TagDefinition(base,U(base,definition+0x40)):0;
 return model?TagDefinition(base,U(base,model+0x3c)):0;
}
std::optional<bool> AuthoredKeyframedBody(uint8_t* base,uint32_t object){
 const auto phmo=PhysicsModel(base,object);
 if(!phmo)return false;
 const auto count=U(base,phmo+0x58),bodies=U(base,phmo+0x5c);
 if(!count)return false;
 if(!Ptr(bodies)||uint64_t(bodies)+uint64_t(count)*176>=0xc0000000ULL)return {};
 for(uint32_t i=0;i<count;++i)if(H(base,bodies+i*176+0x1a)==4)return true;
 return false;
}
forge::PhysicsMode AuthoredPhysics(uint8_t* base,uint32_t object){
 if(U(base,object+0xac)&kFrozen)return forge::PhysicsMode::Fixed;
 const auto phmo=PhysicsModel(base,object);
 if(!phmo)return forge::PhysicsMode::Normal;
 const auto count=U(base,phmo+0x58),bodies=U(base,phmo+0x5c);
 if(!count||count>1024||!Ptr(bodies))return forge::PhysicsMode::Normal;
 for(uint32_t i=0;i<count;++i)if(H(base,bodies+i*176+0x1a)!=5)return forge::PhysicsMode::Normal;
 return forge::PhysicsMode::Fixed;
}
void ResetWorldState(){
 physicsObjects.clear();controllerAttachments.clear();settledInvalid.clear();
 ClearNativeEditors();ClearAnchorWorld();
}
// Local Forge on a map the user enabled (Forge Gulch, Force Cove).
bool PhysicsWorld(PPCContext& ctx,uint8_t* base){
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))return false;
 const auto engine=U(base,tls+0x64),array=U(base,tls+0xa8),time=U(base,tls+0xbc);
 if(!Ptr(engine)||!Ptr(array)||!Ptr(time))return false;
 const auto headers=U(base,array+0x44),map=U(base,engine+0x178),tick=U(base,time+0xc);
 if(!Ptr(headers)||!forge::AdvancedForgeMap(map))return false;
 if(engine!=physicsEngine||headers!=physicsHeaders||map!=physicsMap||tick<physicsTick)ResetWorldState();
 physicsEngine=engine;physicsHeaders=headers;physicsMap=map;physicsTick=tick;
 return true;
}
bool PhysicsValid(uint8_t* base,uint32_t datum,const PhysicsObject& object){
 return ObjectPointer(base,physicsHeaders,datum)==object.pointer&&U(base,object.pointer)==object.tag;
}
float TickInterval(PPCContext& ctx,uint8_t* base){
 const auto tls=U(base,ctx.r13.u32),time=Ptr(tls)?U(base,tls+188):0;
 if(!Ptr(time))throw std::runtime_error("Missing native simulation time");
 return F(base,time+8);
}

// Early-mover history phases: observed so detach velocity follows the
// association rule (spec 02 5 step 11) with Halo 3's own records.
struct NativeHistoryIdentity {
 uint32_t history,headers,object,engine,map,time,datum;
 bool operator==(const NativeHistoryIdentity&) const =default;
};
struct NativeHistoryPhase {NativeHistoryIdentity identity{};uint32_t tick=0;bool known=false,first=false;};
std::mutex nativeHistoryMutex;
std::array<NativeHistoryPhase,32> nativeHistoryPhases;
thread_local bool* nativeFirstHistorySampled=nullptr;
std::optional<NativeHistoryPhase> NativeHistoryIdentityAt(PPCContext& ctx,uint8_t* base,uint32_t datum,uint32_t index){
 if(index>=nativeHistoryPhases.size()||datum==kNone)return {};
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+128)))return {};
 const auto history=U(base,tls+264),array=U(base,tls+168);
 const auto engine=U(base,tls+100),time=U(base,tls+188);
 if(!Ptr(history)||uint64_t(history)+9860>=0xc0000000ULL||!Ptr(array)||!Ptr(engine)||!Ptr(time))return {};
 const auto count=U(base,history+9856);
 if(count>32||index>=count||U(base,history+9728+index*4)!=datum)return {};
 const auto headers=U(base,array+68),object=ObjectPointer(base,headers,datum);
 if(!object)return {};
 NativeHistoryPhase value;
 value.identity={history,headers,object,engine,U(base,engine+0x178),time,datum};
 value.tick=U(base,time+12);
 return value;
}
void RecordNativeHistoryPhase(PPCContext& ctx,uint8_t* base,uint32_t datum,uint32_t index,bool first,bool sampled){
 if(index>=nativeHistoryPhases.size())return;
 const auto current=NativeHistoryIdentityAt(ctx,base,datum,index);
 std::lock_guard lock(nativeHistoryMutex);
 auto& slot=nativeHistoryPhases[index];
 if(!current){slot={};return;}
 if(!(slot.identity==current->identity)||current->tick<slot.tick)slot=*current;
 if(!first||sampled){slot=*current;slot.known=true;slot.first=first;}
}
std::optional<bool> NativeHistoryFirstBank(PPCContext& ctx,uint8_t* base,uint32_t datum,uint32_t index){
 const auto current=NativeHistoryIdentityAt(ctx,base,datum,index);
 if(!current)return {};
 std::lock_guard lock(nativeHistoryMutex);
 const auto& slot=nativeHistoryPhases[index];
 if(!slot.known||!(slot.identity==current->identity)||current->tick<slot.tick)return {};
 return slot.first;
}

V NativeObjectVector(PPCContext& ctx,uint8_t* base,uint32_t datum,void(*query)(PPCContext&,uint8_t*)){
 if(!ObjectPointer(base,physicsHeaders,datum))throw std::runtime_error("Invalid native object-vector datum");
 Frame f(ctx,base,0x100);
 f.call.r3.u32=datum;f.call.r4.u32=f.at;query(f.call,base);
 auto result=Vec(base,f.at);
 CheckFinite(result,"Nonfinite native object vector");
 return result;
}
// Linear velocity (no angular output requested).
V NativeObjectMotion(PPCContext& ctx,uint8_t* base,uint32_t datum){
 auto query=ctx;query.r5.u32=0;
 return NativeObjectVector(query,base,datum,__imp__sub_820AC960);
}
std::array<V,2> NativeObjectVelocities(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!ObjectPointer(base,physicsHeaders,datum))throw std::runtime_error("Invalid native velocity datum");
 Frame f(ctx,base,0x100);
 f.call.r3.u32=datum;f.call.r4.u32=f.at;f.call.r5.u32=f.at+12;
 __imp__sub_820AC960(f.call,base);
 std::array<V,2> result{Vec(base,f.at),Vec(base,f.at+12)};
 for(const auto& v:result)CheckFinite(v,"Nonfinite native object velocities");
 return result;
}
// Physics body point, else object centre.
V NativePhysicsPoint(PPCContext& ctx,uint8_t* base,uint32_t datum){return NativeObjectVector(ctx,base,datum,__imp__sub_820AFA98);}
// Object origin including the parent-node transform.
V NativeObjectOrigin(PPCContext& ctx,uint8_t* base,uint32_t datum){return NativeObjectVector(ctx,base,datum,__imp__sub_820A9E58);}
// Unit eye / aim origin.
V NativeSelectionOrigin(PPCContext& ctx,uint8_t* base,uint32_t monitor){return NativeObjectVector(ctx,base,monitor,__imp__sub_820AA480);}
std::array<V,2> NativeObjectOrientation(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!ObjectPointer(base,physicsHeaders,datum))throw std::runtime_error("Invalid native orientation datum");
 Frame f(ctx,base,0x100);
 f.call.r3.u32=datum;f.call.r4.u32=f.at;f.call.r5.u32=f.at+12;
 __imp__sub_820B1928(f.call,base);
 std::array<V,2> result{Vec(base,f.at),Vec(base,f.at+12)};
 for(const auto& v:result)CheckFinite(v,"Nonfinite native object orientation");
 return result;
}
float DefinitionRadius(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 const auto definition=object?TagDefinition(base,U(base,object)):0;
 if(!definition)throw std::runtime_error("Missing object definition");
 const auto radius=F(base,definition+4);
 if(!std::isfinite(radius)||radius<0)throw std::runtime_error("Invalid definition radius");
 return radius;
}
float RuntimeRadius(uint8_t* base,uint32_t object){
 const auto r=F(base,object+44);
 if(!std::isfinite(r)||r<0)throw std::runtime_error("Invalid runtime bounding radius");
 return r;
}

// Halo 3 world point classification: true when the point is outside every
// loaded structure BSP (spec 05 A.9.1); zero mask: no objects or instances.
bool NativePointOutsideWorld(PPCContext& ctx,uint8_t* base,const V& point){
 CheckFinite(point,"Nonfinite world query point");
 Frame f(ctx,base,0x100);
 PutVec(base,f.at,point);
 f.call.r3.u64=0;f.call.r4.u32=f.at;f.call.r5.u32=kNone;f.call.r6.u32=kNone;f.call.r7.u32=0;
 __imp__sub_820AE5C0(f.call,base);
 return f.call.r3.u8!=0;
}
// Vertex walk for spec 02 3.5: false as soon as one vertex is inside the world.
bool NativeCollisionVerticesOutside(PPCContext& ctx,uint8_t* base,uint32_t datum){
 Frame frame(ctx,base,0x180);
 const auto descriptor=frame.at,iterator=frame.at+0x20;
 std::memset(base+descriptor,0,20);std::memset(base+iterator,0,28);
 auto call=frame.call;call.r3.u32=descriptor;call.r4.u32=datum;
 __imp__sub_820AF448(call,base);
 if(!call.r3.u8)return false;
 const auto nodes=U(base,descriptor+16);
 call=frame.call;call.r3.u32=iterator;call.r4.u32=U(base,descriptor+4);
 call.r5.u32=U(base,descriptor+8);call.r6.u32=U(base,descriptor+12);
 __imp__sub_820AF6D0(call,base);
 bool outside=true;
 for(;;){
  call=frame.call;call.r3.u32=iterator;__imp__sub_820AF7B0(call,base);
  if(!call.r3.u8)break;
  const auto geometry=U(base,iterator+24),node=U(base,iterator+20)&255;
  if(!Ptr(geometry)||uint64_t(geometry)+96>=0xc0000000ULL)throw std::runtime_error("Invalid native collision geometry");
  const auto count=int32_t(U(base,geometry+84));
  const auto vertices=U(base,geometry+88);
  if(count<=0)continue;
  const uint64_t matrixAddress=uint64_t(nodes)+node*52;
  if(!Ptr(nodes)||matrixAddress+52>=0xc0000000ULL||!Ptr(vertices)||uint64_t(vertices)+uint64_t(count)*16>=0xc0000000ULL)
   throw std::runtime_error("Invalid native collision vertex range");
  const auto matrix=uint32_t(matrixAddress);
  const auto scale=F(base,matrix);
  for(int32_t i=0;i<count;++i){
   const auto vertex=Vec(base,vertices+uint32_t(i)*16);
   V world;
   for(unsigned axis=0;axis<3;++axis)
    world[axis]=scale*(vertex[0]*F(base,matrix+4+axis*4)+vertex[1]*F(base,matrix+16+axis*4)+vertex[2]*F(base,matrix+28+axis*4))+F(base,matrix+40+axis*4);
   auto query=frame.call;
   if(!NativePointOutsideWorld(query,base,world)){outside=false;break;}
  }
  if(!outside)break;
 }
 return outside;
}
// Spec 02 3.5: physics point and every geometry vertex outside the world.
bool NativeObjectFullyOutside(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!NativePointOutsideWorld(ctx,base,NativePhysicsPoint(ctx,base,datum)))return false;
 return NativeCollisionVerticesOutside(ctx,base,datum);
}
// Settle validity (spec 04 4.6): not fully outside, and the origin inside the
// scenario's playable volumes (Halo 3 counterpart of the world point test).
bool NativePlacementValid(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(NativeObjectFullyOutside(ctx,base,datum))return false;
 const auto origin=NativeObjectOrigin(ctx,base,datum);
 Frame f(ctx,base,0x100);
 PutVec(base,f.at,origin);
 f.call.r3.u32=f.at;__imp__sub_821AA050(f.call,base);
 return (f.call.r3.u32&255)!=0;
}
uint32_t NativePhysicsInstance(uint8_t* base,uint32_t object){
 const auto datum=U(base,object+160);
 if(datum==kNone)return 0;
 const auto pool=U(base,0x828e62b4);
 if(!Ptr(pool))throw std::runtime_error("Invalid native physics-instance pool");
 const auto entries=U(base,pool+68);
 const uint64_t address=uint64_t(entries)+(datum&65535)*144ull;
 if(!Ptr(entries)||address+144>=0xc0000000ULL)throw std::runtime_error("Invalid native physics-instance range");
 return uint32_t(address);
}
uint32_t BodyCount(uint8_t* base,uint32_t instance){return instance?U(base,instance+36):0;}
// Held tick gate (spec 03 4.4): unparented, instance bodies in the physics world.
bool NativeCoupledSceneryEligible(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||!SceneryType(ObjectType(base,datum))||U(base,object+16)!=kNone)return false;
 const auto instance=NativePhysicsInstance(base,object);
 return instance&&(U(base,instance+4)&(1u<<3))!=0;
}
uint32_t NativeRoot(uint8_t* base,uint32_t datum){
 std::vector<uint32_t> visited;
 uint32_t current=datum;
 for(;;){
  if(std::find(visited.begin(),visited.end(),current)!=visited.end())throw std::runtime_error("Cycle in object ancestry");
  const auto object=ObjectPointer(base,physicsHeaders,current);
  if(!object)throw std::runtime_error("Invalid object ancestor");
  visited.push_back(current);
  const auto parent=U(base,object+16);
  if(parent==kNone)return current;
  current=parent;
 }
}
// Live node 0 transform (the object frame for magnets; spec 01 Q2).
forge::Pose NativeNode0(uint8_t* base,uint32_t object){
 const auto bytes=int16_t(H(base,object+314));
 const auto offset=int16_t(H(base,object+316));
 if(bytes<52||offset<0||uint64_t(object)+offset+52>=0xc0000000ULL)throw std::runtime_error("Invalid live node array");
 std::array<float,13> v;
 for(unsigned i=0;i<13;++i){v[i]=F(base,object+uint32_t(offset)+i*4);if(!std::isfinite(v[i]))throw std::runtime_error("Nonfinite node transform");}
 return forge::Pose::Unpack(v);
}
const forge::MagnetTable* MagnetTableOf(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 // Magnets: Forge scenery pieces only (Halo 3 builds them as scenery or crate
 // objects); weapons, vehicles, equipment and others never carry magnets.
 if(!object||!SceneryType(ObjectType(base,datum)))return nullptr;
 return forge::FindMagnets(physicsMap,U(base,object));
}
// Spec 01 1.3: a candidate's own group decides eligibility; markers come from its root.
forge::MagnetObject NativeMagnetObject(uint8_t* base,uint32_t datum){
 forge::MagnetObject result;
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid magnet object");
 result.datum=datum;result.center=Vec(base,object+32);result.radius=RuntimeRadius(base,object);
 result.hasGroup=MagnetTableOf(base,datum)!=nullptr;
 const auto root=NativeRoot(base,datum);
 if(const auto* table=MagnetTableOf(base,root))
  result.markers=forge::BuildMarkers(*table,NativeNode0(base,ObjectPointer(base,physicsHeaders,root)));
 return result;
}
// Halo 3 nearby-object query (spec 01 Q4: Halo 3 supplies its own).
constexpr uint32_t kNativeMagnetTypeMask=0x1cdf;
std::vector<uint32_t> NativeNearbyObjects(PPCContext& ctx,uint8_t* base,uint32_t referenceDatum,const V& center,float radius){
 const auto object=ObjectPointer(base,physicsHeaders,referenceDatum);
 if(!object||!std::isfinite(radius)||radius<0)throw std::runtime_error("Invalid native nearby-object query");
 CheckFinite(center,"Nonfinite nearby-object centre");
 Frame f(ctx,base,0x300);
 const auto point=f.at,output=f.at+0x20;
 PutVec(base,point,center);
 f.call.r3.u32=1;f.call.r4.u32=kNativeMagnetTypeMask;
 f.call.r5.u32=object+28;f.call.r6.u32=point;f.call.r7.u32=0;
 f.call.r8.u32=output;f.call.r9.u32=forge::tuning::kMaxNearby;f.call.f1.f64=radius;
 __imp__sub_820B0B60(f.call,base);
 if(f.call.r3.s32<0||f.call.r3.u32>forge::tuning::kMaxNearby)throw std::runtime_error("Invalid nearby-object count");
 std::vector<uint32_t> result;
 for(uint32_t i=0;i<f.call.r3.u32;++i){
  const auto datum=U(base,output+i*4);
  if(ObjectPointer(base,physicsHeaders,datum))result.push_back(datum);
 }
 return result;
}
// Serialize the current pose into Halo 3's map variant (stock settling path).
void SyncNativeSceneryPose(PPCContext& ctx,uint8_t* base,uint32_t datum){
 auto call=ctx;call.r3.u32=1;call.r4.u32=datum;
 __imp__sub_82284078(call,base);
}
// First body's local centre of mass (spec 05 A.3).
V NativePredictionLocalPoint(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 const auto instance=object?NativePhysicsInstance(base,object):0;
 if(!instance||!BodyCount(base,instance))throw std::runtime_error("Prediction point requires a physics body");
 const auto entry=U(base,instance+32);
 if(!Ptr(entry)||uint64_t(entry)+72>=0xc0000000ULL)throw std::runtime_error("Invalid first body entry");
 const auto body=U(base,entry+64);
 if(!Ptr(body)||uint64_t(body)+316>=0xc0000000ULL)throw std::runtime_error("Invalid first body");
 V point=Vec(base,body+304);
 const auto motion=base[body+168];
 if((U(base,instance+4)&(1u<<8))&&(motion==7||motion==6)&&U(base,entry+16)>0){
  const auto indices=U(base,entry+12);
  if(!Ptr(indices))throw std::runtime_error("Invalid body binding");
  const auto index=static_cast<int8_t>(base[indices]);
  if(index>=0){
   const auto owner=ObjectPointer(base,physicsHeaders,U(base,instance+8));
   const auto phmo=owner?PhysicsModel(base,owner):0;
   if(!phmo||uint32_t(index)>=U(base,phmo+88))throw std::runtime_error("Missing authored body");
   const auto bodies=U(base,phmo+92);
   const uint64_t record=uint64_t(bodies)+uint32_t(index)*176ull;
   if(!Ptr(bodies)||record+176>=0xc0000000ULL)throw std::runtime_error("Invalid authored body range");
   point=Vec(base,uint32_t(record)+44);  // authored centre-of-mass offset
  }
 }
 CheckFinite(point,"Nonfinite prediction point");
 return point;
}
forge::RotationGate NativeRotationGate(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid rotation object");
 forge::RotationGate gate;
 // Allowed object kinds (spec 04 2.3): everything but projectiles, sound
 // scenery, effect scenery and higher (Halo 3: 5, 9, 13 and above).
 const auto type=ObjectType(base,datum);
 gate.typeAllowed=type<=12&&type!=5&&type!=9;
 gate.connected=(U(base,object+172)&kConnected)!=0;
 const auto instance=NativePhysicsInstance(base,object);
 gate.hasInstance=instance!=0;
 if(!instance)return gate;
 gate.instanceBlocked=(U(base,instance+4)&0x80)!=0;
 const auto count=BodyCount(base,instance),bodies=U(base,instance+32);
 if(count>64||(count&&(!Ptr(bodies)||uint64_t(bodies)+uint64_t(count)*72>=0xc0000000ULL)))throw std::runtime_error("Invalid rotation body table");
 for(unsigned i=0;i<count;++i){
  const auto body=U(base,bodies+i*72+64);
  if(!Ptr(body))throw std::runtime_error("Invalid rotation body");
  gate.bodyFixed.push_back(base[body+168]==7);  // Halo 3 fixed motion
 }
 return gate;
}
V NativeMonitorView(uint8_t* base,uint32_t monitor){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object)throw std::runtime_error("Invalid monitor");
 const auto view=Vec(base,object+424);  // current view
 CheckFinite(view,"Nonfinite monitor view");
 return view;
}
V NativeMonitorDesiredView(uint8_t* base,uint32_t monitor){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object)throw std::runtime_error("Invalid monitor");
 const auto view=Vec(base,object+400);  // desired facing
 CheckFinite(view,"Nonfinite monitor desired view");
 return view;
}
void SubmitNativeMonitorView(PPCContext& ctx,uint8_t* base,uint32_t localIndex,uint32_t monitor,const V& forward){
 const auto tls=U(base,ctx.r13.u32);
 const auto controls=U(base,tls+120);
 if(localIndex>=4||!Ptr(controls)||U(base,controls+localIndex*236+16)!=monitor)
  throw std::runtime_error("Monitor view ownership changed");
 CheckFinite(forward,"Nonfinite monitor facing");
 Frame f(ctx,base,0x100);
 PutVec(base,f.at,forward);
 f.call.r3.u32=localIndex;f.call.r4.u32=f.at;
 __imp__sub_820B04B0(f.call,base);
}
// Write the flattened forward and notify (spec 02 4.1 step 2).
void SubmitNativeMonitorOrientation(PPCContext& ctx,uint8_t* base,uint32_t monitor,const V& facing){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object||ObjectType(base,monitor)!=0||U(base,object+16)!=kNone)throw std::runtime_error("Monitor orientation requires a biped root");
 const auto previous=Vec(base,object+96);
 Frame f(ctx,base,0x100);
 PutVec(base,f.at,previous);
 PutVec(base,object+96,facing);
 PutVec(base,object+108,{0.f,0.f,1.f});
 f.call.r3.u32=monitor;f.call.r4.u32=f.at;f.call.r5.u32=object+96;
 __imp__sub_820F6550(f.call,base);
}
std::array<float,6> NativeVariantBounds(uint8_t* base){
 std::array<float,6> result;
 for(unsigned i=0;i<6;++i){
  result[i]=F(base,physicsEngine+120+260+i*4);
  if(!std::isfinite(result[i]))throw std::runtime_error("Nonfinite variant bounds");
 }
 return result;
}

// ------------------------------------------------------------------ contacts (soft ceilings)
// Halo 3's own soft-ceiling collector supplies the samples; selection and the
// response follow spec 02 3.
forge::ContactSet CollectNativeContacts(PPCContext& ctx,uint8_t* base,uint32_t datum,const V& center,
                                        float objectRadius,float searchRadius,bool monitor){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid contact datum");
 const auto type=ObjectType(base,datum);
 const auto origin=NativeObjectOrigin(ctx,base,datum);
 Frame f(ctx,base,0x2300);
 const auto collection=f.at,point=f.call.r1.u32+0x2100;
 const auto reference=point+16,flags=point+32;
 PutVec(base,point,center);PutVec(base,reference,origin);
 f.call.r3.u32=collection;f.call.r4.u32=flags;f.call.r5.u32=type;
 f.call.r6.u32=0;f.call.r8.u32=reference;f.call.r9.u32=point;
 f.call.r10.u32=monitor&&base[object+1218]==1?1:0;
 f.call.f1.f64=objectRadius;f.call.f2.f64=searchRadius;
 __imp__sub_822385C8(f.call,base);
 forge::ContactSet result;
 result.flags=U(base,flags);result.primary=int32_t(U(base,collection));
 result.closestDistance=F(base,collection+4);
 const auto count=U(base,collection+20);
 if(count>256||result.primary<-1||(result.primary>=0&&uint32_t(result.primary)>=count))
  throw std::runtime_error("Invalid collected contact header");
 for(unsigned i=0;i<count;++i){
  const auto entry=collection+24+i*32,triangle=U(base,entry+8);
  if(!Ptr(triangle))throw std::runtime_error("Invalid contact triangle");
  forge::ContactSample s;
  s.normal=Vec(base,triangle);s.closestPoint=Vec(base,entry+20);
  s.planeDistance=F(base,entry+12);s.closestDistance=F(base,entry+16);
  for(unsigned j=0;j<3;++j)s.triangle[j]=Vec(base,triangle+32+j*12);
  result.samples.push_back(s);
 }
 return result;
}
void SetContactFlag(uint8_t* base,uint32_t object,bool contact){
 PutU(base,object+172,(U(base,object+172)&~kContact)|(contact?kContact:0u));
}
// Held piece: the response velocity is overwritten by the drive in the same
// tick (spec 02 3.4); only the normal, the flag and the cached point matter.
std::optional<V> ResolveNativeSceneryContact(PPCContext& ctx,uint8_t* base,uint32_t datum,V& cachedPoint){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||U(base,object+16)!=kNone)throw std::runtime_error("Contact response requires an unparented root");
 forge::ContactInput in;
 in.biped=false;in.optOut=(U(base,object+276)&4)!=0;
 in.previouslyActive=(U(base,object+172)&kContact)!=0;
 in.objectRadius=DefinitionRadius(base,datum);in.dt=TickInterval(ctx,base);
 if(!in.optOut){in.velocity=NativeObjectMotion(ctx,base,datum);in.physicsPoint=NativePhysicsPoint(ctx,base,datum);}
 in.collect=[&](const V& c,float r,float range){return CollectNativeContacts(ctx,base,datum,c,r,range,false);};
 const auto result=forge::ResolveContact(in,cachedPoint);
 if(in.optOut)return {};
 cachedPoint=result.cachedPoint;
 SetContactFlag(base,object,result.contact);
 if(result.contact)return result.normal;
 return {};
}
// Monitor (biped) response, replacing Halo 3's at the same call site.
bool ReplaceNativeMonitorContact(PPCContext& ctx,uint8_t* base){
 if(ctx.lr!=0x820F584C||!enabled||failed||!PhysicsWorld(ctx,base))return false;
 const auto datum=ctx.r3.u32,object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||ObjectType(base,datum)!=0)return false;
 const auto player=U(base,object+380),index=player&65535;
 if(player==kNone||index>=nativeEditors.size())return false;
 auto& slot=nativeEditors[index];
 if(slot.player!=player||!slot.editor||!slot.ownsMonitorContact||slot.contactMonitor!=datum)return false;
 const auto tls=U(base,ctx.r13.u32);
 auto* contact=PlayerContact(base,tls,player,false);
 if(!contact||ctx.r4.u32!=contact->record+64||U(base,contact->record+40)!=datum)
  throw std::runtime_error("Monitor contact caller lost player ownership");
 const auto time=U(base,tls+0xbc);
 forge::ContactInput in;
 in.biped=true;in.optOut=(U(base,object+276)&4)!=0;
 in.previouslyActive=(U(base,object+172)&kContact)!=0;
 in.objectRadius=DefinitionRadius(base,datum);in.dt=F(base,time+8);
 if(!in.optOut){in.velocity=NativeObjectMotion(ctx,base,datum);in.physicsPoint=NativePhysicsPoint(ctx,base,datum);}
 in.collect=[&](const V& c,float r,float range){return CollectNativeContacts(ctx,base,datum,c,r,range,true);};
 const auto destination=ctx.r4.u32;
 const auto result=forge::ResolveContact(in,Vec(base,destination));
 if(!in.optOut){
  PutVec(base,destination,result.cachedPoint);
  if(result.contact){
   // Biped response velocity applies to the monitor (spec 02 3.3).
   Frame f(ctx,base,0x100);
   PutVec(base,f.at,result.velocity);
   f.call.r3.u32=datum;f.call.r4.u32=f.at;f.call.r5.u32=0;
   __imp__sub_820F29C8(f.call,base);
  }
  SetContactFlag(base,object,result.contact);
  if(contact->normalKnown||result.contact){contact->normal=result.normal;contact->normalKnown=true;}
  // Biped extras (spec 02 3.1 step 11).
  const uint32_t tick=U(base,time+12),rate=(uint16_t(base[time+4])<<8)|base[time+5];
  if(result.collectorFlags&2){
   const uint32_t lo=uint32_t(std::lround(3.0*rate)),hi=uint32_t(std::lround(6.0*rate));
   const uint32_t stamp=U(base,object+1008);
   const uint32_t elapsed=tick-stamp;
   if(stamp==kNone||elapsed==kNone||elapsed>hi)PutU(base,object+1008,tick);
   else if(elapsed>=lo){
    PutU(base,object+276,U(base,object+276)|64u);
    auto call=ctx;call.r3.u32=datum;__imp__sub_820F2A78(call,base);
   }
  }
  if((result.collectorFlags&4)&&base[object+1218]==1)base[object+1323]|=2;
 }
 ctx.r3.u64=result.contact?1:0;
 return true;
}

// ------------------------------------------------------------------ bodies
std::array<float,13> NativeSceneryBodyPose(PPCContext& ctx,uint8_t* base,uint32_t datum,uint32_t index){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 const auto instance=object?NativePhysicsInstance(base,object):0;
 if(!instance||index>=BodyCount(base,instance))throw std::runtime_error("Invalid body index");
 Frame f(ctx,base,0x100);
 f.call.r3.u32=instance;f.call.r4.u32=index;f.call.r5.u32=f.at;
 __imp__sub_820FFAB0(f.call,base);
 std::array<float,13> result;
 for(unsigned i=0;i<13;++i){result[i]=F(base,f.at+i*4);if(!std::isfinite(result[i]))throw std::runtime_error("Nonfinite body pose");}
 return result;
}
struct NativeBody {
 forge::BodyState state;
 std::function<void()> activate;
 std::function<void(const V&)> setLinear,setAngular;
};
NativeBody NativeControlledBody(PPCContext& ctx,uint8_t* base,uint32_t datum,uint32_t index){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 const auto instance=object?NativePhysicsInstance(base,object):0;
 if(!instance||index>=BodyCount(base,instance)||BodyCount(base,instance)>64)throw std::runtime_error("Invalid controlled body");
 const auto entries=U(base,instance+32);
 const auto body=U(base,entries+index*72+64);
 if(!Ptr(body)||(body&15)||uint64_t(body)+416>=0xc0000000ULL)throw std::runtime_error("Invalid controlled body storage");
 const auto validate=[base,datum,object,instance,index,entries,body]{
  if(ObjectPointer(base,physicsHeaders,datum)!=object||NativePhysicsInstance(base,object)!=instance||
     U(base,instance+32)!=entries||index>=U(base,instance+36)||U(base,entries+index*72+64)!=body)
   throw std::runtime_error("Controlled body changed during submission");
 };
 NativeBody result;
 result.state.position=Vec(base,body+224);
 result.state.orientation={F(base,body+288),F(base,body+292),F(base,body+296),F(base,body+300)};
 result.state.linearVelocity=Vec(base,body+384);
 result.state.angularVelocity=Vec(base,body+400);
 result.activate=[&ctx,base,body,validate]{validate();auto call=ctx;call.r3.u32=body;__imp__sub_82651968(call,base);};
 const auto setMotion=[&ctx,base,body,validate](uint32_t slot,const V& value){
  validate();const auto table=U(base,body+160);
  if(!Ptr(table))throw std::runtime_error("Invalid motion dispatch table");
  auto* function=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(U(base,table+slot));
  if(!function)throw std::runtime_error("Missing native motion setter");
  Frame f(ctx,base,0x100);
  PutVec(base,f.at,value);PutF(base,f.at+12,0.f);
  f.call.r3.u32=body+160;f.call.r4.u32=f.at;function(f.call,base);
 };
 result.setLinear=[setMotion](const V& v){setMotion(60,v);};
 result.setAngular=[setMotion](const V& v){setMotion(64,v);};
 return result;
}
void ApplyBodyCommand(NativeBody& body,const forge::BodyCommand& cmd){
 if(cmd.setAngular){body.activate();body.setAngular(cmd.angular);}
 if(cmd.setLinear){body.activate();body.setLinear(cmd.linear);}
}
// Attachment compensation applies only to roots driven this tick (spec 02 5).
bool NativeAttachmentCompensationEligible(uint8_t* base,uint32_t root){
 const auto object=ObjectPointer(base,physicsHeaders,root);
 if(!object||U(base,object+16)!=kNone)return false;
 const auto definition=TagDefinition(base,U(base,object));
 if(!definition)throw std::runtime_error("Missing attachment root definition");
 if(!(H(base,definition+2)&(1u<<7)))return false;
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return false;
 const int selected=int8_t(base[instance+12]);
 if(selected<0||uint32_t(selected)>=BodyCount(base,instance))return false;
 const auto body=U(base,U(base,instance+32)+uint32_t(selected)*72+64);
 return Ptr(body)&&base[body+168]==6;
}
void RememberControllerAttachment(uint8_t* base,uint32_t datum){
 if(!NativeAttachmentCompensationEligible(base,datum)){controllerAttachments.erase(datum);return;}
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 controllerAttachments[datum]={object,NativePhysicsInstance(base,object)};
}
// Spec 02 5 maths: previousRoot o inverse(Rt) o Nt.
std::array<float,13> CompensateAttachmentPose(const forge::Pose& Rt,const forge::Pose& Nt,const V& v,const V& w,float dt){
 V axis=w;const float length=forge::Normalize(axis);
 const float theta=length*(-dt);
 const float s=std::sin(theta),c=std::cos(theta);
 forge::Pose previous=Rt;
 previous.forward=forge::RotateAbout(Rt.forward,axis,s,c);
 previous.left=forge::RotateAbout(Rt.left,axis,s,c);
 previous.up=forge::RotateAbout(Rt.up,axis,s,c);
 previous.position=forge::Add(Rt.position,forge::Mul(v,-dt));
 forge::Pose inverse;
 inverse.scale=1.f/Rt.scale;
 inverse.forward={Rt.forward[0],Rt.left[0],Rt.up[0]};
 inverse.left={Rt.forward[1],Rt.left[1],Rt.up[1]};
 inverse.up={Rt.forward[2],Rt.left[2],Rt.up[2]};
 const V p=Rt.position;
 inverse.position={-inverse.scale*forge::Dot(Rt.forward,p),-inverse.scale*forge::Dot(Rt.left,p),-inverse.scale*forge::Dot(Rt.up,p)};
 return forge::Compose(forge::Compose(previous,inverse),Nt).Packed();
}
std::optional<std::array<float,13>> NativeCompensatedAttachment(PPCContext& ctx,uint8_t* base){
 if(ctx.lr!=0x82331858||controllerAttachments.empty()||failed||!enabled||!PhysicsWorld(ctx,base))return {};
 const auto child=ctx.r3.u32,object=ObjectPointer(base,physicsHeaders,child);
 const auto attachment=nativeDetachAttachment;
 if(!attachment||attachment->datum!=child)return {};
 if(!object||object!=attachment->object)throw std::runtime_error("Attachment child changed during detach");
 const auto parent=attachment->parent;
 if(parent==kNone)return {};
 const auto root=NativeRoot(base,parent);
 const auto rootObject=ObjectPointer(base,physicsHeaders,root);
 const auto entry=controllerAttachments.find(root);
 if(entry==controllerAttachments.end())return {};
 if(entry->second.object!=rootObject||entry->second.instance!=NativePhysicsInstance(base,rootObject)){controllerAttachments.erase(entry);return {};}
 if(!NativeAttachmentCompensationEligible(base,root))return {};
 auto nodeAddress=[&](uint32_t owner,int index){
  const auto bytes=H(base,owner+314);
  const int offset=int16_t(H(base,owner+316));
  if(index<0||offset<0||uint32_t(index+1)*52>bytes)throw std::runtime_error("Invalid attachment node index");
  return owner+uint32_t(offset)+uint32_t(index)*52;
 };
 const auto parentObject=ObjectPointer(base,physicsHeaders,parent);
 if(!parentObject)throw std::runtime_error("Invalid attachment parent");
 const auto node=nodeAddress(parentObject,attachment->node);
 if(node!=ctx.r4.u32)throw std::runtime_error("Unexpected attachment transform argument");
 std::array<float,13> rootPose,parentPose;
 const auto rootNode=nodeAddress(rootObject,0);
 for(unsigned i=0;i<13;++i){rootPose[i]=F(base,rootNode+i*4);parentPose[i]=F(base,node+i*4);}
 const auto velocity=NativeObjectVelocities(ctx,base,root);
 return CompensateAttachmentPose(forge::Pose::Unpack(rootPose),forge::Pose::Unpack(parentPose),velocity[0],velocity[1],TickInterval(ctx,base));
}
// Body router for scenery (spec 02 4.1): selected body only.
void SubmitNativeSceneryTarget(PPCContext& ctx,uint8_t* base,uint32_t datum,const forge::Pose& pose,float tau){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||!SceneryType(ObjectType(base,datum)))throw std::runtime_error("Target submission requires scenery");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return;
 const int selected=int8_t(base[instance+12]);
 if(selected<0||uint32_t(selected)>=BodyCount(base,instance))return;
 auto body=NativeControlledBody(ctx,base,datum,uint32_t(selected));
 ApplyBodyCommand(body,forge::DriveBody(pose,tau,body.state));
 RememberControllerAttachment(base,datum);
}
// Body router for the monitor, with the active-biped branch (spec 02 4.1 step 2).
void SubmitNativeMonitorTarget(PPCContext& ctx,uint8_t* base,uint32_t datum,const forge::Pose& pose,float tau){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||ObjectType(base,datum)!=0||U(base,object+16)!=kNone)throw std::runtime_error("Monitor target requires a biped root");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return;
 const auto count=BodyCount(base,instance),entries=U(base,instance+32);
 if(count>64||(count&&!Ptr(entries)))throw std::runtime_error("Invalid monitor body table");
 bool upright=false;
 for(uint32_t i=0;i<count;++i)upright|=(base[entries+i*72+68]&1)!=0;
 auto submission=pose;
 if(upright){
  V facing;
  submission=forge::FlattenBipedTarget(pose,facing);
  SubmitNativeMonitorOrientation(ctx,base,datum,facing);
 }
 const int selected=int8_t(base[instance+12]);
 if(selected<0||uint32_t(selected)>=BodyCount(base,instance))return;
 auto body=NativeControlledBody(ctx,base,datum,uint32_t(selected));
 ApplyBodyCommand(body,forge::DriveBody(submission,tau,body.state));
 RememberControllerAttachment(base,datum);
}

// ------------------------------------------------------------------ aim ray
std::vector<uint32_t> NativeSelectionRayExclusions(PPCContext& ctx,uint8_t* base,uint32_t held){
 const auto tls=U(base,ctx.r13.u32),array=U(base,tls+168);
 const auto count=U(base,array+56),stride=U(base,array+36),headers=U(base,array+68);
 if(stride!=16||count>65536||!Ptr(headers))throw std::runtime_error("Invalid selection object table");
 std::vector<uint32_t> result;
 // Seatless bipeds (monitors and Spartans), in header order, at most 64.
 for(uint32_t index=0;index<count&&result.size()<64;++index){
  const auto header=headers+index*16;
  const auto salt=H(base,header);
  if(!salt||base[header+3]!=0)continue;
  const auto object=U(base,header+12);
  if(!Ptr(object))continue;
  const auto definition=TagDefinition(base,U(base,object));
  if(!definition)continue;
  if(static_cast<int32_t>(U(base,definition+672))<1)result.push_back((uint32_t(salt)<<16)|index);
 }
 // The held piece is not excluded: Ravine's held pieces sit on layers the
 // aim ray's row accepts (spec 03 Round 4).
 (void)held;
 return result;
}
struct NativeRayHit {uint32_t category=0,datum=kNone;float fraction=1;V point{},normal{};};
std::optional<NativeRayHit> NativeRay(PPCContext& ctx,uint8_t* base,uint64_t mask,const V& origin,const V& displacement,
                                      const std::vector<uint32_t>& exclusions){
 CheckFinite(origin,"Nonfinite ray");CheckFinite(displacement,"Nonfinite ray");
 auto call=ctx;
 if(ctx.r1.u32<0x5000)throw std::runtime_error("Invalid ray stack");
 call.r1.u32-=0x200;
 const auto frame=call.r1.u32,start=frame+0x80,delta=frame+0x90,output=frame+0xa0;
 PutU(base,frame,ctx.r1.u32);
 PutVec(base,start,origin);PutVec(base,delta,displacement);
 std::memset(base+output,0,96);
 call.r3.u64=mask;call.r4.u32=0;call.r5.u32=start;call.r6.u32=delta;
 call.r7.u32=call.r8.u32=call.r9.u32=kNone;call.r10.u32=output;
 SelectionRayExclusionScope scope(exclusions);
 __imp__sub_820AD3E0(call,base);
 if(!(call.r3.u32&255))return {};
 NativeRayHit hit;
 hit.category=U(base,output);hit.fraction=F(base,output+4);
 hit.point=Vec(base,output+8);hit.normal=Vec(base,output+36);
 if(hit.category==4)hit.datum=U(base,output+60);
 if(hit.category==4&&!ObjectPointer(base,physicsHeaders,hit.datum))return {};
 return hit;
}
// Halo 3 Forge's own selection categories (world, scenery, crates, items).
constexpr uint64_t kSelectionMask=0x0010000900000b9full;
// Camera obstruction rays (spec 05 A.9.2 + Ravine row 27): structure with
// front-facing surfaces only (surface flag 1 = high bit 11), plus objects of
// every kind row 27 lets block: bipeds, vehicles, weapons, equipment,
// projectiles, scenery, machines, controls, crates, creatures. Low word: bit 0
// tests objects, bit (type + 1) admits a Halo 3 object type.
constexpr uint32_t kObstructionTypes=(1u<<0)|(1u<<1)|(1u<<2)|(1u<<3)|(1u<<5)|(1u<<6)|(1u<<7)|(1u<<8)|(1u<<10)|(1u<<11);
constexpr uint64_t kObstructionMask=0x0000080900000000ull|1ull|(uint64_t(kObstructionTypes)<<1);

// ------------------------------------------------------------------ ownership
struct NativeSceneryOwner {uint32_t monitor,localIndex;};
NativeSceneryOwner ResolveNativeSceneryOwner(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t held,bool allowAttached=false){
 if(player==kNone||(player&65535)>=16)throw std::runtime_error("Invalid scenery owner");
 const auto tls=U(base,ctx.r13.u32);
 const auto contact=PlayerContact(base,tls,player,false);
 if(!contact)throw std::runtime_error("Missing player lifetime");
 const auto slot=U(base,physicsEngine+0xe198+(player&65535)*4);
 if(slot>=640||U(base,physicsEngine+0x1ac+slot*0x54)!=held)throw std::runtime_error("Native holder changed");
 const auto heldObject=ObjectPointer(base,physicsHeaders,held);
 if(!heldObject||(!allowAttached&&U(base,heldObject+16)!=kNone)||!SceneryType(ObjectType(base,held)))
  throw std::runtime_error("Held object is not unparented scenery");
 const auto monitor=U(base,contact->record+40);
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object||ObjectType(base,monitor)!=0||U(base,object+16)!=kNone||U(base,object+380)!=player)
  throw std::runtime_error("Monitor ownership changed");
 const auto controls=U(base,tls+120);
 if(!Ptr(controls))throw std::runtime_error("Invalid local controls");
 uint32_t localIndex=kNone;
 for(uint32_t i=0;i<4;++i)if(U(base,controls+i*236+16)==monitor)localIndex=i;
 if(localIndex==kNone)throw std::runtime_error("Holder has no local control slot");
 return {monitor,localIndex};
}
forge::SelectionWorld NativeSelectionWorld(PPCContext& ctx,uint8_t* base,uint32_t player){
 forge::SelectionWorld w;
 w.localPlayer=true;
 w.physicsPoint=[context=ctx,base](uint32_t datum) mutable {return NativePhysicsPoint(context,base,datum);};
 w.origin=[context=ctx,base](uint32_t datum) mutable {return NativeObjectOrigin(context,base,datum);};
 const auto tls=U(base,ctx.r13.u32),players=Ptr(tls)?U(base,tls+96):0;
 const auto table=Ptr(players)?U(base,players+68):0;
 const uint64_t record=uint64_t(table)+(player&65535)*880ull;
 if(Ptr(table)&&record+880<0xc0000000ULL){
  const auto unit=U(base,uint32_t(record)+40);
  if(ObjectPointer(base,physicsHeaders,unit))w.monitor=unit;
 }
 return w;
}
NativeEditorSlot& NativeEditor(uint32_t player){
 if(player==kNone||(player&65535)>=nativeEditors.size())throw std::runtime_error("Invalid editor owner");
 auto& slot=nativeEditors[player&65535];
 if(slot.player!=player){slot=NativeEditorSlot{};slot.player=player;}
 if(!slot.editor){slot.editor.emplace();forge::InitializeEditor(*slot.editor);}
 return slot;
}
void ApplyVisibility(NativeEditorSlot& slot,const forge::VisibilityChange& change){
 for(auto datum:change.hide)slot.shown.erase(datum);
 for(auto datum:change.show)slot.shown.emplace(datum,float(physicsTick)/30.f);
}
void SelectNativeHeldEditor(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t datum){
 auto& slot=NativeEditor(player);
 ApplyVisibility(slot,forge::SelectHeld(*slot.editor,datum,NativeSelectionWorld(ctx,base,player)));
 if(datum==kNone){
  slot.ownsMonitorContact=false;slot.contactMonitor=kNone;
  slot.shown.clear();ClearPlayerAnchors(player);
 }
}
NativeEditorSlot* OwnedSceneryEditorSlot(uint32_t datum){
 NativeEditorSlot* result=nullptr;
 for(auto& slot:nativeEditors){
  if(!slot.editor||!slot.ownsMonitorContact||slot.editor->held!=datum)continue;
  if(result)throw std::runtime_error("Multiple editors own one object");
  result=&slot;
 }
 return result;
}
forge::Editor* OwnedSceneryEditor(uint32_t datum){
 auto* slot=OwnedSceneryEditorSlot(datum);
 return slot?&*slot->editor:nullptr;
}

// ------------------------------------------------------------------ physics modes
struct SceneryBodyConstruction {uint32_t datum;bool keyframed;};
thread_local std::optional<SceneryBodyConstruction> sceneryBodyConstruction;
struct SceneryBodyConstructionScope {
 std::optional<SceneryBodyConstruction> prior=sceneryBodyConstruction;
 SceneryBodyConstructionScope(uint32_t datum,bool keyframed){sceneryBodyConstruction=SceneryBodyConstruction{datum,keyframed};}
 ~SceneryBodyConstructionScope(){sceneryBodyConstruction=prior;}
};
std::optional<SceneryBodyConstruction> SceneryConstructionRequest(uint8_t* base,uint32_t instance){
 if(!Ptr(instance))return {};
 const auto datum=U(base,instance+8);
 if(sceneryBodyConstruction&&sceneryBodyConstruction->datum==datum)return sceneryBodyConstruction;
 const auto found=physicsObjects.find(datum);
 if(found==physicsObjects.end()||!found->second.keyframedOverride||!PhysicsValid(base,datum,found->second))return {};
 return SceneryBodyConstruction{datum,true};
}
// Spec 04 4.3 steps 2-3 on Halo 3 flags, then Halo 3's own create/rebuild.
void RebuildSceneryPhysics(PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,const forge::PhysicsFlags& flags,bool create){
 if(!PhysicsValid(base,datum,object))throw std::runtime_error("Invalid physics transition object");
 const auto definition=TagDefinition(base,object.tag);
 if(!definition||(H(base,definition+2)&(1u<<11)))throw std::runtime_error("Object disallows Forge physics override");
 auto native=U(base,object.pointer+172)&~(kFrozen|kForceDynamic);
 if(flags.frozen)native|=kFrozen;
 if(flags.forceDynamic)native|=kForceDynamic;
 PutU(base,object.pointer+172,native);
 object.keyframedOverride=flags.keyframed;
 SceneryBodyConstructionScope scope(datum,object.keyframedOverride);
 auto call=ctx;call.r3.u32=datum;call.r4.u32=create?1:0;
 if(create){call.r5.u32=1;__imp__sub_821CBB88(call,base);}
 else __imp__sub_821CB8D8(call,base);
 if(!PhysicsValid(base,datum,object))throw std::runtime_error("Object invalidated during physics rebuild");
}
void TransitionNativeSceneryPhysics(PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,unsigned state,
                                    bool localHolder,forge::Editor* holder){
 if(!PhysicsValid(base,datum,object)||!SceneryType(ObjectType(base,datum)))throw std::runtime_error("Invalid physics transition");
 // Step 0: requires a model with a physics model.
 if(!PhysicsModel(base,object.pointer))return;
 std::optional<V> before;
 if(holder)before=NativePhysicsPoint(ctx,base,datum);
 forge::PhysicsFlags flags;
 if(!forge::PhysicsStateFlags(state,localHolder,flags))return;
 const bool create=NativePhysicsInstance(base,object.pointer)==0&&state!=0;
 RebuildSceneryPhysics(ctx,base,datum,object,flags,create);
 if(U(base,object.pointer+172)&kFrozen)PutU(base,object.pointer+172,U(base,object.pointer+172)|kAtRest);
 if(holder&&before){
  const auto after=NativePhysicsPoint(ctx,base,datum);
  forge::CompensateHeldOffset(*holder,*before,after);
 }
 if(Tracing())REXLOG_INFO("Advanced Forge physics: {:08X} state {} frozen {} dynamic {} keyframed {}",datum,state,flags.frozen,flags.forceDynamic,flags.keyframed);
}
void RestoreRuntimePhysics(PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,bool frozen,bool forceDynamic){
 if(!PhysicsValid(base,datum,object))return;
 const bool removeKeyframed=object.keyframedOverride;
 SceneryBodyConstructionScope authoredConstruction(datum,false);
 const auto before=U(base,object.pointer+0xac);
 const auto changed=frozen?(before|kFrozen):(before&~kFrozen);
 if(changed!=before)PutU(base,object.pointer+0xac,changed);
 auto call=ctx;call.r3.u32=datum;
 if(bool(before&kForceDynamic)!=forceDynamic){call.r4.u32=forceDynamic;__imp__sub_8232EB28(call,base);}
 else if(changed!=before||removeKeyframed){call.r4.u32=0;__imp__sub_821CB8D8(call,base);}
 object.keyframedOverride=false;
}
bool PhysicsHeld(uint8_t* base,uint32_t datum){
 for(unsigned i=0;i<16;++i){const auto slot=U(base,physicsEngine+0xe198+i*4);
  if(slot<640&&U(base,physicsEngine+0x1ac+slot*0x54)==datum)return true;
 }return false;
}
// Spec 04 4.2 with Halo 3's variant slot and settle-queue membership.
unsigned SelectNativeSceneryPhysics(PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,forge::PhysicsMode mode,bool held){
 if(!PhysicsValid(base,datum,object))throw std::runtime_error("Invalid physics selection");
 const auto variantSlot=H(base,object.pointer+24);
 const bool variantObject=variantSlot!=65535;
 bool keyframed=false,settling=false;
 if(variantObject&&!held&&(mode==forge::PhysicsMode::Fixed||mode==forge::PhysicsMode::Phased)){
  const auto authored=AuthoredKeyframedBody(base,object.pointer);
  if(!authored)throw std::runtime_error("Invalid authored body table");
  keyframed=*authored;
 }else if(variantObject&&!held&&mode==forge::PhysicsMode::Normal){
  auto query=ctx;query.r3.u32=datum;__imp__sub_8227EB28(query,base);
  settling=(query.r3.u32&255)!=0;
 }
 return forge::SelectPhysicsState(mode,variantObject,held,keyframed,settling);
}
void SelectAndTransition(PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,forge::PhysicsMode mode,forge::Editor* holder){
 const auto state=SelectNativeSceneryPhysics(ctx,base,datum,object,mode,holder!=nullptr);
 TransitionNativeSceneryPhysics(ctx,base,datum,object,state,true,holder);
}
forge::PhysicsMode ModeOf(const PhysicsObject& o){return o.mode.value_or(o.authoredMode);}
// Menu physics edit (spec 04 4.4): transition only when the state changes.
void ChangeNativeSceneryPhysicsMode(PPCContext& ctx,uint8_t* base,uint32_t datum,forge::PhysicsMode requested){
 auto it=physicsObjects.find(datum);
 if(it==physicsObjects.end()||!PhysicsValid(base,datum,it->second))throw std::runtime_error("Physics edit without valid object");
 auto& object=it->second;
 const auto previous=ModeOf(object);
 auto* editor=OwnedSceneryEditor(datum);
 const auto before=SelectNativeSceneryPhysics(ctx,base,datum,object,previous,editor!=nullptr);
 object.mode=static_cast<forge::PhysicsMode>(forge::EditPhysicsProperty(uint16_t(previous),uint16_t(requested))&0xc0);
 const auto after=SelectNativeSceneryPhysics(ctx,base,datum,object,*object.mode,editor!=nullptr);
 if(after!=before)TransitionNativeSceneryPhysics(ctx,base,datum,object,after,true,editor);
 if(!editor)object.releasedPhysics=true;
}
void SyncPhysicsPose(PPCContext& ctx,uint8_t* base,uint32_t datum,const PhysicsObject& object){
 if(!PhysicsValid(base,datum,object)||U(base,object.pointer+0x10)!=kNone)return;
 const auto slot=H(base,object.pointer+0x18);
 if(slot>=640)return;
 const auto record=physicsEngine+0x1a8+slot*0x54;
 if(U(base,record+4)!=datum)return;
 if(std::memcmp(base+object.pointer+0x54,base+record+0x10,36)==0)return;
 auto sync=ctx;sync.r3.u32=0;sync.r4.u32=datum;__imp__sub_82284078(sync,base);
}
// Leaving Forge editing: restore authored Halo 3 physics on every touched object.
void RestorePhysics(PPCContext& ctx,uint8_t* base){
 ClearNativeEditors();controllerAttachments.clear();ClearAnchorWorld();
 if(!PhysicsWorld(ctx,base)){physicsObjects.clear();return;}
 restoringPhysics=true;
 struct Guard{~Guard(){restoringPhysics=false;}} guard;
 for(auto& [datum,object]:physicsObjects){
  if(!object.mode||!PhysicsValid(base,datum,object))continue;
  RestoreRuntimePhysics(ctx,base,datum,object,bool(object.original&kFrozen),bool(object.original&kForceDynamic));
  SyncPhysicsPose(ctx,base,datum,object);
 }
 physicsObjects.clear();
}
void Fail(PPCContext& ctx,uint8_t* base,const char* stage,const std::exception& e){
 REXLOG_ERROR("Advanced Forge {} failed: {}",stage,e.what());
 failed=true;
 try{RestorePhysics(ctx,base);}catch(const std::exception& r){REXLOG_ERROR("Advanced Forge restoration failed: {}",r.what());}
}
PhysicsObject& CapturePhysics(uint8_t* base,uint32_t datum,uint32_t pointer){
 auto it=physicsObjects.find(datum);
 if(it==physicsObjects.end()||!PhysicsValid(base,datum,it->second)){
  const auto authored=AuthoredPhysics(base,pointer);
  PhysicsObject object;object.pointer=pointer;object.tag=U(base,pointer);object.original=U(base,pointer+172);
  object.authoredMode=authored;object.mode=authored;
  it=physicsObjects.insert_or_assign(datum,object).first;
 }
 return it->second;
}

// ------------------------------------------------------------------ input
// Read Halo 3's frame packet before its own Forge input routine (the direct
// counterpart of the routine in spec 04 1). Scenery and crates only.
struct NativeInputFrame:forge::InputFrame {bool processed=false;};
std::optional<NativeInputFrame> ReadNativeSceneryInput(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t packet,uint32_t& held){
 if(!Ptr(packet)||uint64_t(packet)+116>=0xc0000000ULL)throw std::runtime_error("Invalid manipulation frame");
 Frame f(ctx,base,0x100);
 PutU(base,f.at,kNone);
 f.call.r3.u32=player;f.call.r4.u32=f.at;f.call.r5.u32=0;
 __imp__sub_820B06A0(f.call,base);
 if(!(f.call.r3.u32&255))return {};
 held=U(base,f.at);
 if(!ObjectPointer(base,physicsHeaders,held)||!SceneryType(ObjectType(base,held)))return {};
 NativeInputFrame frame;
 frame.eligible=true;
 frame.forward=F(base,packet+20);frame.left=F(base,packet+24);
 frame.trigger=F(base,packet+44);
 // Halo 3 raises this flag when manipulation was active on the previous
 // tick, as spec 04 1.2 step 7 describes (one-tick latency).
 frame.rotationAvailable=base[packet+28]!=0;
 if(frame.rotationAvailable){frame.lookA=F(base,packet+32);frame.lookB=F(base,packet+36);}
 // Replace Halo 3's stick processing with the spec's chain (Ravine dead
 // zones and response curves), from the controller's raw state.
 const auto tls=U(base,ctx.r13.u32),controls=U(base,tls+120);
 const auto unit=U(base,U(base,U(base,tls+96)+68)+(player&65535)*880+40);
 for(uint32_t i=0;i<4&&Ptr(controls);++i)
  if(U(base,controls+i*236+16)==unit&&rawSticks[i]){
   const auto sticks=forge::ProcessSticks(*rawSticks[i]);
   // Triggers carry no dead zone or curve (spec 04 1.2); Halo 3's analog stays.
   frame.forward=sticks.forward;frame.left=sticks.left;
   if(frame.rotationAvailable){frame.lookA=sticks.lookA;frame.lookB=sticks.lookB;}
   frame.processed=true;
   break;
  }
 return frame;
}
// True when the packet was consumed (Halo 3's own routine must not also run).
bool ConsumeNativeSceneryInput(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t packet,NativeEditorSlot& slot){
 uint32_t held=kNone;
 const auto frame=ReadNativeSceneryInput(ctx,base,player,packet,held);
 if(!frame){slot.input.active=false;return false;}
 if(slot.editor->held!=held)throw std::runtime_error("Input refers to a different held object");
 const auto tls=U(base,ctx.r13.u32),pool=U(base,tls+96);
 const auto record=U(base,pool+68)+(player&65535)*880;
 const auto remaining=forge::ShapeInput(slot.input,*frame);
 if(Tracing()&&physicsTick%15==0)
  REXLOG_INFO("Advanced Forge input: tick {} spec sticks {} trigger {} move {},{} look {} {},{} active {} distance {} roll {} yaw {} pitch {}",
   physicsTick,frame->processed,frame->trigger,frame->forward,frame->left,frame->rotationAvailable,frame->lookA,frame->lookB,
   slot.input.active,slot.input.distance,slot.input.roll,slot.input.yaw,slot.input.pitch);
 // Keep Halo 3's own bookkeeping consistent with the consumed input.
 base[record+764]=slot.input.active?1:0;
 if(slot.input.active){
  PutF(base,record+768,frame->forward);PutF(base,record+772,frame->left);
  if(frame->rotationAvailable){PutF(base,record+776,frame->lookA);PutF(base,record+780,frame->lookB);}
 }
 PutF(base,packet+20,remaining[0]);PutF(base,packet+24,remaining[1]);
 return true;
}

// ------------------------------------------------------------------ held stage
void PublishAnchors(PPCContext& ctx,uint8_t* base,uint32_t localIndex,NativeEditorSlot& slot){
 const auto tls=U(base,ctx.r13.u32),observers=U(base,tls+716);
 if(!Ptr(observers)||localIndex>=4){ClearPlayerAnchors(slot.player);return;}
 AnchorView view;view.player=slot.player;view.updated=std::chrono::steady_clock::now();view.time=float(physicsTick)/30.f;
 for(const auto& [datum,since]:slot.shown){
  if(!ObjectPointer(base,physicsHeaders,datum))continue;
  const auto root=NativeRoot(base,datum);
  const auto* table=MagnetTableOf(base,root);
  if(!table)continue;
  const auto markers=forge::BuildMarkers(*table,NativeNode0(base,ObjectPointer(base,physicsHeaders,root)));
  for(size_t i=0;i<markers.size();++i){
   VisibleAnchor anchor;anchor.datum=datum;anchor.position=markers[i].worldPosition;anchor.shown=since;
   anchor.seed=float((datum&0xffff)*37+i*13)*0.001f;
   view.anchors.push_back(anchor);
  }
 }
 std::lock_guard lock(anchorMutex);anchorViews[localIndex]=std::move(view);
}
// The coupled held stage (spec 03 4.4): rotation, offset decay, distance,
// held update (snap and magnets), then monitor follow.
void RunHeldStage(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t datum,uint32_t monitor,uint32_t localIndex){
 auto& slot=nativeEditors[player&65535];
 auto& e=*slot.editor;
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 const auto monitorObject=ObjectPointer(base,physicsHeaders,monitor);
 if(!object||!monitorObject)throw std::runtime_error("Held stage lost its objects");
 const auto tls=U(base,ctx.r13.u32),time=U(base,tls+188);
 const float dt=F(base,time+8);
 const uint32_t tick=U(base,time+12);
 const float runtimeRadius=RuntimeRadius(base,object);
 // 1. Rotation.
 forge::RotateHeld(e,slot.input,NativeMonitorView(base,monitor),dt,NativeRotationGate(base,datum));
 // 2. Offset decay. 3. Hold distance (push/pull).
 e.offsetScale=std::max(e.offsetScale-e.offsetDecay,0.f);
 e.holdDistance=forge::ClampHoldDistance(e,slot.input,e.holdDistance,true,runtimeRadius);
 // 4. Held update.
 forge::HeldWorld w;
 const auto instance=NativePhysicsInstance(base,object);
 w.hasBodies=instance&&BodyCount(base,instance)>0;
 w.tick=tick;w.dt=dt;
 w.heldVelocity=NativeObjectMotion(ctx,base,datum);
 w.heldOrigin=NativeObjectOrigin(ctx,base,datum);
 w.heldPhysicsPoint=NativePhysicsPoint(ctx,base,datum);
 w.heldRuntimeRadius=runtimeRadius;w.heldDefinitionRadius=DefinitionRadius(base,datum);
 w.monitorDesiredFacing=NativeMonitorDesiredView(base,monitor);
 w.monitorMovement=Vec(base,monitorObject+496);
 CheckFinite(w.monitorMovement,"Nonfinite processed movement");
 w.precision=(U(base,monitorObject+392)&1)!=0;
 {
  const auto definition=TagDefinition(base,U(base,monitorObject));
  auto call=ctx;call.r3.u32=monitor;__imp__sub_820EA138(call,base);
  const float peak=definition?F(base,definition+720):1.f,fraction=float(call.f1.f64);
  w.boost=1.f+(peak-1.f)*fraction;
 }
 w.bounds=NativeVariantBounds(base);
 w.monitorReference=NativeObjectOrigin(ctx,base,monitor);
 w.viewDirection=NativeMonitorDesiredView(base,monitor);
 w.heldFullyOutside=[&]{return NativeObjectFullyOutside(ctx,base,datum);};
 w.body0Transform=[&]{return forge::Pose::Unpack(NativeSceneryBodyPose(ctx,base,datum,0));};
 w.contact=[&](V& cached){return ResolveNativeSceneryContact(ctx,base,datum,cached);};
 // Magnets: scenery only, and only while enabled (spec 01 5.2).
 forge::MagnetObject heldMagnets;
 const bool magnetPiece=MagnetTableOf(base,datum)!=nullptr;
 w.magnets=[&](forge::Pose& submission,bool& snapped)->uint32_t{
  forge::MagnetPair pair;snapped=false;
  if(e.magnetsEnabled&&magnetPiece){
   heldMagnets=NativeMagnetObject(base,datum);
   forge::MagnetWorld mw;
   mw.held=&heldMagnets;mw.heldPhysicsPoint=w.heldPhysicsPoint;
   mw.processedMovement=w.monitorMovement;
   mw.nearby=[&](const V& c,float r){
    std::vector<forge::MagnetObject> list;
    for(auto id:NativeNearbyObjects(ctx,base,datum,c,r)){
     if(id==datum||!MagnetTableOf(base,id)){forge::MagnetObject o;o.datum=id;
      if(const auto p=ObjectPointer(base,physicsHeaders,id)){o.center=Vec(base,p+32);o.radius=F(base,p+44);}
      list.push_back(o);continue;}
     list.push_back(NativeMagnetObject(base,id));
    }
    return list;
   };
   pair=forge::MagnetStep(e,mw,submission,snapped);
  }
  ApplyVisibility(slot,forge::SetMagnetTarget(e,pair.candidate,true));
  return pair.candidate;
 };
 const auto held=forge::UpdateHeld(e,w);
 if(held.submitted)SubmitNativeSceneryTarget(ctx,base,datum,held.submission,forge::tuning::kHeldDriveTime);
 // 5. Monitor follow, after the held submission.
 forge::FollowWorld fw;
 fw.camera.heldPhysicsPoint=NativePhysicsPoint(ctx,base,datum);
 fw.camera.view=NativeMonitorDesiredView(base,monitor);
 fw.camera.definitionRadius=w.heldDefinitionRadius;
 fw.camera.dt=dt;
 const auto velocities=NativeObjectVelocities(ctx,base,datum);
 fw.camera.linearVelocity=velocities[0];fw.camera.angularVelocity=velocities[1];
 fw.camera.heldOriginNow=NativeObjectOrigin(ctx,base,datum);
 if(instance&&BodyCount(base,instance)>0){
  fw.camera.hasBody=true;
  const auto orientation=NativeObjectOrientation(ctx,base,datum);
  forge::Pose p;p.forward=orientation[0];p.up=orientation[1];p.left=forge::Cross(p.up,p.forward);
  fw.camera.heldOrientation=forge::QuatFromBasis(p.GetBasis());
  fw.camera.firstBodyLocalCenter=NativePredictionLocalPoint(base,datum);
 }
 fw.monitorReference=NativeObjectOrigin(ctx,base,monitor);
 fw.monitorContactActive=(U(base,monitorObject+172)&kContact)!=0;
 if(fw.monitorContactActive){
  const auto* contact=PlayerContact(base,tls,player,true);
  if(!contact)throw std::runtime_error("Monitor contact normal unknown");
  fw.monitorContactNormal=contact->normal;
 }
 fw.pointOutsideWorld=[&](const V& p){return NativePointOutsideWorld(ctx,base,p);};
 const auto exclusions=std::vector<uint32_t>{datum,monitor};
 fw.obstructionRay=[&](const V& from,const V& to)->std::optional<forge::RayHit>{
  const auto hit=NativeRay(ctx,base,kObstructionMask,from,forge::Sub(to,from),exclusions);
  if(!hit)return {};
  return forge::RayHit{hit->fraction,hit->point};
 };
 unsigned obstructionRays=0,obstructionHits=0;
 if(Tracing()){
  const auto ray=fw.obstructionRay;
  fw.obstructionRay=[&,ray](const V& a,const V& b){auto h=ray(a,b);++obstructionRays;if(h)++obstructionHits;return h;};
 }
 const auto follow=forge::MonitorFollow(e,fw);
 if(Tracing()&&(e.focusOutside||obstructionRays))
  REXLOG_INFO("Advanced Forge camera: tick {} focus outside {} rays {} hits {} clear fraction {} leash {}",tick,e.focusOutside,obstructionRays,obstructionHits,e.obstruction.fraction,e.leash);
 SubmitNativeMonitorTarget(ctx,base,monitor,follow.monitorTarget,forge::tuning::kMonitorDriveTime);
 SubmitNativeMonitorView(ctx,base,localIndex,monitor,follow.facing);
 PublishAnchors(ctx,base,localIndex,slot);
 // Halo 3's menus read its own distance cache.
 PutF(base,physicsEngine+0xe1d8+(player&65535)*4,e.holdDistance);
 if(Tracing()&&tick%30==0)
  REXLOG_INFO("Advanced Forge held: tick {} held {:08X} target {:08X} snapped {} distance {} pose {},{},{} forward {},{},{} shown {}",
   tick,datum,held.magnetCandidate,held.snapped,e.holdDistance,held.submission.position[0],held.submission.position[1],held.submission.position[2],
   held.submission.forward[0],held.submission.forward[1],held.submission.forward[2],slot.shown.size());
 if(Tracing()&&forge::Length(w.monitorMovement)>0)
  REXLOG_INFO("Advanced Forge movement: tick {} unit movement {},{},{} facing {},{},{} boost {} precision {} velocity {},{},{} target {},{},{}",
   tick,w.monitorMovement[0],w.monitorMovement[1],w.monitorMovement[2],w.monitorDesiredFacing[0],w.monitorDesiredFacing[1],w.monitorDesiredFacing[2],
   w.boost,w.precision,w.heldVelocity[0],w.heldVelocity[1],w.heldVelocity[2],e.target.position[0],e.target.position[1],e.target.position[2]);
}
bool DispatchHeldStage(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t datum){
 if(player==kNone||(player&65535)>=nativeEditors.size())return false;
 auto& slot=nativeEditors[player&65535];
 if(slot.player!=player||!slot.editor||!slot.ownsMonitorContact)return false;
 try{
  if(!enabled.load()||failed)throw std::runtime_error("Held stage lost its lifecycle");
  if(!PhysicsWorld(ctx,base))throw std::runtime_error("Held stage outside Advanced Forge");
  const auto owner=ResolveNativeSceneryOwner(ctx,base,player,datum,true);
  if(owner.monitor!=slot.contactMonitor||slot.editor->held!=datum)throw std::runtime_error("Held stage ownership changed");
  const bool coupled=NativeCoupledSceneryEligible(base,datum);
  if(coupled)RunHeldStage(ctx,base,player,datum,owner.monitor,owner.localIndex);
  // Spec 03 2.1 step 6: refresh the held origin.
  slot.editor->heldOrigin=NativeObjectOrigin(ctx,base,datum);
  if(!coupled)return true;
  // Halo 3 bookkeeping of the skipped native block: serialize once when
  // manipulation stops.
  const auto dirty=physicsEngine+58520+(player&65535);
  if(slot.input.active)base[dirty]=1;
  else if(base[dirty]){SyncNativeSceneryPose(ctx,base,datum);base[dirty]=0;}
 }catch(const std::exception& e){Fail(ctx,base,"held stage",e);}
 return true;
}
}  // namespace

bool OwnsKeyframedSceneryPose(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(failed||!OwnedSceneryEditor(datum)||!PhysicsWorld(ctx,base))return false;
 const auto found=physicsObjects.find(datum);
 if(found==physicsObjects.end()||!found->second.keyframedOverride||!PhysicsValid(base,datum,found->second))return false;
 const auto object=found->second.pointer;
 if(!SceneryType(ObjectType(base,datum))||U(base,object+16)!=kNone)return false;
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return false;
 const int selected=int8_t(base[instance+12]);
 if(selected<0||uint32_t(selected)>=BodyCount(base,instance))return false;
 const auto body=U(base,U(base,instance+32)+uint32_t(selected)*72+64);
 return Ptr(body)&&base[body+168]==6;
}
void AttachControls(rex::ui::ImGuiDrawer*){
 enabled=rex::cvar::GetFlagSource("halo3mp_advanced_forge")==rex::cvar::Source::kCommandLine?
     REXCVAR_GET(halo3mp_advanced_forge):true;
}
void AttachRenderer(rex::graphics::CommandProcessor* renderer){
 markerRenderer=renderer;
 if(!markerMaterial.valid())markerMaterial=std::async(std::launch::async,forge::BuildMarkerMaterial).share();
}
}  // namespace advanced_forge

// ======================================================================= hooks
using namespace advanced_forge;

// Raw controller sticks: Halo 3's poll (sub_820903E0, user r3, record r5)
// passes each stick's raw XInput shorts to its dead-zone routine
// (sub_82206B90: r3 = 1 left / 0 right, output r4 = record +52 / +56, x r5,
// y r6). Record the raw values; Halo 3's own processing is left untouched.
namespace advanced_forge { namespace {
std::array<uint32_t,4> rawRecords{};
thread_local int pollUser=-1;
}}
extern "C" void __imp__sub_820903E0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_820903E0){
 const auto user=ctx.r3.u32;
 if(user<4)rawRecords[user]=ctx.r5.u32;
 const int prior=pollUser;pollUser=user<4?int(user):-1;
 __imp__sub_820903E0(ctx,base);
 pollUser=prior;
 if(user<4&&!(ctx.r3.u32&255))rawSticks[user].reset();
}
extern "C" void __imp__sub_82206B90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82206B90){
 if(pollUser>=0&&rawRecords[pollUser]){
  auto& raw=rawSticks[pollUser];
  if(!raw)raw.emplace();
  const auto x=int16_t(ctx.r5.u32&0xffff),y=int16_t(ctx.r6.u32&0xffff);
  if(ctx.r4.u32==rawRecords[pollUser]+52){raw->lx=x;raw->ly=y;}
  else if(ctx.r4.u32==rawRecords[pollUser]+56){raw->rx=x;raw->ry=y;}
 }
 __imp__sub_82206B90(ctx,base);
}
// Manipulation input (Halo 3's counterpart of spec 04 1).
REX_HOOK_RAW(sub_821F04C0){
 const auto player=ctx.r3.u32;
 if(enabled.load()&&!failed&&player!=kNone&&(player&65535)<16&&PhysicsWorld(ctx,base)){
  auto& slot=nativeEditors[player&65535];
  if(slot.player==player&&slot.editor&&slot.ownsMonitorContact){
   try{if(ConsumeNativeSceneryInput(ctx,base,player,ctx.r4.u32,slot))return;}
   catch(const std::exception& e){Fail(ctx,base,"input",e);}
  }else if(slot.player==player)slot.input.active=false;  // nothing held by the editor
 }
 __imp__sub_821F04C0(ctx,base);
}
extern "C" void __imp__sub_82333388(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82333388){
 controllerAttachments.erase(ctx.r3.u32);
 __imp__sub_82333388(ctx,base);
}
extern "C" void __imp__sub_823316D8(PPCContext& __restrict,uint8_t*);
void ResetNativeDetachPhysics(PPCContext& ctx,uint8_t* base);
REX_HOOK_RAW(sub_823316D8){
 const bool detachWithoutReconnect=ctx.lr==0x82331858&&(ctx.r28.u32&255)==0;
 struct FinishDetachPose {PPCContext& ctx;uint8_t* base;bool reset;~FinishDetachPose(){if(reset)ResetNativeDetachPhysics(ctx,base);}} finish{ctx,base,detachWithoutReconnect};
 std::optional<std::array<float,13>> pose;
 try{pose=NativeCompensatedAttachment(ctx,base);}
 catch(const std::exception& e){
  if(auto* grab=nativeGrabTransaction)grab->error=e.what();
  else{failed=true;REXLOG_ERROR("Advanced Forge attachment compensation failed: {}",e.what());}
 }
 if(!pose){__imp__sub_823316D8(ctx,base);return;}
 const auto stack=ctx.r1.u32;
 ctx.r1.u32-=0x100;
 const auto input=ctx.r1.u32+0x60;
 PutU(base,ctx.r1.u32,stack);
 for(unsigned i=0;i<13;++i)PutF(base,input+i*4,(*pose)[i]);
 struct RestoreStack {PPCContext& ctx;uint32_t stack;~RestoreStack(){ctx.r1.u32=stack;}} restore{ctx,stack};
 ctx.r4.u32=input;
 __imp__sub_823316D8(ctx,base);
}
// Detach physics reset inside our grab transaction (spec 02 5 step 6-7).
void ResetNativeDetachPhysics(PPCContext& ctx,uint8_t* base){
 auto* attachment=nativeDetachAttachment;
 auto* grab=nativeGrabTransaction;
 if(!attachment||!attachment->deferVelocity||attachment->physicsReset||!grab||grab->datum!=attachment->datum||
    !grab->error.empty()||failed||!enabled.load())return;
 try{
  const auto datum=attachment->datum;
  const auto pointer=ObjectPointer(base,physicsHeaders,datum);
  auto found=physicsObjects.find(datum);
  if(!pointer||pointer!=attachment->object||found==physicsObjects.end()||!PhysicsValid(base,datum,found->second)||U(base,pointer+16)!=kNone)
   throw std::runtime_error("Detached object invalidated before physics reset");
  const auto flags=U(base,pointer+172);
  const bool overrides=(flags&(kFrozen|kForceDynamic))||found->second.keyframedOverride;
  if(attachment->rebuildAfterUnlink||overrides)RebuildSceneryPhysics(ctx,base,datum,found->second,forge::PhysicsFlags{},false);
  attachment->physicsReset=true;
 }catch(const std::exception& e){grab->error=e.what();}
}
extern "C" void __imp__sub_82330778(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82330778){
 const bool detachReconnect=ctx.lr==0x82331870;
 __imp__sub_82330778(ctx,base);
 if(detachReconnect)ResetNativeDetachPhysics(ctx,base);
}
extern "C" void __imp__sub_82330B20(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82330B20){
 const auto* attachment=nativeDetachAttachment;
 const auto* grab=nativeGrabTransaction;
 if(ctx.lr==0x823318AC&&attachment&&attachment->physicsReset&&attachment->datum==ctx.r3.u32&&grab&&grab->error.empty()){
  const auto object=ObjectPointer(base,physicsHeaders,attachment->datum);
  if(object==attachment->object&&object&&(U(base,object+172)&kConnected))return;
 }
 __imp__sub_82330B20(ctx,base);
}
extern "C" void __imp__sub_821FCA48(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821FCA48){
 const auto tls=U(base,ctx.r13.u32);
 const bool players=Ptr(tls)&&ctx.r3.u32==U(base,tls+96);
 __imp__sub_821FCA48(ctx,base);
 if(players)ClearNativePlayerContacts();
}
extern "C" void __imp__sub_821E7A90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821E7A90){
 __imp__sub_821E7A90(ctx,base);
 InitializeNativePlayerContact(ctx,base,ctx.r3.u32);
}
extern "C" void __imp__sub_821EF708(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821EF708){
 const auto player=ctx.r3.u32;
 const auto tls=U(base,ctx.r13.u32);
 const auto* contact=PlayerContact(base,tls,player,false);
 const auto record=contact?contact->record:0;
 __imp__sub_821EF708(ctx,base);
 if(record&&H(base,record)==(player>>16)&&(U(base,record+4)&2)){
  auto& state=nativePlayerContacts[player&65535];
  if(state.player==player&&state.record==record)state={};
  auto& editor=nativeEditors[player&65535];
  if(editor.player==player){ClearPlayerAnchors(player);editor=NativeEditorSlot{};}
  if(completedMonitorExitPlayer==player)completedMonitorExitPlayer.reset();
 }
}
extern "C" void __imp__sub_820FFBE0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_820FFBE0){
 try{if(ReplaceNativeMonitorContact(ctx,base))return;}
 catch(const std::exception& e){Fail(ctx,base,"monitor contact",e);}
 auto observation=ObserveNativeContact(ctx,base);
 struct Scope {NativeContactObservation* previous;~Scope(){nativeContactObservation=previous;}} scope{nativeContactObservation};
 nativeContactObservation=observation?&*observation:nullptr;
 __imp__sub_820FFBE0(ctx,base);
 if(observation&&observation->normal)
  if(auto* state=PlayerContact(base,observation->tls,observation->player,false)){state->normal=*observation->normal;state->normalKnown=true;}
}
extern "C" void __imp__sub_82237E58(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82237E58){
 const auto observation=nativeContactObservation;
 const bool primary=observation&&ctx.lr==0x820FFED0&&ctx.r9.u32==0;
 const auto normal=ctx.r6.u32;
 __imp__sub_82237E58(ctx,base);
 if(primary&&(ctx.r3.u32&255)&&Ptr(normal)){
  const auto value=Vec(base,normal);
  if(std::all_of(value.begin(),value.end(),[](float v){return std::isfinite(v);}))observation->normal=value;
 }
}
// Extend Halo 3's object filter with the aim ray's exclusion list.
REX_HOOK_RAW(sub_820AF170){
 const auto exclusions=selectionRayExclusions;
 if(!exclusions||exclusions->empty()){__imp__sub_820AF170(ctx,base);return;}
 const auto entry=ctx;
 __imp__sub_820AF170(ctx,base);
 if(!ctx.r3.u32)return;
 for(size_t i=0;i<exclusions->size();i+=3){
  auto call=entry;
  call.r7.u32=(*exclusions)[i];
  call.r8.u32=i+1<exclusions->size()?(*exclusions)[i+1]:kNone;
  call.r9.u32=i+2<exclusions->size()?(*exclusions)[i+2]:kNone;
  __imp__sub_820AF170(call,base);
  if(!call.r3.u32){ctx.r3.u32=0;return;}
 }
}
// Phased release maps "phased = true" onto Halo 3's release synchronization.
REX_HOOK_RAW(sub_82284078){
 if(ctx.lr==0x8227FEC4&&nativePhasedReleaseDatum==ctx.r4.u32)ctx.r3.u32=1;
 __imp__sub_82284078(ctx,base);
}
extern "C" void __imp__sub_820F2DD0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82283950(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_820F2DD0){
 if(ctx.lr==0x8227FED0&&nativePhasedReleaseDatum==ctx.r3.u32)ctx.r4.u32=1;
 __imp__sub_820F2DD0(ctx,base);
}
// Phased pieces are not queued for settling (spec 04 4.5 step 1).
REX_HOOK_RAW(sub_82283950){
 if(ctx.lr==0x8227FFC8&&nativePhasedReleaseDatum==ctx.r3.u32)return;
 __imp__sub_82283950(ctx,base);
}
// Variant removal: release the editor (selection reset only).
extern "C" void __imp__sub_8227E710(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227E710){
 const auto variant=ctx.r3.u32;
 auto selection=ctx;
 if(variant<640&&!failed&&PhysicsWorld(selection,base)){
  const auto datum=U(base,physicsEngine+0x1ac+variant*0x54);
  for(uint32_t i=0;i<nativeEditors.size();++i){
   auto& editor=nativeEditors[i];
   if(!editor.editor||!editor.ownsMonitorContact||U(base,physicsEngine+0xe198+i*4)!=variant||editor.editor->held!=datum)continue;
   try{SelectNativeHeldEditor(selection,base,editor.player,kNone);}
   catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge removal reset failed: {}",e.what());}
  }
 }
 __imp__sub_8227E710(ctx,base);
}
// Object deleted (spec 03 1.5).
extern "C" void __imp__sub_82280860(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280860){
 const auto datum=ctx.r4.u32;
 auto deletion=ctx;
 if(datum!=kNone&&!failed&&PhysicsWorld(deletion,base)){
  for(auto& slot:nativeEditors){
   if(slot.player==kNone||!slot.editor)continue;
   auto& e=*slot.editor;
   if(e.held!=datum&&e.magnetTarget!=datum&&e.aimed!=datum&&!slot.shown.contains(datum))continue;
   try{
    forge::VisibilityChange change;
    if(forge::ObjectDeleted(e,datum,NativeSelectionWorld(deletion,base,slot.player),change)){
     slot.ownsMonitorContact=false;slot.contactMonitor=kNone;
    }
    ApplyVisibility(slot,change);
    slot.shown.erase(datum);
   }catch(const std::exception& error){failed=true;REXLOG_ERROR("Advanced Forge deletion cleanup failed: {}",error.what());}
  }
 }
 __imp__sub_82280860(ctx,base);
}
// Release (drop) of a held object.
extern "C" void __imp__sub_8227FDF8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227FDF8){
 const auto releasePlayer=ctx.r3.u32;
 const auto index=releasePlayer&65535;
 const bool skipPlacement=(ctx.r5.u32&255)!=0;
 uint32_t engine=0,heldBefore=kNone;
 bool ours=false;
 if(!failed&&index<16&&PhysicsWorld(ctx,base)){
  engine=physicsEngine;
  const auto slot=U(base,engine+0xe198+index*4);
  if(slot<640)heldBefore=U(base,engine+0x1ac+slot*0x54);
  auto& editor=nativeEditors[index];
  ours=heldBefore!=kNone&&editor.player==releasePlayer&&editor.ownsMonitorContact&&editor.editor&&editor.editor->held==heldBefore;
 }
 bool placement=false;
 if(ours){
  try{
   const auto pointer=ObjectPointer(base,physicsHeaders,heldBefore);
   if(!pointer)throw std::runtime_error("Released object lost");
   placement=!skipPlacement&&U(base,pointer+16)==kNone;
   SelectNativeHeldEditor(ctx,base,releasePlayer,kNone);
  }catch(const std::exception& e){failed=true;ours=false;REXLOG_ERROR("Advanced Forge release reset failed: {}",e.what());}
 }
 {
  struct Scope {
   std::optional<uint32_t> previous=nativePhasedReleaseDatum;
   Scope(bool active,uint32_t held){
    nativePhasedReleaseDatum.reset();
    if(!active)return;
    const auto it=physicsObjects.find(held);
    if(it!=physicsObjects.end()&&ModeOf(it->second)==forge::PhysicsMode::Phased)nativePhasedReleaseDatum=held;
   }
   ~Scope(){nativePhasedReleaseDatum=previous;}
  } scope(ours&&placement,heldBefore);
  __imp__sub_8227FDF8(ctx,base);
 }
 if(!ours||U(base,engine+0xe198+index*4)!=kNone)return;
 ClearPlayerAnchors(releasePlayer);
 if(skipPlacement)return;
 // Spec 04 4.5: select and transition the released (unheld) object.
 try{
  auto it=physicsObjects.find(heldBefore);
  if(it==physicsObjects.end()||!PhysicsValid(base,heldBefore,it->second))throw std::runtime_error("Released object lost its physics record");
  if(PhysicsHeld(base,heldBefore))throw std::runtime_error("Release precedes ownership clear");
  SelectAndTransition(ctx,base,heldBefore,it->second,ModeOf(it->second),nullptr);
  it->second.releasedPhysics=true;
  lastReleased=heldBefore;
  if(Tracing()){
   const auto origin=NativeObjectOrigin(ctx,base,heldBefore);
   const auto orientation=NativeObjectOrientation(ctx,base,heldBefore);
   REXLOG_INFO("Advanced Forge released: {:08X} origin {},{},{} forward {},{},{}",heldBefore,origin[0],origin[1],origin[2],orientation[0][0],orientation[0][1],orientation[0][2]);
  }
  it->second.settlePlayer=ModeOf(it->second)==forge::PhysicsMode::Phased?kNone:releasePlayer;
 }catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge release physics failed: {}",e.what());}
}
// Physics capture before Halo 3's grab changes the body, and the settle
// dequeue transition (Halo 3's counterpart of the settle processor).
extern "C" void __imp__sub_8227E770(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227E770){
 const auto datum=ctx.r3.u32;
 const auto grab=nativeGrabTransaction;
 // Inside our grab, the complete transition follows; skip Halo 3's forced rebuild.
 if(grab&&grab->selected&&grab->error.empty()&&grab->datum==datum&&(ctx.r4.u32&255)==1&&ctx.lr==0x8227E9F0)return;
 const bool world=!restoringPhysics&&!failed&&PhysicsWorld(ctx,base);
 if(world&&ctx.lr==0x82283D50&&(ctx.r4.u32&255)==0){
  auto it=physicsObjects.find(datum);
  if(it!=physicsObjects.end()&&it->second.releasedPhysics&&PhysicsValid(base,datum,it->second)){
   try{
    SelectAndTransition(ctx,base,datum,it->second,ModeOf(it->second),nullptr);
    // Spec 04 4.5 step 4 / 4.6: a dequeued object is checked once settled.
    if(it->second.settlePlayer!=kNone){
     const bool valid=NativePlacementValid(ctx,base,datum);
     if(Tracing())REXLOG_INFO("Advanced Forge settle check: {:08X} valid {} fully outside {}",datum,valid,NativeObjectFullyOutside(ctx,base,datum));
     if(!valid)settledInvalid.push_back(datum);
    }
   }catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge settle transition failed: {}",e.what());}
   return;
  }
 }
 if(world&&(ctx.r4.u32&255)==1){
  const auto pointer=ObjectPointer(base,physicsHeaders,datum);
  const auto definition=pointer?TagDefinition(base,U(base,pointer)):0;
  if(pointer&&SceneryType(ObjectType(base,datum))&&definition&&!(H(base,definition+2)&(1u<<11))&&
     U(base,pointer+0x10)==kNone&&(U(base,pointer+0xac)&kConnected))
   CapturePhysics(base,datum,pointer);
 }
 __imp__sub_8227E770(ctx,base);
 // Halo 3 may reset Forge physics on its own; our selected state stays authoritative.
 if(world){
  auto it=physicsObjects.find(datum);
  if(it!=physicsObjects.end()&&PhysicsValid(base,datum,it->second)){
   auto* holder=OwnedSceneryEditor(datum);
   if(holder||it->second.releasedPhysics){
    try{SelectAndTransition(ctx,base,datum,it->second,ModeOf(it->second),holder);}
    catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge physics reapply failed: {}",e.what());}
   }
  }
 }
}
// Monitor teardown before the mode change commits.
extern "C" void __imp__sub_822843A8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_822843A8){
 const auto player=ctx.r3.u32;
 bool owned=false;
 if(player!=kNone&&(player&65535)<nativeEditors.size()){
  const auto& slot=nativeEditors[player&65535];
  owned=slot.player==player&&slot.editor&&slot.ownsMonitorContact;
 }
 __imp__sub_822843A8(ctx,base);
 if((ctx.r3.u32&255)&&owned)completedMonitorExitPlayer=player;
}
// Leaving edit mode: restore authored Halo 3 physics.
extern "C" void __imp__sub_82280720(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280720){
 const bool requestedPlay=ctx.r5.u32==1;
 struct ExitScope {std::optional<uint32_t> prior=completedMonitorExitPlayer;ExitScope(){completedMonitorExitPlayer.reset();}~ExitScope(){completedMonitorExitPlayer=prior;}} scope;
 __imp__sub_82280720(ctx,base);
 if(requestedPlay&&!physicsObjects.empty()){
  auto maintenance=ctx;
  if(PhysicsWorld(maintenance,base)&&H(base,physicsEngine+57748)==0)RestorePhysics(maintenance,base);
 }
}
// Halo 3's deferred update (settle queue). Invalidly settled objects are
// deleted afterwards (spec 04 4.6, user decision 3).
extern "C" void __imp__sub_82283A30(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82283A30){
 const bool world=PhysicsWorld(ctx,base);
 __imp__sub_82283A30(ctx,base);
 if(!world||restoringPhysics)return;
 auto invalid=std::move(settledInvalid);settledInvalid.clear();
 for(const auto datum:invalid){
  const auto it=physicsObjects.find(datum);
  const auto pointer=ObjectPointer(base,physicsHeaders,datum);
  if(it==physicsObjects.end()||!pointer||!PhysicsValid(base,datum,it->second)||PhysicsHeld(base,datum))continue;
  const auto slot=H(base,pointer+24);
  if(slot>=640||U(base,physicsEngine+0x1ac+slot*0x54)!=datum)continue;
  const auto flags=H(base,physicsEngine+0x1a8+slot*0x54);
  if(!(flags&1)||(flags&0x20))continue;
  auto removal=ctx;removal.r3.u32=it->second.settlePlayer;removal.r4.u32=slot;
  __imp__sub_822802D0(removal,base);
  REXLOG_INFO("Advanced Forge deleted an object that settled outside the playable space: {:08X}",datum);
 }
 for(auto it=physicsObjects.begin();it!=physicsObjects.end();){
  if(!PhysicsValid(base,it->first,it->second))it=physicsObjects.erase(it);else ++it;
 }
}
// Render view rectangles per local observer.
extern "C" void __imp__sub_821582B0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821582B0){
 const auto renderView=ctx.r3.u32,localView=ctx.r7.u32;
 __imp__sub_821582B0(ctx,base);
 if(localView>=anchorViewports.size()||!Ptr(renderView)||uint64_t(renderView)+10720>=0xc0000000ULL)return;
 AnchorViewport viewport;viewport.renderView=renderView;viewport.updated=std::chrono::steady_clock::now();
 const int width=int16_t(U(base,0x8275a248)),height=int16_t(U(base,0x8275a24c));
 const int left=int16_t(H(base,renderView+68)),top=int16_t(H(base,renderView+70));
 const int viewWidth=int16_t(H(base,renderView+58)),viewHeight=int16_t(H(base,renderView+56));
 if(width>0&&height>0&&left>=0&&top>=0&&viewWidth>0&&viewHeight>0&&left+viewWidth<=width&&top+viewHeight<=height){
  viewport.rect={float(left)/width,float(top)/height,float(left+viewWidth)/width,float(top+viewHeight)/height};
  viewport.valid=true;
 }
 std::lock_guard lock(anchorMutex);anchorViewports[localView]=viewport;
}
static void DiscardFailedNativeMarkerStream(uint8_t* base,uint32_t state){
 if(!Ptr(state)||uint64_t(state)+10942>=0xc0000000ULL||state!=U(base,0x828e66f0)||!(base[state+10941]&0x20))return;
 if(auto* renderer=markerRenderer.load())renderer->DiscardQueuedSceneMarkers();
}
extern "C" void __imp__sub_82182D90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82182D90){const auto state=ctx.r3.u32;__imp__sub_82182D90(ctx,base);DiscardFailedNativeMarkerStream(base,state);}
extern "C" void __imp__sub_825C13B8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_825C13B8){const auto state=ctx.r3.u32;__imp__sub_825C13B8(ctx,base);DiscardFailedNativeMarkerStream(base,state);}
// Camera constants: queue this view's markers in draw order.
extern "C" void __imp__sub_82162398(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82157688(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82162398){
 const auto camera=ctx.r3.u32,projection=ctx.r4.u32;
 __imp__sub_82162398(ctx,base);
 auto* renderer=markerRenderer.load();if(!renderer)return;
 const auto state=U(base,0x828e66f0);
 if(!Ptr(state)||uint64_t(state)+14924>=0xc0000000ULL)return;
 if(base[state+10941]&0x20){renderer->DiscardQueuedSceneMarkers();return;}
 std::shared_ptr<const rex::graphics::SceneMarkerMaterial> material;
 if(markerMaterial.valid()&&markerMaterial.wait_for(std::chrono::seconds(0))==std::future_status::ready)material=markerMaterial.get();
 rex::graphics::SceneMarkers markers;markers.local_view=UINT32_MAX;
 {
  std::lock_guard lock(anchorMutex);
  const auto now=std::chrono::steady_clock::now();
  for(uint32_t i=0;i<anchorViewports.size();++i){
   const auto& viewport=anchorViewports[i];const auto& view=anchorViews[i];
   if(!viewport.valid||camera!=viewport.renderView+4||projection!=viewport.renderView+140||
      now-viewport.updated>=std::chrono::milliseconds(250))continue;
   markers.local_view=i;markers.output_rect=viewport.rect;
   markers.camera=Vec(base,state+2032);
   for(unsigned j=0;j<16;++j)markers.world_to_clip[j]=F(base,state+1920+j*4);
   if(enabled.load()&&material&&now-view.updated<std::chrono::milliseconds(250)){
    markers.material=material;markers.time=view.time;
    for(const auto& anchor:view.anchors){
     if(markers.points.size()>=64)break;
     markers.points.push_back({anchor.position,{anchor.seed,anchor.shown,0.f,forge::kMarkerHalfSize}});
    }
   }
   break;
  }
 }
 // Only a player's own view carries markers. Other camera passes in the same
 // frame (weapon, effects) must not replace that view's snapshot.
 if(markers.local_view==UINT32_MAX)return;
 auto cursor=U(base,state+48),limit=U(base,state+52);
 if(uint64_t(cursor)+20>=limit){
  auto allocation=ctx;allocation.r3.u64=state;
  __imp__sub_82157688(allocation,base);
  cursor=U(base,state+48);limit=U(base,state+52);
 }
 if(base[state+10941]&0x20){renderer->DiscardQueuedSceneMarkers();return;}
 if(!Ptr(cursor)||(cursor&3)||uint64_t(cursor)+20>=limit)return;
 if(Tracing()){
  static auto last=std::chrono::steady_clock::now();
  const auto now=std::chrono::steady_clock::now();
  if(now-last>std::chrono::seconds(2)){
   last=now;
   size_t anchors=0;bool fresh=false;
   {std::lock_guard lock(anchorMutex);for(const auto& v:anchorViews){anchors+=v.anchors.size();fresh|=now-v.updated<std::chrono::milliseconds(250);}}
   REXLOG_INFO("Advanced Forge markers: view {} points {} material {} anchors {} fresh {} viewport {} camera {:08X} projection {:08X} renderView {:08X} age {}ms",
    markers.local_view,markers.points.size(),bool(material),anchors,fresh,anchorViewports[0].valid,camera,projection,anchorViewports[0].renderView,
    std::chrono::duration_cast<std::chrono::milliseconds>(now-anchorViewports[0].updated).count());
  }
 }
 const auto token=renderer->QueueSceneMarkers(std::move(markers));
 const uint32_t words[]={0xc0031000,rex::graphics::kSceneMarkerPacketSignature,rex::graphics::kSceneMarkerPacketVersion,uint32_t(token>>32),uint32_t(token)};
 for(auto word:words){cursor+=4;PutU(base,cursor,word);}
 PutU(base,state+48,cursor);
}
// Aim ray (spec 03 2.2-2.3) in Halo 3 Forge's targeting call.
extern "C" void __imp__sub_82281268(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82281268){
 const auto player=ctx.r3.u32;
 const bool forgeTick=ctx.lr==0x82281B0C;
 const auto targetOutput=ctx.r4.u32;
 auto rayContext=ctx;
 __imp__sub_82281268(ctx,base);
 if(!forgeTick||!enabled.load()||failed||player==kNone||(player&65535)>=16||!PhysicsWorld(rayContext,base))return;
 try{
  const auto contact=PlayerContact(base,U(base,rayContext.r13.u32),player,false);
  if(!contact)return;
  const auto monitor=U(base,contact->record+40);
  const auto unit=ObjectPointer(base,physicsHeaders,monitor);
  if(!unit||ObjectType(base,monitor)!=0||U(base,unit+16)!=kNone||U(base,unit+380)!=player)return;
  const auto variant=U(base,physicsEngine+0xe198+(player&65535)*4);
  uint32_t held=kNone;
  if(variant!=kNone){
   if(variant>=640)throw std::runtime_error("Invalid holder slot");
   held=U(base,physicsEngine+0x1ac+variant*0x54);
   const auto object=ObjectPointer(base,physicsHeaders,held);
   if(!object||!SceneryType(ObjectType(base,held)))return;
   const auto& owner=nativeEditors[player&65535];
   if(owner.player!=player||!owner.editor||!owner.ownsMonitorContact)return;
  }
  auto& slot=NativeEditor(player);
  auto& e=*slot.editor;
  if(e.held!=held)throw std::runtime_error("Aim ray disagrees with the native holder");
  const auto origin=NativeSelectionOrigin(rayContext,base,monitor);
  V direction=NativeMonitorView(base,monitor);forge::Normalize(direction);
  const float range=forge::AimRange(e);
  const V end=forge::Add(origin,forge::Mul(direction,range));
  const auto hit=NativeRay(rayContext,base,kSelectionMask,origin,forge::Mul(direction,range),NativeSelectionRayExclusions(rayContext,base,held));
  e.aimPoint=hit?hit->point:end;
  uint32_t target=kNone;
  if(hit&&hit->category==4&&hit->datum!=kNone){
   uint32_t candidate=NativeRoot(base,hit->datum);
   const auto object=ObjectPointer(base,physicsHeaders,candidate);
   // Forge variant slot and the allowed kinds (spec 03 2.3 step 4).
   const auto type=ObjectType(base,candidate);
   const bool kind=type<=3||type==6||type==7||type==8||type==10;
   if(object&&H(base,object+24)!=0xffff&&kind)target=candidate;
  }
  e.aimed=target;
  const auto nativeTarget=targetOutput?U(base,targetOutput):kNone;
  const auto isScenery=[base](uint32_t datum){return ObjectPointer(base,physicsHeaders,datum)&&SceneryType(ObjectType(base,datum));};
  // Scenery targeting follows the spec; weapons and vehicles stay with Halo 3.
  if(isScenery(target)||(target==kNone&&isScenery(nativeTarget))){
   const auto index=player&65535;
   PutVec(base,physicsEngine+57880+index*12,e.aimPoint);
   if(hit)PutVec(base,physicsEngine+58072+index*12,hit->normal);
   else std::memcpy(base+physicsEngine+58072+index*12,base+0x8203b0e0,12);
   if(targetOutput)PutU(base,targetOutput,target);
   ctx.r3.u32=target!=kNone?1:0;
  }
 }catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge aim ray failed: {}",e.what());}
}
// Forge initializer: new session, new editors (spec 03 1.2).
extern "C" void __imp__sub_82280D80(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280D80){
 __imp__sub_82280D80(ctx,base);
 ClearNativeEditors();controllerAttachments.clear();physicsObjects.clear();settledInvalid.clear();ClearAnchorWorld();
}
// Variant reset event: reset every editor (spec 03 1.2).
extern "C" void __imp__sub_82280F98(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280F98){
 __imp__sub_82280F98(ctx,base);
 if(!enabled.load()||failed)return;
 try{
  if(!PhysicsWorld(ctx,base))return;
  for(unsigned i=0;i<nativeEditors.size();++i){
   auto& slot=nativeEditors[i];
   if(!slot.editor)continue;
   const auto selected=slot.editor->held;
   const auto nativeSlot=U(base,physicsEngine+0xe198+i*4);
   forge::InitializeEditor(*slot.editor);
   if(selected!=kNone&&nativeSlot<640&&U(base,physicsEngine+0x1ac+nativeSlot*0x54)==selected){
    const auto object=ObjectPointer(base,physicsHeaders,selected);
    if(object&&SceneryType(ObjectType(base,selected))){
     PutU(base,physicsEngine+0xe198+i*4,kNone);
     PutF(base,physicsEngine+0xe1d8+i*4,slot.editor->holdDistance);
    }
   }
   slot.ownsMonitorContact=false;slot.contactMonitor=kNone;slot.shown.clear();
   ClearPlayerAnchors(slot.player);
  }
  controllerAttachments.clear();
 }catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge editor reset failed: {}",e.what());}
}
// State replacement / history lifecycle.
extern "C" void __imp__sub_821ABAB0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821ABAB0){
 __imp__sub_821ABAB0(ctx,base);
 {std::lock_guard lock(nativeHistoryMutex);nativeHistoryPhases={};}
 ClearNativeEditors();controllerAttachments.clear();physicsObjects.clear();settledInvalid.clear();
 for(auto& contact:nativePlayerContacts)contact.normalKnown=false;
 ClearAnchorWorld();
}
extern "C" void __imp__sub_82344AE0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344AE0){__imp__sub_82344AE0(ctx,base);std::lock_guard lock(nativeHistoryMutex);nativeHistoryPhases={};}
extern "C" void __imp__sub_82344A88(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344A88){__imp__sub_82344A88(ctx,base);std::lock_guard lock(nativeHistoryMutex);nativeHistoryPhases={};}
extern "C" void __imp__sub_82344AF8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344AF8){__imp__sub_82344AF8(ctx,base);std::lock_guard lock(nativeHistoryMutex);nativeHistoryPhases={};}
extern "C" void __imp__sub_821224C0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821224C0){
 const auto datum=ctx.r3.u32,tls=U(base,ctx.r13.u32);
 const auto history=Ptr(tls)?U(base,tls+264):0;
 uint32_t count=0,index=32,lastDatum=kNone;
 if(Ptr(history)&&uint64_t(history)+9864<0xc0000000ULL){
  count=U(base,history+9856);
  if(count&&count<=32){
   lastDatum=U(base,history+9728+(count-1)*4);
   for(uint32_t i=0;i<count;++i)if(U(base,history+9728+i*4)==datum){index=i;break;}
  }
 }
 __imp__sub_821224C0(ctx,base);
 if(index>=32||U(base,history+9856)!=count-1||U(base,history+9728+index*4)!=lastDatum)return;
 std::lock_guard lock(nativeHistoryMutex);
 for(const auto slot:{index,count-1})if(nativeHistoryPhases[slot].identity.history==history)nativeHistoryPhases[slot]={};
}
extern "C" void __imp__sub_82345A80(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82345A80){
 const auto caller=ctx.lr;
 __imp__sub_82345A80(ctx,base);
 if(caller==0x82344DCC&&nativeFirstHistorySampled)*nativeFirstHistorySampled=(ctx.r3.u32&255)!=0;
}
extern "C" void __imp__sub_82344D50(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344D50){
 const auto datum=ctx.r3.u32,index=ctx.r4.u32;
 bool sampled=false;
 {
  struct Scope {bool* prior=nativeFirstHistorySampled;explicit Scope(bool& v){nativeFirstHistorySampled=&v;}~Scope(){nativeFirstHistorySampled=prior;}} scope(sampled);
  __imp__sub_82344D50(ctx,base);
 }
 RecordNativeHistoryPhase(ctx,base,datum,index,true,sampled);
}
extern "C" void __imp__sub_82344E90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344E90){
 const auto datum=ctx.r3.u32,index=ctx.r4.u32;
 __imp__sub_82344E90(ctx,base);
 RecordNativeHistoryPhase(ctx,base,datum,index,false,true);
}
// Detach velocity inheritance (spec 02 5 steps 11-12) inside our grab.
REX_HOOK_RAW(sub_820F29C8){
 auto* attachment=nativeDetachAttachment;
 auto* grab=nativeGrabTransaction;
 if(ctx.lr==0x823318CC&&attachment&&attachment->deferVelocity&&grab&&grab->datum==attachment->datum&&grab->error.empty()&&ctx.r3.u32==attachment->datum){
  try{
   if(attachment->fallbackVelocity)throw std::runtime_error("Repeated deferred detach velocity");
   attachment->fallbackVelocity=std::array<V,2>{Vec(base,ctx.r4.u32),Vec(base,ctx.r5.u32)};
   return;
  }catch(const std::exception& e){grab->error=e.what();attachment->fallbackVelocity.reset();}
 }
 __imp__sub_820F29C8(ctx,base);
}
namespace advanced_forge { namespace {
bool ApplyNativeDetachPointVelocity(PPCContext& ctx,uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||U(base,object+16)!=kNone)throw std::runtime_error("Detach did not produce an unparented object");
 if(!(U(base,object+172)&8))return false;
 auto resolve=ctx;resolve.r3.u32=datum;
 __imp__sub_8211DE00(resolve,base);
 const auto index=resolve.r3.u32;
 if(index==kNone)return false;
 const auto tls=U(base,ctx.r13.u32),history=Ptr(tls)?U(base,tls+264):0;
 if(index>=32||!Ptr(history)||index>=U(base,history+9856))throw std::runtime_error("Invalid detach history association");
 const auto root=U(base,history+9728+index*4);
 const auto phase=NativeHistoryFirstBank(ctx,base,root,index);
 const auto point=NativePhysicsPoint(ctx,base,datum);
 Frame f(ctx,base,0x100);
 const auto position=f.at,linear=position+12,angular=linear+12;
 PutVec(base,position,point);
 f.call.r3.u32=datum;f.call.r4.u32=position;f.call.r5.u32=linear;f.call.r6.u32=angular;f.call.r7.u32=1;f.call.r8.u32=phase.value_or(false)?1:0;
 __imp__sub_820AFCF8(f.call,base);
 if(!(f.call.r3.u32&255))return false;
 if(!phase)throw std::runtime_error("Detached object history phase not observed");
 auto apply=f.call;apply.r3.u32=datum;apply.r4.u32=linear;apply.r5.u32=angular;
 __imp__sub_820F29C8(apply,base);
 return true;
}
void ApplyNativeDetachFallback(PPCContext& ctx,uint8_t* base,const NativeDetachAttachment& attachment){
 if(!attachment.fallbackVelocity||ObjectPointer(base,physicsHeaders,attachment.datum)!=attachment.object)
  throw std::runtime_error("Detached object lost its deferred velocity target");
 Frame f(ctx,base,0x100);
 PutVec(base,f.at,(*attachment.fallbackVelocity)[0]);PutVec(base,f.at+12,(*attachment.fallbackVelocity)[1]);
 f.call.r3.u32=attachment.datum;f.call.r4.u32=f.at;f.call.r5.u32=f.at+12;
 __imp__sub_820F29C8(f.call,base);
}
}}
extern "C" void __imp__sub_823317C0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_823317C0){
 const auto caller=ctx.lr;
 const auto datum=ctx.r3.u32;
 const auto grab=nativeGrabTransaction;
 std::optional<NativeDetachAttachment> attachment;
 if(enabled.load()&&!failed&&PhysicsWorld(ctx,base)){
  const auto object=ObjectPointer(base,physicsHeaders,datum);
  if(object&&SceneryType(ObjectType(base,datum))&&U(base,object+16)!=kNone)
   attachment=NativeDetachAttachment{datum,object,U(base,object+16),int8_t(base[object+20])};
 }
 if(attachment){
  attachment->deferVelocity=caller==0x82120A18&&grab&&grab->datum==datum&&grab->error.empty();
  attachment->rebuildAfterUnlink=(U(base,attachment->object+172)&kConnected)!=0;
 }
 {
  struct Scope {NativeDetachAttachment* prior=nativeDetachAttachment;explicit Scope(NativeDetachAttachment* v){nativeDetachAttachment=v;}~Scope(){nativeDetachAttachment=prior;}} scope(attachment?&*attachment:nullptr);
  __imp__sub_823317C0(ctx,base);
 }
 if(!attachment||!attachment->fallbackVelocity)return;
 bool applied=false;
 if(grab&&grab->error.empty()&&!failed&&enabled.load()){
  try{applied=ApplyNativeDetachPointVelocity(ctx,base,datum);}catch(const std::exception& e){grab->error=e.what();}
 }
 if(!applied){
  if(grab&&grab->error.empty()&&!failed&&enabled.load()){
   try{attachment->fallbackVelocity=NativeObjectVelocities(ctx,base,attachment->parent);}catch(const std::exception& e){grab->error=e.what();}
  }
  try{ApplyNativeDetachFallback(ctx,base,*attachment);}
  catch(const std::exception& e){if(grab)grab->error=e.what();else{failed=true;REXLOG_ERROR("Deferred detach velocity failed: {}",e.what());}}
 }
}
// Grab detaches a child whose root is a valid object (spec 03 3.2 step 2).
extern "C" void __imp__sub_82345288(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82345288){
 const auto caller=ctx.lr;
 const auto root=ctx.r3.u32,flag=ctx.r4.u32;
 const auto grab=nativeGrabTransaction;
 __imp__sub_82345288(ctx,base);
 if(caller!=0x822801F8||flag||!grab||!grab->error.empty()||failed||!enabled.load()||ctx.r27.u32!=grab->datum||ctx.r23.u32!=grab->player||
    root==grab->datum||root==kNone)return;
 const auto object=ObjectPointer(base,physicsHeaders,grab->datum);
 if(!object||U(base,object+16)==kNone||!ObjectPointer(base,physicsHeaders,root))return;
 ctx.r3.u32=1;
}
// Grab dequeue: the selection stage runs once Halo 3 has committed ownership.
extern "C" void __imp__sub_82283B90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82283B90){
 auto grab=nativeGrabTransaction;
 if(grab&&grab->error.empty()&&ctx.lr==0x822802A8&&ctx.r3.u32==grab->datum&&ctx.r4.u32==kNone){
  try{
   const auto slot=U(base,physicsEngine+0xe198+(grab->player&65535)*4);
   if(slot>=640||U(base,physicsEngine+0x1ac+slot*0x54)!=grab->datum)throw std::runtime_error("Native grab did not commit ownership");
   SelectNativeHeldEditor(ctx,base,grab->player,grab->datum);
   grab->selected=true;
  }catch(const std::exception& e){grab->error=e.what();}
 }
 __imp__sub_82283B90(ctx,base);
}
// Creation: requested point pulled toward the player (spec 03 5.2 steps 3-4);
// the clearance search is Halo 3's own (overview; spec 03 5.3 data PENDING).
extern "C" void __imp__sub_8227F2A0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227F2A0){
 NativeCreatePlacement creation{ctx.r3.u32,ctx.r4.u32,ctx.r5.u32!=0,{}};
 NativeCreatePlacementScope scope(&creation);
 __imp__sub_8227F2A0(ctx,base);
}
extern "C" void __imp__sub_822836D8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_822836D8){
 auto creation=nativeCreatePlacement;
 if(creation&&creation->hasPoint&&ctx.lr==0x8227F344&&creation->tag==ctx.r3.u32&&creation->player!=kNone&&
    (creation->player&65535)<16&&enabled.load()&&!failed&&PhysicsWorld(ctx,base)){
  const auto definition=TagDefinition(base,creation->tag);
  const auto type=definition?H(base,definition):0xffff;
  if(SceneryType(uint8_t(type))&&type<256&&!(H(base,definition+2)&(1u<<11))){
   try{
    if(!Ptr(ctx.r4.u32))throw std::runtime_error("Invalid creation point");
    std::optional<V> monitor;
    if(ctx.r5.u32!=kNone)monitor=NativePhysicsPoint(ctx,base,ctx.r5.u32);
    float radius=F(base,definition+4);
    const auto point=forge::PullSpawnPoint(Vec(base,ctx.r4.u32),monitor,radius);
    if(radius<0.0001f)radius=1.f;
    PutVec(base,ctx.r4.u32,point);
    creation->radius=radius;
   }catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge creation placement failed: {}",e.what());}
  }
 }
 __imp__sub_822836D8(ctx,base);
}
extern "C" void __imp__sub_822835E0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_822835E0){
 const auto creation=nativeCreatePlacement;
 const bool overrideRadius=creation&&creation->radius&&ctx.lr==0x822836FC&&ctx.r3.u32==creation->tag;
 __imp__sub_822835E0(ctx,base);
 if(overrideRadius)ctx.f1.f64=*creation->radius;
}
// Grab (and creation's grab): Halo 3 ownership, then spec 03 3.2.
extern "C" void __imp__sub_8227E810(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227E810){
 const auto player=ctx.r3.u32,slot=ctx.r4.u32;
 std::optional<NativeGrabTransaction> grab;
 if(enabled.load()&&!failed&&slot<640&&player!=kNone&&(player&65535)<16&&PhysicsWorld(ctx,base)){
  const auto datum=U(base,physicsEngine+0x1ac+slot*0x54);
  const auto pointer=ObjectPointer(base,physicsHeaders,datum);
  const auto definition=pointer?TagDefinition(base,U(base,pointer)):0;
  if(pointer&&SceneryType(ObjectType(base,datum))&&definition&&!(H(base,definition+2)&(1u<<11))){
   try{
    if(nativeGrabTransaction)throw std::runtime_error("Nested grab");
    CapturePhysics(base,datum,pointer);
    grab=NativeGrabTransaction{player,datum};
   }catch(const std::exception& e){failed=true;REXLOG_ERROR("Advanced Forge grab preparation failed: {}",e.what());}
  }
 }
 {
  NativeGrabTransactionScope scope(grab?&*grab:nullptr);
  __imp__sub_8227E810(ctx,base);
 }
 if(!grab)return;
 if(!grab->error.empty()){Fail(ctx,base,"grab selection",std::runtime_error(grab->error));return;}
 if(!grab->selected)return;
 try{
  auto& slotRef=nativeEditors[player&65535];
  if(slotRef.player!=player||!slotRef.editor||slotRef.editor->held!=grab->datum)throw std::runtime_error("Grab lacks its selection");
  auto& object=physicsObjects.at(grab->datum);
  object.releasedPhysics=false;object.settlePlayer=kNone;
  // Physics state for a held object (spec 03 3.2 step 6).
  SelectAndTransition(ctx,base,grab->datum,object,ModeOf(object),&*slotRef.editor);
  const auto world=NativeSelectionWorld(ctx,base,player);
  if(world.monitor==kNone)throw std::runtime_error("Grab without a monitor");
  // Pose, distance and held point (steps 7-10).
  forge::GrabInput g;
  const auto pointer=ObjectPointer(base,physicsHeaders,grab->datum);
  const auto instance=NativePhysicsInstance(base,pointer);
  g.hasBodies=instance&&BodyCount(base,instance)>0;
  if(g.hasBodies){
   int selected=int8_t(base[instance+12]);
   if(selected>=0&&uint32_t(selected)<BodyCount(base,instance))g.objectPose=forge::Pose::Unpack(NativeSceneryBodyPose(ctx,base,grab->datum,uint32_t(selected)));
   else{
    Frame f(ctx,base,0x100);f.call.r3.u32=grab->datum;f.call.r4.u32=f.at;__imp__sub_820D8FA0(f.call,base);
    std::array<float,13> v;for(unsigned i=0;i<13;++i)v[i]=F(base,f.at+i*4);
    g.objectPose=forge::Pose::Unpack(v);
   }
   g.bounds=NativeVariantBounds(base);
   g.monitorPoint=NativePhysicsPoint(ctx,base,world.monitor);
   g.monitorForward=NativeObjectOrientation(ctx,base,world.monitor)[0];
   g.runtimeRadius=RuntimeRadius(base,pointer);
   g.heldPhysicsPoint=NativePhysicsPoint(ctx,base,grab->datum);
  }
  if(forge::InitializeGrab(*slotRef.editor,slotRef.input,g))
   PutF(base,physicsEngine+0xe1d8+(player&65535)*4,slotRef.editor->holdDistance);
  // Diagnostic placement for unattended tests: offset from the last dropped piece.
  const auto testOffset=REXCVAR_GET(halo3mp_advanced_forge_test_offset);
  if(!testOffset.empty()&&Tracing()&&lastReleased!=kNone&&lastReleased!=grab->datum&&ObjectPointer(base,physicsHeaders,lastReleased)){
   float d[3]{};
   if(std::sscanf(testOffset.c_str(),"%f,%f,%f",&d[0],&d[1],&d[2])==3){
    const auto reference=forge::Pose::Unpack(NativeSceneryBodyPose(ctx,base,lastReleased,0));
    auto pose=reference;
    pose.position=forge::Apply(reference,{d[0],d[1],d[2]});
    slotRef.editor->target=pose;
    // Move the piece itself there (Halo 3's object pose setter), so the held
    // update starts from this pose rather than leading toward it.
    Frame f(ctx,base,0x100);
    PutVec(base,f.at,pose.position);PutVec(base,f.at+12,pose.forward);PutVec(base,f.at+24,pose.up);
    f.call.r3.u32=grab->datum;f.call.r4.u32=f.at;f.call.r5.u32=f.at+12;f.call.r6.u32=f.at+24;f.call.r7.u32=0;f.call.r8.u32=0;
    __imp__sub_8232E8B8(f.call,base);
    REXLOG_INFO("Advanced Forge test placement: {:08X} beside {:08X} at {},{},{}",grab->datum,lastReleased,pose.position[0],pose.position[1],pose.position[2]);
   }
  }
  const auto owner=ResolveNativeSceneryOwner(ctx,base,player,grab->datum,true);
  slotRef.contactMonitor=owner.monitor;
  slotRef.ownsMonitorContact=true;
  if(Tracing()){const auto b=NativeVariantBounds(base);REXLOG_INFO("Advanced Forge bounds: X {}..{} Y {}..{} Z {}..{}",b[0],b[1],b[2],b[3],b[4],b[5]);}
  if(Tracing()){
   std::string probes;
   for(const V& p:{V{50,54,16},V{50,54,-30},V{50,54,300},V{50,54,1100},V{2000,54,16},V{-6000,-6000,16},V{5000,5000,1000}})
    probes+=fmt::format(" ({},{},{})={}",p[0],p[1],p[2],NativePointOutsideWorld(ctx,base,p));
   REXLOG_INFO("Advanced Forge outside-world probes:{}",probes);
  }
  if(Tracing())REXLOG_INFO("Advanced Forge grab: {:08X} tag {:08X} type {} map {} distance {} magnets {}",grab->datum,U(base,pointer),ObjectType(base,grab->datum),physicsMap,slotRef.editor->holdDistance,MagnetTableOf(base,grab->datum)!=nullptr);
 }catch(const std::exception& e){Fail(ctx,base,"grab initialization",e);}
}
// Halo 3 Forge per-player update with the Advanced Forge held stage.
REX_HOOK_RAW(sub_82281A98){
 RunNativeForgeTick(ctx,base,DispatchHeldStage);
}
#include "advanced_forge_menu.inl"
extern "C" void __imp__sub_824F5D40(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_824F5D40){
 const auto screen=ctx.r3.u32;
 __imp__sub_824F5D40(ctx,base);
 try{AddEditorMenu(ctx,base,screen);}
 catch(const std::exception& e){Fail(ctx,base,"menu",e);}
}
// Keyframed request: override the motion array before Halo 3 builds bodies.
REX_HOOK_RAW(sub_82267DD8){
 const auto request=SceneryConstructionRequest(base,ctx.r3.u32);
 if(!request||!request->keyframed||!Ptr(ctx.r3.u32)||U(base,ctx.r3.u32+8)!=request->datum){__imp__sub_82267DD8(ctx,base);return;}
 if(!Ptr(ctx.r4.u32)||!Ptr(ctx.r8.u32))throw std::runtime_error("Invalid body creation descriptor");
 const auto phmo=U(base,ctx.r4.u32+72);
 if(!Ptr(phmo))throw std::runtime_error("Missing body physics model");
 const auto count=U(base,phmo+88),address=ctx.r8.u32;
 if(count>64)throw std::runtime_error("Body motion array exceeds native capacity");
 struct RestoreMotion {uint8_t* destination;std::vector<uint8_t> original;~RestoreMotion(){std::copy(original.begin(),original.end(),destination);}}
  restore{base+address,std::vector<uint8_t>(base+address,base+address+count)};
 std::fill_n(base+address,count,uint8_t(6));
 __imp__sub_82267DD8(ctx,base);
}
#undef AF_IMPORT
