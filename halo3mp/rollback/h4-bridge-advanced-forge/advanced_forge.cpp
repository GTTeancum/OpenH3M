#include "advanced_forge.h"
#include "pc_video_menu.h"
#include "forge_bridge.h"
#include "forge_coordinates.h"
#include "forge_physics.h"
#include "forge_overlay.h"
#include "scene_snapshot.h"
#include <rex/cvar.h>
#include <rex/filesystem.h>
#include <rex/hook.h>
#include <rex/system/function_dispatcher.h>
#include <rex/logging.h>
#include <rex/ui/imgui_dialog.h>
#include <rex/graphics/command_processor.h>
#include <imgui.h>
#include <atomic>
#include <bit>
#include <fstream>
#include <deque>
#include <mutex>
#include <unordered_map>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <sstream>
#include <chrono>
#include <algorithm>

REXCVAR_DEFINE_BOOL(halo3mp_advanced_forge,true,"Halo3MP","Automatic original Halo 4 magnets in offline Forge; false is a diagnostic override");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_data,"","Halo3MP","Directory containing private H4 inputs and isolated marker metadata");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_trace,"","Halo3MP","Optional private scene diagnostic path");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_test_position,"","Halo3MP","Diagnostic-only held drag request x,y,z; requires scene tracing and exclusive input replay");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_test_coordinates,"","Halo3MP","Diagnostic-only coordinate panel request x,y,z,yaw,pitch,roll; requires scene tracing and exclusive input replay");
REXCVAR_DEFINE_STRING(halo3mp_advanced_forge_test_physics,"","Halo3MP","Diagnostic-only physics sequence normal,fixed,phased; requires scene tracing and exclusive input replay");
extern "C" void __imp__sub_822837C8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_8232E8B8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82284078(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_821AA050(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_822802D0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_8232EB28(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_821CB8D8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82330B20(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_821CBB88(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820A9E58(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AA480(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AF448(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AF170(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AD3E0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AE5C0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820EA138(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AF6D0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AF7B0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AFA98(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AC960(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820F29C8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820AFCF8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_8211DE00(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820F2A78(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82651968(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_8265FD48(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_822385C8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820FFAB0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820D8FA0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820B1928(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820B04B0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820F6550(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820B06A0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82267DD8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_8227EB28(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_820B0B60(PPCContext& __restrict,uint8_t*);

namespace advanced_forge {
namespace {
struct ControlState {std::atomic<bool> enabled=true,showAnchors=true;std::atomic<unsigned> sensitivity=2;};
ControlState controlState;
CoordinateSession coordinates;
PhysicsSession physics;
std::atomic<rex::graphics::CommandProcessor*> markerRenderer=nullptr;
auto& enabled=controlState.enabled;
auto& sensitivity=controlState.sensitivity;
std::atomic<uint64_t> evaluations=0,snaps=0;
std::mutex statusMutex;
std::string status="Off";
struct AnchorView {
 uint32_t player=0xffffffff;
 AnchorCamera camera;
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
std::shared_ptr<const rex::graphics::SceneMarkerMaterial> markerMaterial;
void ClearAnchors(){std::lock_guard lock(anchorMutex);for(auto& view:anchorViews)view.anchors.clear();}
void ClearAnchorWorld(){
 {
  std::lock_guard lock(anchorMutex);
  for(auto& view:anchorViews)view=AnchorView{};
  for(auto& viewport:anchorViewports)viewport=AnchorViewport{};
 }
 // Old camera packets may still be in flight when the native world changes.
 // Invalidate host snapshots without touching backend resources on this thread.
 if(auto* renderer=markerRenderer.load())renderer->DiscardQueuedSceneMarkers();
}
void ClearPlayerAnchors(uint32_t player){std::lock_guard lock(anchorMutex);for(auto& view:anchorViews)if(view.player==player)view.anchors.clear();}
void Status(std::string s){std::lock_guard lock(statusMutex);status=std::move(s);}
struct Anchor {float p[3],q[4];};
struct Binding {bool fixed=false;float radius;std::vector<Anchor> anchors;std::vector<MarkerDefinition> definitions;};
std::unordered_map<uint64_t,Binding> bindings;
std::unique_ptr<Bridge> bridge;
bool failed=false;
// Final placement updates the variant before calling the live-pose routine.
// Evaluate once, before that update, so both consumers receive the same pose.
thread_local unsigned placementDepth=0;
// Only a synchronous Forge selection query may extend native exclusions.
// No H4 runtime object flags are written into native H3 objects.
thread_local const std::vector<uint32_t>* selectionRayExclusions=nullptr;
struct SelectionRayExclusionScope {
 explicit SelectionRayExclusionScope(const std::vector<uint32_t>& exclusions){
  if(selectionRayExclusions||exclusions.size()>64)
   throw std::runtime_error("Invalid or nested Forge selection exclusions");
  selectionRayExclusions=&exclusions;
 }
 ~SelectionRayExclusionScope(){selectionRayExclusions=nullptr;}
 SelectionRayExclusionScope(const SelectionRayExclusionScope&)=delete;
 SelectionRayExclusionScope& operator=(const SelectionRayExclusionScope&)=delete;
};
thread_local uint32_t diagnosticDatum=0xffffffff;
thread_local uint32_t syncCaller=0;
thread_local uint32_t fixedSnap=0xffffffff;
struct PlacementScope {
 PlacementScope(){++placementDepth;}
 ~PlacementScope(){--placementDepth;}
};
using V=std::array<float,3>;
struct HeldMovement {uint32_t player;V value;};
thread_local std::optional<HeldMovement> heldMovement;
// Native variant synchronization after the original H4 controller must not
// enter the legacy snap evaluator through822837C8 or its live-pose callback.
thread_local std::optional<uint32_t> nativePoseSyncDatum;
thread_local std::optional<uint32_t> nativePhasedReleaseDatum;
struct HeldMovementScope {
 std::optional<HeldMovement> prior=heldMovement;
 HeldMovementScope(){heldMovement.reset();}
 ~HeldMovementScope(){heldMovement=prior;}
};
using M=std::array<float,9>;
bool Ptr(uint32_t a){return a>=0x10000&&a<0xc0000000;}
uint32_t U(uint8_t* b,uint32_t a){uint32_t v;std::memcpy(&v,b+a,4);return std::byteswap(v);}
uint16_t H(uint8_t* b,uint32_t a){uint16_t v;std::memcpy(&v,b+a,2);return std::byteswap(v);}
float F(uint8_t* b,uint32_t a){return std::bit_cast<float>(U(b,a));}
V Vec(uint8_t* b,uint32_t a){return {F(b,a),F(b,a+4),F(b,a+8)};}
V Cross(V a,V b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
V Transform(const M& m,V v){return {m[0]*v[0]+m[3]*v[1]+m[6]*v[2],m[1]*v[0]+m[4]*v[1]+m[7]*v[2],m[2]*v[0]+m[5]*v[1]+m[8]*v[2]};}
M Basis(V f,V up){V l=Cross(up,f);return {f[0],f[1],f[2],l[0],l[1],l[2],up[0],up[1],up[2]};}
M Quaternion(const float* q){float x=q[0],y=q[1],z=q[2],w=q[3];return {1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)};}
void Put(Marker& m,unsigned off,float f){auto v=std::byteswap(std::bit_cast<uint32_t>(f));std::memcpy(m.data()+off,&v,4);}
Marker MakeMarker(const Anchor& a,const M& basis,V pos){
 Marker m{};M local=Quaternion(a.q),world{};
 for(unsigned i=0;i<3;++i){V v=Transform(basis,{local[i*3],local[i*3+1],local[i*3+2]});for(unsigned j=0;j<3;++j)world[i*3+j]=v[j];}
 V point=Transform(basis,{a.p[0],a.p[1],a.p[2]});
 Put(m,4,1);Put(m,0x38,1);
 for(unsigned i=0;i<9;++i){Put(m,8+i*4,local[i]);Put(m,0x3c+i*4,world[i]);}
 for(unsigned i=0;i<3;++i){Put(m,0x2c+i*4,a.p[i]);Put(m,0x60+i*4,point[i]+pos[i]);}
 return m;
}
void Load(){
 if(bridge||failed)return;
 auto root=REXCVAR_GET(halo3mp_advanced_forge_data);
 const auto adjacent=rex::filesystem::GetExecutableFolder()/"advanced-forge";
 const bool explicitPath=rex::cvar::GetFlagSource("halo3mp_advanced_forge_data")==rex::cvar::Source::kCommandLine&&!root.empty();
 // Prefer the inputs distributed with this build over an old persisted path.
 // Retain that path as a migration fallback for earlier local installations.
 if(root.empty()||(!explicitPath&&std::filesystem::is_regular_file(adjacent/"h4-image.bin")&&
    std::filesystem::is_regular_file(adjacent/"isolated/forge-globals.bin")&&
    std::filesystem::is_regular_file(adjacent/"isolated/camera-pitch-function.bin")&&
    std::filesystem::is_regular_file(adjacent/"isolated/camera-settings.bin")&&
    std::filesystem::is_regular_file(adjacent/"isolated/markers.bin")))root=adjacent.string();
 std::ifstream file(root+"/isolated/markers.bin",std::ios::binary);
 char magic[4];uint32_t count=0;file.read(magic,4);file.read(reinterpret_cast<char*>(&count),4);
 if(!file||!count||count>1024)throw std::runtime_error("Invalid marker bindings");
 // The live original lifecycle requires full marker records. Reject old
 // packs here instead of reporting Ready and failing on the first grab.
 if(std::memcmp(magic,"AFM3",4))
  throw std::runtime_error("Advanced Forge requires AFM3 marker metadata; rebuild its data pack");
 std::unordered_map<uint64_t,Binding> loadedBindings;
 for(unsigned i=0;i<count;++i){uint32_t mid,datum,n,fixed;Binding b;
  file.read(reinterpret_cast<char*>(&mid),4);file.read(reinterpret_cast<char*>(&datum),4);file.read(reinterpret_cast<char*>(&b.radius),4);file.read(reinterpret_cast<char*>(&n),4);
  file.read(reinterpret_cast<char*>(&fixed),4);b.fixed=fixed==1;
  if(!file||fixed>1||n>32||!n)throw std::runtime_error("Invalid marker count");
  b.anchors.resize(n);file.read(reinterpret_cast<char*>(b.anchors.data()),n*sizeof(Anchor));
  if(!file)throw std::runtime_error("Short marker data");
  b.definitions.resize(n);
  for(auto& definition:b.definitions)
   file.read(reinterpret_cast<char*>(definition.data()),definition.size());
  if(!file)throw std::runtime_error("Short original marker metadata");
  for(unsigned j=0;j<n;++j){
   const auto& definition=b.definitions[j];
   for(unsigned field=0;field<11;++field){
    uint32_t encoded;std::memcpy(&encoded,definition.data()+4+field*4,4);
    const auto bits=std::byteswap(encoded);
    if(!std::isfinite(std::bit_cast<float>(bits)))
     throw std::runtime_error("Nonfinite original marker metadata");
    if(field<7){
     const auto expected=field<3?b.anchors[j].p[field]:b.anchors[j].q[field-3];
     if(bits!=std::bit_cast<uint32_t>(expected))
      throw std::runtime_error("Marker pose disagrees with original metadata");
    }
   }
  }
  if(!std::isfinite(b.radius)||b.radius<=0)throw std::runtime_error("Invalid marker bounds");
  for(const auto& a:b.anchors){
   for(float v:a.p)if(!std::isfinite(v))throw std::runtime_error("Nonfinite marker position");
   float norm=0;for(float v:a.q){if(!std::isfinite(v))throw std::runtime_error("Nonfinite marker rotation");norm+=v*v;}
   if(std::abs(norm-1.f)>.001f)throw std::runtime_error("Invalid marker quaternion");
  }
  if(!loadedBindings.emplace((uint64_t(mid)<<32)|datum,std::move(b)).second)throw std::runtime_error("Duplicate marker binding");
 }
 if(file.peek()!=std::ifstream::traits_type::eof())throw std::runtime_error("Trailing marker data");
 std::ifstream materialFile(root+"/isolated/marker-material.bin",std::ios::binary);
 uint32_t header[5]{};materialFile.read(reinterpret_cast<char*>(header),sizeof(header));
 if(!materialFile||header[0]!=0x504d3448||header[1]!=3||header[2]<4||header[2]>1024*1024||
    header[3]<4||header[3]>1024*1024||!header[4]||header[4]>16*1024*1024||header[4]%4)
  throw std::runtime_error("Invalid precompiled original marker material");
 auto material=std::make_shared<rex::graphics::SceneMarkerMaterial>();
 for(unsigned i=0;i<2;++i){
  auto& program=material->programs[i];program.resize(header[2+i]);
  materialFile.read(reinterpret_cast<char*>(program.data()),program.size());
  if(!materialFile||std::memcmp(program.data(),"DXBC",4))throw std::runtime_error("Invalid marker program");
 }
 material->pixels.resize(header[4]);
 materialFile.read(reinterpret_cast<char*>(material->pixels.data()),header[4]);
 if(!materialFile||materialFile.peek()!=std::ifstream::traits_type::eof())throw std::runtime_error("Invalid marker material payload length");
 auto loadedBridge=std::make_unique<Bridge>(root+"/h4-image.bin",root+"/isolated/forge-globals.bin");
 bindings.swap(loadedBindings);
 bridge=std::move(loadedBridge);
 {std::lock_guard lock(anchorMutex);markerMaterial=std::move(material);}
 REXLOG_INFO("Advanced Forge inputs ready: {} ({} bindings)",root,bindings.size());
 Status("Ready: original Halo 4 magnets");
}
bool LocalForge(uint8_t* base,uint32_t game){
 // Same mode gates as retail 8227E810, before interpreting sandbox state.
 return Ptr(game)&&U(base,game+0x10)==2&&(U(base,game+0x238)&65535)==5&&base[game+0x14]==1;
}
constexpr uint32_t kFrozen=1u<<6,kConnected=1u<<7,kForceDynamic=1u<<20;
struct PhysicsObject {
 uint32_t pointer=0,tag=0,original=0;
 PhysicsMode authoredMode=PhysicsMode::Normal;
 std::optional<PhysicsMode> mode;
 // Retain original physics ownership after the editor selection clears.
 // This is host lifetime metadata, never a bit in a native saved variant.
 bool originalReleasedPhysics=false;
 // H4 object flag22 is a persistent forced-keyframed request. Native H3 has
 // no equivalent saved flag; retain its ownership separately from body type.
 bool keyframedOverride=false;
};
std::unordered_map<uint32_t,PhysicsObject> physicsObjects;
struct ControllerAttachmentState {uint32_t object=0,instance=0;};
std::unordered_map<uint32_t,ControllerAttachmentState> controllerAttachments;
uint32_t physicsEngine=0,physicsHeaders=0,physicsMap=0,physicsTick=0;
bool restoringPhysics=false;
// Valid only inside native82280720's synchronous mode transaction. Its
// successful monitor teardown precedes the exact82280818 release call.
thread_local std::optional<uint32_t> completedMonitorExitPlayer;
struct NativeEditorSlot {
 uint32_t player=0xffffffff;
 std::optional<HeldEditorState> editor;
 ManipulationInputState input;
 // Armed only by the complete scenery lifecycle after contact initialization.
 // Native H3 has no player152 counterpart; never alias native player memory.
 bool ownsMonitorContact=false;
 uint32_t contactMonitor=0xffffffff;
};
// Original H4 owns16 independent336-byte editors. These are host-side editor
// state only; never overlay native H3 player memory or serialize H4 records.
// Scoped around one native public grab call. The inner dequeue hook supplies
// the original H4 selection stage only after H3 committed ownership.
struct NativeGrabTransaction {
 uint32_t player,datum;
 bool selected=false;
 std::string error;
};
thread_local NativeGrabTransaction* nativeGrabTransaction=nullptr;
// Creation retains native allocation/budget services. This scope prevents a
// placement-radius override from escaping into other native query callers.
struct NativeCreatePlacement {
 uint32_t tag,player;
 bool hasPoint;
 std::optional<float> radius;
};
thread_local NativeCreatePlacement* nativeCreatePlacement=nullptr;
struct NativeCreatePlacementScope {
 NativeCreatePlacement* prior=nativeCreatePlacement;
 explicit NativeCreatePlacementScope(NativeCreatePlacement* value){nativeCreatePlacement=value;}
 ~NativeCreatePlacementScope(){nativeCreatePlacement=prior;}
};

// Native82331608 clears parent16/node20 before the world-pose callback.
// Preserve only attachment identity; root motion/poses are read at that callback.
struct NativeDetachAttachment {
 uint32_t datum,object,parent;
 int node;
 bool deferVelocity=false;
 bool rebuildAfterUnlink=false,physicsReset=false;
 std::optional<std::array<V,2>> fallbackVelocity;
};
thread_local NativeDetachAttachment* nativeDetachAttachment=nullptr;

struct NativeGrabTransactionScope {
 NativeGrabTransaction* prior=nativeGrabTransaction;
 explicit NativeGrabTransactionScope(NativeGrabTransaction* value){nativeGrabTransaction=value;}
 ~NativeGrabTransactionScope(){nativeGrabTransaction=prior;}
};
std::array<NativeEditorSlot,16> nativeEditors;
void ClearNativeEditors(){for(auto& slot:nativeEditors)slot=NativeEditorSlot{};}
// Contact normal belongs to the player lifetime, not the per-map editor.
// Keep it separately so initial PhysicsWorld synchronization cannot erase a
// normal initialized by the player allocator before Forge begins updating.
struct NativePlayerContact {
 uint32_t player=0xffffffff,pool=0,record=0;
 V normal{};
 bool normalKnown=false;
};
std::array<NativePlayerContact,16> nativePlayerContacts;
void ClearNativePlayerContacts(){
 nativePlayerContacts={};ClearNativeEditors();
}
NativePlayerContact* PlayerContact(uint8_t* base,uint32_t tls,uint32_t player,bool requireNormal){
 if(!Ptr(tls)||player==0xffffffff||(player&65535)>=nativePlayerContacts.size())return nullptr;
 const auto pool=U(base,tls+96),table=Ptr(pool)?U(base,pool+68):0;
 const uint64_t record=uint64_t(table)+(player&65535)*880ull;
 if(!Ptr(table)||record+880>=0xc0000000ULL||H(base,uint32_t(record))!=(player>>16))return nullptr;
 // Native821EF708 marks a departed player with record+4 bit1 before its
 // datum allocation is reclaimed. Matching salt alone is not a live player.
 if(U(base,uint32_t(record)+4)&2)return nullptr;
 auto& state=nativePlayerContacts[player&65535];
 if(state.player!=player||state.pool!=pool||state.record!=record){
  if(requireNormal)return nullptr;
  // Observation may encounter a restored live player without an allocation
  // callback. Bind identity only; do not invent the missing contact normal.
  state={player,pool,uint32_t(record),V{},false};
 }
 if(requireNormal&&!state.normalKnown)return nullptr;
 return &state;
}
struct NativeContactObservation {
 uint32_t player=0xffffffff,tls=0;
 std::optional<V> normal;
};
thread_local NativeContactObservation* nativeContactObservation=nullptr;
std::optional<NativeContactObservation> ObserveNativeContact(PPCContext& ctx,uint8_t* base){
 if(ctx.lr!=0x820F584C)return {};
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))return {};
 const auto pool=U(base,tls+0xa8),headers=Ptr(pool)?U(base,pool+68):0,datum=ctx.r3.u32;
 if(!Ptr(headers)||datum==0xffffffff)return {};
 const uint64_t header=uint64_t(headers)+(datum&65535)*16ull;
 if(header+16>=0xc0000000ULL||H(base,uint32_t(header))!=(datum>>16)||base[header+3]!=0)return {};
 const auto object=U(base,uint32_t(header)+12);
 if(!Ptr(object)||U(base,object+16)!=0xffffffff)return {};
 const auto player=U(base,object+380);
 auto* state=PlayerContact(base,tls,player,false);
 if(!state||ctx.r4.u32!=state->record+64||U(base,state->record+40)!=datum)return {};
 return NativeContactObservation{player,tls,{}};
}
void InitializeNativePlayerContact(PPCContext& ctx,uint8_t* base,uint32_t player){
 if(player==0xffffffff||(player&65535)>=nativePlayerContacts.size())return;
 const auto tls=U(base,ctx.r13.u32),pool=Ptr(tls)?U(base,tls+96):0;
 const auto table=Ptr(pool)?U(base,pool+68):0;
 const uint64_t record=uint64_t(table)+(player&65535)*880ull;
 if(!Ptr(table)||record+880>=0xc0000000ULL||H(base,uint32_t(record))!=(player>>16))
  throw std::runtime_error("Invalid completed native player allocation");
 auto& slot=nativeEditors[player&65535];
 slot=NativeEditorSlot{};slot.player=player;
 // H482355698 ->82A3B180 ->82A3B2B0 clears the whole4144-byte player
 // before82355740/823562E8. Neither overwrites normal152..160.
 // This is allocation-time initialization, not a per-grab default.
 nativePlayerContacts[player&65535]={player,pool,uint32_t(record),V{},true};
}


uint32_t ObjectPointer(uint8_t* base,uint32_t headers,uint32_t datum){
 if(datum==0xffffffff||!Ptr(headers))return 0;
 const auto header=headers+(datum&65535)*16;
 if(H(base,header)!=datum>>16)return 0;
 const auto object=U(base,header+12);
 return Ptr(object)?object:0;
}
uint32_t TagDefinition(uint8_t* base,uint32_t datum){
 if(datum==0xffffffff)return 0;
 const auto table=U(base,0x827f0f8c);
 if(!Ptr(table))return 0;
 const auto definition=U(base,table+(datum&65535)*8+4);
 return Ptr(definition)?definition:0;
}
// Counterpart data for H4's82469630: ANY authored keyframed body,
// not "all fixed bodies" and not the current runtime motion class.
// H3 model/phmo layout is the same stock layout used by AuthoredPhysics below.
std::optional<bool> AuthoredKeyframedBody(uint8_t* base,uint32_t object){
 const auto definition=TagDefinition(base,U(base,object));
 if(!definition)return false;
 const auto model=TagDefinition(base,U(base,definition+0x40));
 if(!model)return false;
 const auto phmo=TagDefinition(base,U(base,model+0x3c));
 if(!phmo)return false;
 const auto count=U(base,phmo+0x58),bodies=U(base,phmo+0x5c);
 if(!count)return false;
 // Reject invalid table ranges instead of treating corrupt data as dynamic.
 if(!Ptr(bodies)||uint64_t(bodies)+uint64_t(count)*176>=0xc0000000ULL)return {};
 for(uint32_t i=0;i<count;++i)if(H(base,bodies+i*176+0x1a)==4)return true;
 return false;
}
PhysicsMode AuthoredPhysics(uint8_t* base,uint32_t object){
 if(U(base,object+0xac)&kFrozen)return PhysicsMode::Fixed;
 const auto definition=TagDefinition(base,U(base,object));
 if(!definition)return PhysicsMode::Normal;
 const auto model=TagDefinition(base,U(base,definition+0x40));
 if(!model)return PhysicsMode::Normal;
 const auto phmo=TagDefinition(base,U(base,model+0x3c));
 if(!phmo)return PhysicsMode::Normal;
 const auto count=U(base,phmo+0x58),bodies=U(base,phmo+0x5c);
 if(!count||count>1024||!Ptr(bodies))return PhysicsMode::Normal;
 for(uint32_t i=0;i<count;++i)if(H(base,bodies+i*176+0x1a)!=5)return PhysicsMode::Normal;
 return PhysicsMode::Fixed;
}
bool PhysicsWorld(PPCContext& ctx,uint8_t* base){
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))return false;
 const auto engine=U(base,tls+0x64),array=U(base,tls+0xa8),time=U(base,tls+0xbc);
 if(!Ptr(engine)||!Ptr(array)||!Ptr(time))return false;
 const auto headers=U(base,array+0x44),map=U(base,engine+0x178),tick=U(base,time+0xc);
 if(!Ptr(headers))return false;
 // A new world owns new objects. Never restore an old pointer into it, even
 // when a map reload reuses the engine and object-table allocation.
 if(engine!=physicsEngine||headers!=physicsHeaders||map!=physicsMap||tick<physicsTick){
  physicsObjects.clear();physics.Reset();controllerAttachments.clear();
  ClearNativeEditors();coordinates.Reset();fixedSnap=0xffffffff;
  ClearAnchorWorld();
 }
 physicsEngine=engine;physicsHeaders=headers;physicsMap=map;physicsTick=tick;
 return true;
}
// Native early-mover records have two velocity banks but no H4 record460.
// Observe their producers without modifying the native records or tick order.
struct NativeHistoryIdentity {
 uint32_t history,headers,object,engine,map,time,datum;
 bool operator==(const NativeHistoryIdentity&) const =default;
};
struct NativeHistoryPhase {
 NativeHistoryIdentity identity{};
 uint32_t tick=0;
 bool known=false,first=false;
};
std::mutex nativeHistoryMutex;
std::array<NativeHistoryPhase,32> nativeHistoryPhases;
thread_local bool* nativeFirstHistorySampled=nullptr;
std::optional<NativeHistoryPhase> NativeHistoryIdentityAt(PPCContext& ctx,uint8_t* base,
                                                         uint32_t datum,uint32_t index){
 if(index>=nativeHistoryPhases.size()||datum==0xffffffff)return {};
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+128)))return {};
 const auto history=U(base,tls+264),array=U(base,tls+168);
 const auto engine=U(base,tls+100),time=U(base,tls+188);
 if(!Ptr(history)||uint64_t(history)+9860>=0xc0000000ULL||
    !Ptr(array)||!Ptr(engine)||!Ptr(time))return {};
 const auto count=U(base,history+9856);
 if(count>32||index>=count||U(base,history+9728+index*4)!=datum)return {};
 const auto headers=U(base,array+68),object=ObjectPointer(base,headers,datum);
 if(!object)return {};
 NativeHistoryPhase value;
 value.identity={history,headers,object,engine,U(base,engine+0x178),time,datum};
 value.tick=U(base,time+12);
 return value;
}
void RecordNativeHistoryPhase(PPCContext& ctx,uint8_t* base,uint32_t datum,
                              uint32_t index,bool first,bool sampled){
 if(index>=nativeHistoryPhases.size())return;
 const auto current=NativeHistoryIdentityAt(ctx,base,datum,index);
 std::lock_guard lock(nativeHistoryMutex);
 auto& slot=nativeHistoryPhases[index];
 if(!current){slot={};return;}
 if(!(slot.identity==current->identity)||current->tick<slot.tick)slot=*current;
 // H4's first producer changes460 only after successful sampling. The
 // second producer sets it even when it invalidates the active record.
 if(!first||sampled){slot=*current;slot.known=true;slot.first=first;}
}
std::optional<bool> NativeHistoryFirstBank(PPCContext& ctx,uint8_t* base,
                                          uint32_t datum,uint32_t index){
 const auto current=NativeHistoryIdentityAt(ctx,base,datum,index);
 if(!current)return {};
 std::lock_guard lock(nativeHistoryMutex);
 const auto& slot=nativeHistoryPhases[index];
 if(!slot.known||!(slot.identity==current->identity)||current->tick<slot.tick)return {};
 return slot.first;
}

bool PhysicsValid(uint8_t* base,uint32_t datum,const PhysicsObject& object){
 return ObjectPointer(base,physicsHeaders,datum)==object.pointer&&U(base,object.pointer)==object.tag;
}
void PhysicsCall(PPCContext& ctx,uint8_t* base,uint32_t datum,
                 void(*function)(PPCContext&,uint8_t*),uint32_t argument=0){
 auto call=ctx;call.r3.u32=datum;call.r4.u32=argument;function(call,base);
}
V NativeObjectVector(PPCContext& ctx,uint8_t* base,uint32_t datum,
                     void(*query)(PPCContext&,uint8_t*)){
 if(!ObjectPointer(base,physicsHeaders,datum))throw std::runtime_error("Invalid native object-vector datum");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto output=call.r1.u32+0x60;
 call.r3.u32=datum;call.r4.u32=output;query(call,base);
 auto result=Vec(base,output);
 for(float value:result)if(!std::isfinite(value))throw std::runtime_error("Nonfinite native object vector");
 return result;
}
V NativeObjectMotion(PPCContext& ctx,uint8_t* base,uint32_t datum){
 // H4 counterpart82260CF0: root ancestry, frozen zero-vector branch,
 // eligible selected physics-body velocity, then object-state fallback.
 // The held update requests linear motion only; explicitly null angular output
 // rather than inheriting an unrelated caller's r5 guest pointer.
 auto query=ctx;query.r5.u32=0;
 return NativeObjectVector(query,base,datum,__imp__sub_820AC960);
}
std::array<V,2> NativeObjectVelocities(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!ObjectPointer(base,physicsHeaders,datum))throw std::runtime_error("Invalid native velocity datum");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto linear=call.r1.u32+0x60,angular=linear+12;
 call.r3.u32=datum;call.r4.u32=linear;call.r5.u32=angular;
 __imp__sub_820AC960(call,base);
 std::array<V,2> result{Vec(base,linear),Vec(base,angular)};
 for(const auto& vector:result)for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite native object velocities");
 return result;
}
V NativePhysicsPoint(PPCContext& ctx,uint8_t* base,uint32_t datum){
 // H4 counterpart82260B58: root traversal, native physics access eligibility,
 // selected-body center (including authored fixed-body handling), then fallback.
 return NativeObjectVector(ctx,base,datum,__imp__sub_820AFA98);
}
bool ApplyNativeDetachPointVelocity(PPCContext& ctx,uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||U(base,object+16)!=0xffffffff)
  throw std::runtime_error("Native scenery detach did not produce an unparented object");
 // H4822980D8/native820AFCF8 reject objects without localized history.
 if(!(U(base,object+172)&8))return false;
 auto resolve=ctx;resolve.r3.u32=datum;
 __imp__sub_8211DE00(resolve,base);
 const auto index=resolve.r3.u32;
 if(index==0xffffffff)return false;
 const auto tls=U(base,ctx.r13.u32),history=Ptr(tls)?U(base,tls+264):0;
 if(index>=32||!Ptr(history)||uint64_t(history)+9864>=0xc0000000ULL||
    index>=U(base,history+9856))
  throw std::runtime_error("Invalid native detach history association");
 const auto root=U(base,history+9728+index*4);
 const auto phase=NativeHistoryFirstBank(ctx,base,root,index);
 const auto point=NativePhysicsPoint(ctx,base,datum);
 auto query=ctx;query.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+query.r1.u32,&backchain,4);
 const auto position=query.r1.u32+0x60,linear=position+12,angular=linear+12;
 for(unsigned i=0;i<3;++i){
  const auto value=std::byteswap(std::bit_cast<uint32_t>(point[i]));
  std::memcpy(base+position+i*4,&value,4);
 }
 query.r3.u32=datum;query.r4.u32=position;query.r5.u32=linear;
 query.r6.u32=angular;query.r7.u32=1;query.r8.u32=phase.value_or(false)?1:0;
 __imp__sub_820AFCF8(query,base);
 if(!(query.r3.u32&255))return false; // Caller applies the retained native parent fallback.
 // With no observed phase, the query only establishes eligibility. Never
 // apply its provisional bank: restored H3 state has no saved H4 record460.
 if(!phase)throw std::runtime_error("Detached scenery history phase has not been observed");
 for(const auto address:{linear,angular})
  for(float value:Vec(base,address))
   if(!std::isfinite(value))throw std::runtime_error("Nonfinite detach point velocity");
 if(ObjectPointer(base,physicsHeaders,datum)!=object)
  throw std::runtime_error("Detached scenery changed during velocity query");
 auto apply=ctx;apply.r1.u32=query.r1.u32;
 apply.r3.u32=datum;apply.r4.u32=linear;apply.r5.u32=angular;
 __imp__sub_820F29C8(apply,base);
 return true;
}
void ApplyNativeDetachFallback(PPCContext& ctx,uint8_t* base,const NativeDetachAttachment& attachment){
 if(!attachment.fallbackVelocity||ObjectPointer(base,physicsHeaders,attachment.datum)!=attachment.object)
  throw std::runtime_error("Detached scenery lost its deferred velocity target");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32),linear=call.r1.u32+0x60,angular=linear+12;
 std::memcpy(base+call.r1.u32,&backchain,4);
 for(unsigned v=0;v<2;++v)for(unsigned i=0;i<3;++i){
  const auto value=std::byteswap(std::bit_cast<uint32_t>((*attachment.fallbackVelocity)[v][i]));
  std::memcpy(base+linear+v*12+i*4,&value,4);
 }
 call.r3.u32=attachment.datum;call.r4.u32=linear;call.r5.u32=angular;
 __imp__sub_820F29C8(call,base);
}
V NativeSelectionOrigin(PPCContext& ctx,uint8_t* base,uint32_t monitor){
 // Original H3 Forge82281268 uses820AA480, the unit eye/marker/seat query.
 // H4 calls822B79A0 at this boundary. Keep player and monitor behavior native
 // as required; object origin and physics center are not substitutes here.
 return NativeObjectVector(ctx,base,monitor,__imp__sub_820AA480);
}
float NativeHeldDefinitionRadius(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||(base[object+154]!=6&&base[object+154]!=10))
  throw std::runtime_error("Held camera radius requires valid scenery");
 const auto definition=TagDefinition(base,U(base,object));
 if(!definition)throw std::runtime_error("Missing held scenery definition");
 // H4 object-definition32 BoundingRadius -> stock H3 definition4.
 // This is separate from the runtime sphere used by grab initialization.
 const auto radius=F(base,definition+4);
 if(!std::isfinite(radius)||radius<0)throw std::runtime_error("Invalid held definition radius");
 return radius;
}
V NativeObjectOrigin(PPCContext& ctx,uint8_t* base,uint32_t datum){
 // H4 counterpart8225EA20: origin with parent-node transformation.
 return NativeObjectVector(ctx,base,datum,__imp__sub_820A9E58);
}
V NativeHeldReferencePoint(PPCContext& ctx,uint8_t* base,uint32_t datum){
 // Original822410D0's alternate provider828211D8 requires simulation4/5
 // (dist-client/dist-server). Both executables name simulation1 "local".
 // This adapter is deliberately confined to the existing local Forge gate;
 // distributed replication must not silently use its ordinary-origin branch.
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))
  throw std::runtime_error("Held reference point requires local Forge simulation");
 // H4 fallback8225EA20 ->native820A9E58, including the parent-node transform.
 return NativeObjectOrigin(ctx,base,datum);
}
// Boolean point-location boundary shared by 82451BA8 and monitor-follow
// 8244AF48: both call 82415970 with the initialized H4 mask
// 0x0000100900000000 (83292E30/83292E50). Its low word disables object
// traversal, bit1 disables the extra world query, and its bit3 helper82569F08
// primes an H4-private cache but always returns false. The remaining result
// is true iff some active BSP was queried and none returned a containing leaf.
// H3 820AE5C0 with zero mask computes that same result: all no-leaf BSPs yield
// true, the first containing leaf yields false, and no active BSP yields false.
// Passing the H4 mask unchanged would incorrectly enable H3 instance hits.
// H3 owns its own world storage; H4's transient query cache is not imported.
bool NativeHeldWorldPointBlocked(PPCContext& ctx,uint8_t* base,const V& point){
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto input=call.r1.u32+0x60;
 for(unsigned axis=0;axis<3;++axis){
  if(!std::isfinite(point[axis]))throw std::runtime_error("Nonfinite held-world query point");
  const auto bits=std::byteswap(std::bit_cast<uint32_t>(point[axis]));
  std::memcpy(base+input+axis*4,&bits,4);
 }
 call.r3.u64=0;call.r4.u32=input;call.r5.u32=0xffffffff;
 call.r6.u32=0xffffffff;call.r7.u32=0;
 __imp__sub_820AE5C0(call,base);
 return call.r3.u8!=0;
}
// Vertex stage of H4 82451BA8. The caller must first perform its original
// object-position location query. Keep that separate until the point-query
// mask and native service are mapped; this is not a generic overlap test.
// Pass the reserved context to callbacks so their guest frames cannot overwrite
// this descriptor/iterator. Original H3 readers preserve selected permutations.
bool NativeCollisionVerticesPass(PPCContext& ctx,uint8_t* base,uint32_t datum,
 const std::function<bool(PPCContext&,const V&)>& pointQuery){
 if(!ObjectPointer(base,physicsHeaders,datum)||!pointQuery)
  throw std::runtime_error("Invalid collision vertex query");
 auto frame=ctx;frame.r1.u32-=0x180;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+frame.r1.u32,&backchain,4);
 const auto descriptor=frame.r1.u32+0x60,iterator=frame.r1.u32+0x80;
 std::memset(base+descriptor,0,20);std::memset(base+iterator,0,28);
 auto call=frame;call.r3.u32=descriptor;call.r4.u32=datum;
 __imp__sub_820AF448(call,base); // H4 821EF090: model, collision, choices, nodes.
 if(!call.r3.u8)return false;
 const auto nodes=U(base,descriptor+16);
 call=frame;call.r3.u32=iterator;call.r4.u32=U(base,descriptor+4);
 call.r5.u32=U(base,descriptor+8);call.r6.u32=U(base,descriptor+12);
 __imp__sub_820AF6D0(call,base); // H4 824F92C8; H3 has 16 choices, not 32.
 bool accepted=true;
 for(;;){
  call=frame;call.r3.u32=iterator;__imp__sub_820AF7B0(call,base);
  if(!call.r3.u8)break;
  const auto geometry=U(base,iterator+24),node=U(base,iterator+20)&255;
  if(!Ptr(geometry)||uint64_t(geometry)+96>=0xc0000000ULL)
   throw std::runtime_error("Invalid native collision geometry");
  const auto count=int32_t(U(base,geometry+84));
  const auto vertices=U(base,geometry+88);
  if(count<=0)continue;
  const uint64_t matrixAddress=uint64_t(nodes)+node*52;
  if(!Ptr(nodes)||matrixAddress+52>=0xc0000000ULL||!Ptr(vertices)||
     uint64_t(vertices)+uint64_t(count)*16>=0xc0000000ULL)
   throw std::runtime_error("Invalid native collision vertex range");
  const auto matrix=uint32_t(matrixAddress);
  for(int32_t i=0;i<count;++i){
   const auto vertex=Vec(base,vertices+uint32_t(i)*16);
   const auto scale=F(base,matrix);
   const float x=vertex[0]*scale,y=vertex[1]*scale,z=vertex[2]*scale;
   V world{};
   // Preserve H4's z,y,x fused-add order. Native 820BDC38 accumulates y,z,x.
   for(unsigned axis=0;axis<3;++axis){
    const float zy=std::fma(F(base,matrix+16+axis*4),y,F(base,matrix+28+axis*4)*z);
    world[axis]=std::fma(F(base,matrix+4+axis*4),x,zy)+F(base,matrix+40+axis*4);
    if(!std::isfinite(world[axis]))throw std::runtime_error("Nonfinite collision vertex");
   }
   // Original skips remaining vertices of this BSP on failure, but continues
   // subsequent BSPs rather than terminating the entire iterator.
   auto queryContext=frame;
   if(!pointQuery(queryContext,world)){accepted=false;break;}
  }
 }
 return accepted;
}
// Complete local-simulation geometry callback for original82451BA8.
// H4 8293A3B0 starts with82260B58 (native820AFA98). Its optional correction
// is enabled by82821790/828218D8 only after828211D8 supplies a distributed
// simulation4/5 record. Creation82933B30 clears the enable byte. Consequently
// the existing simulation1 gate uses the ordinary physics-center branch.
// Do not extend this assumption to network sessions or use object origin here.
bool NativeHeldGeometryBlocked(PPCContext& ctx,uint8_t* base,uint32_t datum){
 const auto tls=U(base,ctx.r13.u32);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))
  throw std::runtime_error("Held geometry query requires local Forge simulation");
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||(base[object+154]!=6&&base[object+154]!=10))
  throw std::runtime_error("Held geometry query requires valid scenery");
 const auto point=NativePhysicsPoint(ctx,base,datum);
 if(!NativeHeldWorldPointBlocked(ctx,base,point))return false;
 return NativeCollisionVerticesPass(ctx,base,datum,
  [base](PPCContext& queryContext,const V& vertex){
   return NativeHeldWorldPointBlocked(queryContext,base,vertex);
  });
}
// First two gates of original82451DA8, in their original order. The later
// teleporter/spawn-specific rules remain native H3 gameplay behavior.
bool NativeSceneryReleasePositionValid(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(NativeHeldGeometryBlocked(ctx,base,datum))return false;
 const auto origin=NativeObjectOrigin(ctx,base,datum);
 for(float component:origin)if(!std::isfinite(component))
  throw std::runtime_error("Nonfinite scenery release origin");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto point=call.r1.u32+0x60;
 for(unsigned i=0;i<3;++i){
  const auto word=std::byteswap(std::bit_cast<uint32_t>(origin[i]));
  std::memcpy(base+point+i*4,&word,4);
 }
 // H482328310(point,0) -> native scenario volume union821AA050(point).
 call.r3.u32=point;__imp__sub_821AA050(call,base);
 return (call.r3.u32&255)!=0;
}
// Stock H3 world orientation, counterpart to H4's ordinary8229D4E0 path.
// Preserve parent-node transforms and the native monitor's orientation rather
// than substituting host camera angles or the held object's forward vector.
std::array<V,2> NativeObjectOrientation(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!ObjectPointer(base,physicsHeaders,datum))throw std::runtime_error("Invalid native orientation datum");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto forward=call.r1.u32+0x60,up=forward+12;
 call.r3.u32=datum;call.r4.u32=forward;call.r5.u32=up;
 __imp__sub_820B1928(call,base);
 std::array<V,2> result{Vec(base,forward),Vec(base,up)};
 for(const auto& axis:result)for(float value:axis)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite native object orientation");
 return result;
}
uint32_t NativePhysicsInstance(uint8_t* base,uint32_t object){
 const auto datum=U(base,object+160);
 if(datum==0xffffffff)return 0;
 // Native820AFA98: 144-byte records in the native physics-instance pool.
 const auto pool=U(base,0x828e62b4);
 if(!Ptr(pool))throw std::runtime_error("Invalid native physics-instance pool");
 const auto entries=U(base,pool+68);
 const uint64_t address=uint64_t(entries)+(datum&65535)*144ull;
 if(!Ptr(entries)||address+144>=0xc0000000ULL)
  throw std::runtime_error("Invalid native physics-instance range");
 return uint32_t(address);
}
// Original8244D514..D5A8 allows coupled held/monitor submission only for
// an unparented object with an instance connected to the physics world.
// H4 instance16 bit2 is set/cleared by8249C390/8249B7B0. Native equivalents
// 822633B8/82263098 use instance4 bit3, not H4's literal mask.
bool NativeCoupledSceneryEligible(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)return false;
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if((type!=6&&type!=10)||U(base,object+16)!=0xffffffff)return false;
 const auto instance=NativePhysicsInstance(base,object);
 return instance&&(U(base,instance+4)&(1u<<3))!=0;
}
// Original82582610 walks to the root before collecting marker transforms.
// Keep the candidate datum itself for eligibility/scoring; do not replace the
// nearby query result with its root or deduplicate multiple children by root.
uint32_t NativeMarkerRoot(uint8_t* base,uint32_t datum){
 if(datum==0xffffffff)return datum;
 std::vector<uint32_t> visited;
 uint32_t current=datum;
 for(;;){
  if(std::find(visited.begin(),visited.end(),current)!=visited.end())
   throw std::runtime_error("Cycle in native marker ancestry");
  const auto object=ObjectPointer(base,physicsHeaders,current);
  if(!object)throw std::runtime_error("Invalid native marker ancestor");
  visited.push_back(current);
  const auto parent=U(base,object+16);
  if(parent==0xffffffff)return current;
  current=parent;
 }
}
struct NativeMarkerNodeState {
 std::vector<std::array<float,13>> matrices;
 std::vector<uint8_t> permutations;
 bool mirrored=false;
};
NativeMarkerNodeState ReadNativeMarkerNodes(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native marker node object");
 // Native8210CDF8 reads signed byte-size314 and relative offset316,
 // divides the byte-size by52, and forwards object4 bit10 as mirroring.
 const auto bytes=int16_t(H(base,object+314));
 const auto offset=int16_t(H(base,object+316));
 if(bytes<=0||bytes%52||bytes/52>256||offset<0||
    !Ptr(object+uint32_t(offset))||uint64_t(object)+offset+bytes>=0xc0000000ULL)
  throw std::runtime_error("Invalid native live marker node array");
 NativeMarkerNodeState result;
 result.mirrored=(U(base,object+4)&(1u<<10))!=0;
 //8210CDF8 passes region-block +8*(adjusted byte-size/10) to82591580.
 // The latter compares one byte per marker region with marker permutation1.
 // The flag-dependent16 bytes are excluded when deriving the region count.
 const int regionBytes=int16_t(H(base,object+318));
 const int regionOffset=int16_t(H(base,object+320));
 const int adjustedBytes=regionBytes-((U(base,object+4)&(1u<<11))?16:0);
 if(adjustedBytes<0||adjustedBytes%10||regionOffset<0||
    !Ptr(object+uint32_t(regionOffset))||
    uint64_t(object)+regionOffset+regionBytes>=0xc0000000ULL)
  throw std::runtime_error("Invalid native marker permutation block");
 const auto regionCount=uint32_t(adjustedBytes/10);
 const auto permutationStart=object+uint32_t(regionOffset)+regionCount*8;
 result.permutations.assign(base+permutationStart,base+permutationStart+regionCount);
 result.matrices.resize(bytes/52);
 for(size_t node=0;node<result.matrices.size();++node)for(unsigned field=0;field<13;++field){
  const auto value=F(base,object+uint32_t(offset)+uint32_t(node)*52+field*4);
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite native marker node transform");
  result.matrices[node][field]=value;
 }
 return result;
}
const Binding* NativeMarkerBinding(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native marker binding object");
 // AFM bindings attach the original H4 marker group to an exact native
 // map/object definition. Candidate and parent lookups must remain separate.
 const auto found=bindings.find((uint64_t(physicsMap)<<32)|U(base,object));
 return found==bindings.end()?nullptr:&found->second;
}
struct NativeMarkerData {
 bool candidateHasGroup=false;
 std::vector<Marker> rootMarkers;
};
NativeMarkerData ReadNativeMarkerData(Bridge& original,uint8_t* base,uint32_t datum){
 NativeMarkerData result;
 if(datum==0xffffffff)return result;
 result.candidateHasGroup=NativeMarkerBinding(base,datum)!=nullptr;
 const auto root=NativeMarkerRoot(base,datum);
 const auto binding=NativeMarkerBinding(base,root);
 if(!binding)return result;
 if(binding->definitions.empty())
  throw std::runtime_error("Complete native marker path requires AFM3 source metadata");
 const auto state=ReadNativeMarkerNodes(base,root);
 result.rootMarkers=original.BuildMarkers(binding->definitions,state.matrices,state.permutations,state.mirrored);
 return result;
}
// Native counterpart of H4's821F2050 sphere query. The caller supplies the
// original query radius/center and an explicitly translated native type mask.
// Preserve native cluster traversal, duplicate suppression and result order;
// do not enumerate only Forge variant slots or rank/prune the result here.
std::vector<uint32_t> NativeNearbyObjects(PPCContext& ctx,uint8_t* base,
    uint32_t referenceDatum,const V& center,float radius,uint32_t nativeTypeMask){
 const auto object=ObjectPointer(base,physicsHeaders,referenceDatum);
 if(!object||!nativeTypeMask||!std::isfinite(radius)||radius<0||
    ctx.r1.u32<0x5000||ctx.r1.u32>=0xc0000000)
  throw std::runtime_error("Invalid native nearby-object query");
 for(float value:center)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite native nearby-object center");
 auto query=ctx;query.r1.u32-=0x300;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+query.r1.u32,&backchain,4);
 const auto point=query.r1.u32+0x60,output=query.r1.u32+0x80;
 for(unsigned axis=0;axis<3;++axis){
  const auto word=std::byteswap(std::bit_cast<uint32_t>(center[axis]));
  std::memcpy(base+point+axis*4,&word,4);
 }
 query.r3.u32=1;query.r4.u32=nativeTypeMask;
 // Native820E0350 supplies object28 as location to820B0B60; the H4
 // marker caller supplies object24 to821F2050. Both read its first ushort.
 query.r5.u32=object+28;query.r6.u32=point;query.r7.u32=0;
 query.r8.u32=output;query.r9.u32=64;query.f1.f64=radius;
 __imp__sub_820B0B60(query,base);
 if(query.r3.s32<0||query.r3.u32>64)
  throw std::runtime_error("Invalid native nearby-object result count");
 std::vector<uint32_t> result;result.reserve(query.r3.u32);
 for(uint32_t i=0;i<query.r3.u32;++i){
  const auto datum=U(base,output+i*4);
  if(!ObjectPointer(base,physicsHeaders,datum))
   throw std::runtime_error("Native nearby-object query returned an invalid datum");
  result.push_back(datum);
 }
 return result;
}
// Original82582250 uses0x3ADF. H4 type table8336AD78 (indexed by
// object178 in822B4458) adds dispenser9 before native sound/crate/etc.
// Preserve classes0..8, omit dispenser (no H3 class), shift10..14 down one.
constexpr uint32_t kH4MagnetTypeMask=0x3adf;
constexpr uint32_t kNativeMagnetTypeMask=
    (kH4MagnetTypeMask&0x1ff)|((kH4MagnetTypeMask&0x7c00)>>1);
static_assert(kNativeMagnetTypeMask==0x1cdf);
std::vector<uint32_t> NativeMagnetCandidates(Bridge& original,PPCContext& ctx,uint8_t* base,
                                          const HeldEditorState& editor,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid held magnet query object");
 uint32_t selected;std::memcpy(&selected,editor.bytes.data(),4);
 if(std::byteswap(selected)!=datum)
  throw std::runtime_error("Magnet query editor/object mismatch");
 // Caller runs original offset-decay/distance update first. Do not use the
 // submitted snap pose as the editor reference or the physics-point input.
 const auto point=NativePhysicsPoint(ctx,base,datum);
 const auto radius=original.MagnetQueryRadius(editor,point,F(base,object+44));
 return NativeNearbyObjects(ctx,base,datum,point,radius,kNativeMagnetTypeMask);
}
void SyncNativeSceneryPose(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!ObjectPointer(base,physicsHeaders,datum))
  throw std::runtime_error("Invalid native scenery synchronization datum");
 struct Scope {
  std::optional<uint32_t> previous=nativePoseSyncDatum;
  explicit Scope(uint32_t datum){nativePoseSyncDatum=datum;}
  ~Scope(){nativePoseSyncDatum=previous;}
 } scope(datum);
 // Original82281A98 settling path calls82284078(1, held). That routine
 // reads the current native pose and forwards it to stock variant placement.
 auto call=ctx;call.r3.u32=1;call.r4.u32=datum;
 __imp__sub_82284078(call,base);
}
Scene BuildNativeMagnetScene(Bridge& original,PPCContext& ctx,uint8_t* base,
                            const HeldEditorState& editor,uint32_t datum,uint32_t monitor){
 Scene scene;scene.nearbyOrder.emplace();
 const auto monitorObject=ObjectPointer(base,physicsHeaders,monitor);
 if(!monitorObject)throw std::runtime_error("Missing native marker-scene monitor");
 scene.processedMovement=Vec(base,monitorObject+496);
 for(float value:scene.processedMovement)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite native marker-scene movement");
 auto append=[&](uint32_t id){
  const auto object=ObjectPointer(base,physicsHeaders,id);
  if(!object)throw std::runtime_error("Invalid native marker-scene object");
  Object item;item.datum=id;
  // Native820FC7F8 and82344B58 supply object32/44 as runtime sphere.
  // H4 candidate scoring reads the corresponding object64/76 fields.
  item.position=Vec(base,object+32);item.radius=F(base,object+44);
  for(float value:item.position)if(!std::isfinite(value))
   throw std::runtime_error("Nonfinite native candidate sphere");
  if(!std::isfinite(item.radius)||item.radius<0)
   throw std::runtime_error("Invalid native candidate radius");
  item.hasMagnetGroup=NativeMarkerBinding(base,id)!=nullptr;
  // Original82582250 collects held markers before querying, but checks each
  // candidate's own group before looking up its root's markers.
  if(id==datum||*item.hasMagnetGroup){
   auto data=ReadNativeMarkerData(original,base,id);
   item.hasMagnetGroup=data.candidateHasGroup;
   item.markers=std::move(data.rootMarkers);
  }
  scene.objects.push_back(std::move(item));
 };
 append(datum);
 // Original early-out: a held object with no markers does not run the query.
 if(scene.objects.front().markers.empty())return scene;
 const auto nearby=NativeMagnetCandidates(original,ctx,base,editor,datum);
 for(auto id:nearby){
  auto found=std::find_if(scene.objects.begin(),scene.objects.end(),
                         [&](const Object& item){return item.datum==id;});
  uint32_t index=uint32_t(found-scene.objects.begin());
  if(found==scene.objects.end())append(id);
  scene.nearbyOrder->push_back(index);
 }
 return scene;
}
V NativePredictionLocalPoint(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||(base[object+154]!=6&&base[object+154]!=10))
  throw std::runtime_error("Prediction point requires valid scenery");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance||!U(base,instance+36))throw std::runtime_error("Prediction point requires a physics body");
 const auto entry=U(base,instance+32);
 if(!Ptr(entry)||uint64_t(entry)+72>=0xc0000000ULL)
  throw std::runtime_error("Invalid first prediction body entry");
 const auto body=U(base,entry+64);
 if(!Ptr(body)||uint64_t(body)+316>=0xc0000000ULL)
  throw std::runtime_error("Invalid first prediction body");
 // H48249B1F8 uses the FIRST body, not the selected-body world point.
 // Local center: H4 body368 -> H3 body304 (native826292C8 rotation).
 V point=Vec(base,body+304);
 const auto motion=base[body+168];
 if((U(base,instance+4)&(1u<<8))&&(motion==7||motion==6)&&U(base,entry+16)>0){
  const auto indices=U(base,entry+12);
  if(!Ptr(indices))throw std::runtime_error("Invalid prediction body binding");
  const auto index=static_cast<int8_t>(base[indices]);
  if(index!=-1){
   if(index<0)throw std::runtime_error("Invalid authored prediction body index");
   const auto owner=ObjectPointer(base,physicsHeaders,U(base,instance+8));
   if(!owner)throw std::runtime_error("Invalid prediction physics owner");
   const auto definition=TagDefinition(base,U(base,owner));
   const auto model=definition?TagDefinition(base,U(base,definition+64)):0;
   const auto phmo=model?TagDefinition(base,U(base,model+60)):0;
   if(!phmo||uint32_t(index)>=U(base,phmo+88))
    throw std::runtime_error("Missing authored prediction body");
   const auto bodies=U(base,phmo+92);
   const uint64_t record=uint64_t(bodies)+uint32_t(index)*176ull;
   if(!Ptr(bodies)||record+176>=0xc0000000ULL)
    throw std::runtime_error("Invalid authored prediction body range");
   // H4 phmo record56 CenterOffMassOffset -> H3 record44 CenterOfMassOffset.
   // Preserve H4's fixed OR keyframed branch and return local coordinates;
   // native820AFBC0's transformed CenterOfMass96 is a different service.
   point=Vec(base,uint32_t(record)+44);
  }
 }
 for(float value:point)if(!std::isfinite(value))throw std::runtime_error("Nonfinite prediction local point");
 return point;
}
RotationPhysics NativeRotationPhysics(uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native rotation object");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Rotation world requires scenery or crate");
 RotationPhysics result;
 // H4 adds dispenser9: stock H3 crate10 maps to H4 crate11; scenery6
 // remains6. The private type is used only by original8244A6A8.
 result.objectType=type==6?6:11;
 // Original H3 predicate8227F578 checks connected7; H4 checks connected8.
 // Only this flag is observed by the original rotation predicate.
 if(U(base,object+172)&kConnected)result.objectFlags=1ull<<8;
 const auto instance=NativePhysicsInstance(base,object);
 result.hasInstance=instance!=0;
 if(!instance)return result;
 // Native instance4 bit7 has the same blocking role as H4 instance16 bit7.
 result.instanceFlags=U(base,instance+4)&0x80;
 const auto count=U(base,instance+36),bodies=U(base,instance+32);
 if(count>64||(count&&(!Ptr(bodies)||uint64_t(bodies)+uint64_t(count)*72>=0xc0000000ULL)))
  throw std::runtime_error("Invalid native rotation body table");
 for(unsigned i=0;i<count;++i){
  const auto body=U(base,bodies+i*72+64);
  if(!Ptr(body)||uint64_t(body)+169>=0xc0000000ULL)
   throw std::runtime_error("Invalid native rotation body");
  // Predicate-only projection, not a general Havok motion conversion:
  // original H4 compares solely against fixed5. Native fixed is7;
  // native keyframed6 must remain NON-fixed here, unlike H3's old gate.
  result.bodyMotion.push_back(base[body+168]==7?5:0);
 }
 return result;
}
V NativeMonitorRotationView(uint8_t* base,uint32_t monitor){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object)throw std::runtime_error("Invalid native rotation monitor");
 const auto type=base[physicsHeaders+(monitor&65535)*16+3];
 if(type!=0&&type!=1)throw std::runtime_error("Native rotation view requires a controlled unit");
 // Counterpart reset routines820F6658/82227810 establish native424 versus
 // H4 1260. Original8244B518 reads this unit view, NOT object orientation.
 const auto view=Vec(base,object+424);
 for(float value:view)if(!std::isfinite(value))throw std::runtime_error("Nonfinite native monitor view");
 return view;
}
// H4 follow823FC348 -> native820B04B0: native controls retain yaw/pitch.
// H3 setter performs direction conversion/wrap then82227800 propagation;
// do not write the H4 three-angle record into the smaller H3 action record.
void SubmitNativeMonitorView(PPCContext& ctx,uint8_t* base,uint32_t localIndex,
                             uint32_t monitor,const V& forward){
 const auto tls=U(base,ctx.r13.u32);
 if(localIndex>=4||!Ptr(tls)||!LocalForge(base,U(base,tls+0x80)))
  throw std::runtime_error("Monitor view requires a local Forge player");
 const auto controls=U(base,tls+120);
 if(!Ptr(controls)||U(base,controls+localIndex*236+16)!=monitor||
    !ObjectPointer(base,physicsHeaders,monitor))
  throw std::runtime_error("Monitor view ownership changed");
 for(float value:forward)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite monitor facing direction");
 const double length=double(forward[0])*forward[0]+double(forward[1])*forward[1]+
                     double(forward[2])*forward[2];
 if(length==0)throw std::runtime_error("Empty monitor facing direction");
 if(ctx.r1.u32<0x5000||ctx.r1.u32>=0xc0000000)
  throw std::runtime_error("Invalid native monitor view stack");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto input=call.r1.u32+0x60;
 for(unsigned axis=0;axis<3;++axis){
  const auto bits=std::byteswap(std::bit_cast<uint32_t>(forward[axis]));
  std::memcpy(base+input+axis*4,&bits,4);
 }
 call.r3.u32=localIndex;call.r4.u32=input;
 __imp__sub_820B04B0(call,base);
}
// Original82452930 active-biped branch writes forward before822AAB18.
// Native820F6550 is that notification: matching epsilon check, relative
// rotation and both cached node-orientation arrays (native306..312).
void SubmitNativeMonitorOrientation(PPCContext& ctx,uint8_t* base,uint32_t monitor,
                                    const V& facing){
 const auto tls=U(base,ctx.r13.u32);
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80))||!object||
    base[physicsHeaders+(monitor&65535)*16+3]!=0||U(base,object+16)!=0xffffffff)
  throw std::runtime_error("Monitor orientation requires a local unparented biped");
 const auto previous=Vec(base,object+96);
 const auto up=Vec(base,object+108);
 for(const auto& vector:{facing,previous,up})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite monitor orientation");
 if(ctx.r1.u32<0x5000||ctx.r1.u32>=0xc0000000)
  throw std::runtime_error("Invalid native monitor orientation stack");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto oldFacing=call.r1.u32+0x60;
 for(unsigned axis=0;axis<3;++axis){
  const auto oldBits=std::byteswap(std::bit_cast<uint32_t>(previous[axis]));
  const auto newBits=std::byteswap(std::bit_cast<uint32_t>(facing[axis]));
  std::memcpy(base+oldFacing+axis*4,&oldBits,4);
  std::memcpy(base+object+96+axis*4,&newBits,4);
 }
 // Current up is retained exactly, as82452930's copy-back does.
 call.r3.u32=monitor;call.r4.u32=oldFacing;call.r5.u32=object+96;
 __imp__sub_820F6550(call,base);
}
V NativeMonitorDesiredView(uint8_t* base,uint32_t monitor){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object)throw std::runtime_error("Invalid native movement monitor");
 const auto type=base[physicsHeaders+(monitor&65535)*16+3];
 if(type!=0&&type!=1)throw std::runtime_error("Native desired view requires a controlled unit");
 // Reset820F6658 copies current424 into desired400 and secondary412.
 // H4 reset82227810 copies current1260 into desired1212 and secondary1248,
 // additionally shifting its two desired-history vectors1224/1236.
 // Original held update8244A8D8 reads1212, whereas rotation reads1260.
 const auto view=Vec(base,object+400);
 for(float value:view)if(!std::isfinite(value))throw std::runtime_error("Nonfinite desired monitor view");
 return view;
}
bool NativeMonitorMovementFlag(uint8_t* base,uint32_t monitor){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object)throw std::runtime_error("Invalid native movement-flag monitor");
 const auto type=base[physicsHeaders+(monitor&65535)*16+3];
 if(type!=0&&type!=1)throw std::runtime_error("Native movement flag requires a controlled unit");
 // Native821EC0E0 copies action8 into unit-packet16, preserving bit0;
 // 820B8608 writes that word into unit392. H4 823619F8 copies action8
 // into its 64-bit packet16 and822562A8 writes unit1200. Intervening
 // producer masks change higher bits only. Read native processed state,
 // not the host key state or the pre-consumption action packet.
 return (U(base,object+392)&1)!=0;
}
struct NativeMonitorBoost {float peakPower,fraction;};
NativeMonitorBoost ReadNativeMonitorBoost(PPCContext& ctx,uint8_t* base,uint32_t monitor){
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object)throw std::runtime_error("Invalid native boost monitor");
 const auto type=base[physicsHeaders+(monitor&65535)*16+3];
 if(type!=0&&type!=1)throw std::runtime_error("Native boost requires a controlled unit");
 const auto definition=TagDefinition(base,U(base,object));
 if(!definition)throw std::runtime_error("Missing native monitor definition");
 // H4 tag1428 and unit2168 supply 1+(peak-1)*fraction in8244A8D8.
 // Native82388AA0/82383E50 use tag720 and original820EA138's f1 result
 // for the same formula. Keep native boost lifecycle and timing untouched;
 // native unit992/996 are timers, not a stored H4-style fraction.
 auto call=ctx;call.r3.u32=monitor;__imp__sub_820EA138(call,base);
 NativeMonitorBoost result{F(base,definition+720),float(call.f1.f64)};
 if(!std::isfinite(result.peakPower)||!std::isfinite(result.fraction))
  throw std::runtime_error("Nonfinite native monitor boost");
 return result;
}
void RotateNativeScenery(PPCContext& ctx,uint8_t* base,HeldEditorState& editor,
                         uint32_t monitor,const ManipulationInputState& mappedInput){
 if(!bridge||!PhysicsWorld(ctx,base))throw std::runtime_error("Native scenery rotation world unavailable");
 uint32_t held;std::memcpy(&held,editor.bytes.data(),4);held=std::byteswap(held);
 if(held==0xffffffff)return;
 const auto tls=U(base,ctx.r13.u32),time=U(base,tls+188);
 if(!Ptr(time))throw std::runtime_error("Invalid native Forge tick state");
 // Native simulation interval is read as-is; no host clock or timing change.
 const float interval=F(base,time+8);
 const auto view=NativeMonitorRotationView(base,monitor);
 const auto world=NativeRotationPhysics(base,held);
 bridge->RotateHeld(editor,mappedInput,view,interval,world);
}
std::array<float,6> NativeVariantBounds(uint8_t* base){
 if(!Ptr(physicsEngine)||uint64_t(physicsEngine)+120+284>=0xc0000000ULL)
  throw std::runtime_error("Invalid native Forge variant");
 // Original822837C8: live variant at engine120. Decoder821E01E0
 // reads192 bits at variant260;821AE060 consumes three min/max pairs.
 std::array<float,6> result;
 for(unsigned i=0;i<6;++i){
  result[i]=F(base,physicsEngine+120+260+i*4);
  if(!std::isfinite(result[i]))throw std::runtime_error("Nonfinite native variant bounds");
 }
 for(unsigned i=0;i<3;++i)if(result[i*2]>result[i*2+1])
  throw std::runtime_error("Inverted native variant bounds");
 return result;
}
// Native BSP collection is a world-data boundary. Keep the H4 response
// selector separate: do not substitute native82237E58 for original824863F8.
ContactCollection CollectNativeSceneryContacts(PPCContext& ctx,uint8_t* base,
                         uint32_t datum,const V& center,float objectRadius,float searchRadius,bool monitor=false){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native contact datum");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(monitor){
  const auto tls=U(base,ctx.r13.u32);
  if(type!=0||!Ptr(tls)||!LocalForge(base,U(base,tls+0x80))||U(base,object+16)!=0xffffffff)
   throw std::runtime_error("Monitor contact collector requires a local Forge biped root");
 }else if(type!=6&&type!=10)throw std::runtime_error("Contact collector requires scenery or crate");
 if(!std::isfinite(objectRadius)||objectRadius<0||!std::isfinite(searchRadius)||searchRadius<0)
  throw std::runtime_error("Invalid native contact radii");
 for(float value:center)if(!std::isfinite(value))throw std::runtime_error("Nonfinite native contact center");
 const auto origin=NativeObjectOrigin(ctx,base,datum);
 auto call=ctx;call.r1.u32-=0x2300;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto collection=call.r1.u32+0x60,point=call.r1.u32+0x2100;
 const auto reference=point+16,flags=point+32;
 // Original collector initializes its header and flag result. Pointer-bearing
 // records remain in native memory only for this synchronous call and copy.
 for(unsigned i=0;i<3;++i){
  const auto p=std::byteswap(std::bit_cast<uint32_t>(center[i]));
  const auto o=std::byteswap(std::bit_cast<uint32_t>(origin[i]));
  std::memcpy(base+point+i*4,&p,4);std::memcpy(base+reference+i*4,&o,4);
 }
 call.r3.u32=collection;call.r4.u32=flags;call.r5.u32=type;
 // Native820FFBE0 passes unit1218==1 as the biped-mode switch;
 // the vehicle-only switch remains false for scenery and monitor alike.
 call.r6.u32=0;call.r8.u32=reference;call.r9.u32=point;
 call.r10.u32=monitor&&base[object+1218]==1?1:0;
 call.f1.f64=objectRadius;call.f2.f64=searchRadius;
 __imp__sub_822385C8(call,base);
 ContactCollection result;
 result.flags=U(base,flags);result.geometry.primary=int32_t(U(base,collection));
 result.geometry.closestDistance=F(base,collection+4);
 const auto count=U(base,collection+20);
 if(count>256||result.geometry.primary< -1||
    (result.geometry.primary>=0&&uint32_t(result.geometry.primary)>=count)||
    !std::isfinite(result.geometry.closestDistance))
  throw std::runtime_error("Invalid native collected contact header");
 result.geometry.samples.reserve(count);
 for(unsigned i=0;i<count;++i){
  const auto entry=collection+24+i*32,triangle=U(base,entry+8);
  if(!Ptr(triangle)||uint64_t(triangle)+68>=0xc0000000ULL)
   throw std::runtime_error("Invalid native contact triangle");
  ContactSample sample;
  sample.normal=Vec(base,triangle);sample.closestPoint=Vec(base,entry+20);
  sample.planeDistance=F(base,entry+12);sample.closestDistance=F(base,entry+16);
  for(unsigned j=0;j<3;++j)sample.triangle[j]=Vec(base,triangle+32+j*12);
  for(float value:sample.normal)if(!std::isfinite(value))throw std::runtime_error("Nonfinite native contact normal");
  for(float value:sample.closestPoint)if(!std::isfinite(value))throw std::runtime_error("Nonfinite native contact point");
  for(const auto& vertex:sample.triangle)for(float value:vertex)
   if(!std::isfinite(value))throw std::runtime_error("Nonfinite native contact vertex");
  if(!std::isfinite(sample.planeDistance)||!std::isfinite(sample.closestDistance))
   throw std::runtime_error("Nonfinite native contact metric");
  result.geometry.samples.push_back(sample);
 }
 return result;
}
// Source82235650 uses the matg SoftCeilings non-biped record for scenery too.
// Exact retail Ravine values, extracted by tools/h4-forge/extract_contact_settings.py:
// record SHA256 23864e6ed506e94f604825b25faf59b2cb3b67336a12efe86c9e88411b3a5864.
// These are original coefficients, not tuning to compensate for H3 behavior.
constexpr std::array<float,3> kH4SceneryContactSettings{20.0f,4.0f,1.0f};

std::optional<V> ResolveNativeSceneryContact(Bridge& bridge,PPCContext& ctx,uint8_t* base,
                                            uint32_t datum,V& cachedPoint){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native contact-response datum");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if((type!=6&&type!=10)||U(base,object+16)!=0xffffffff)
  throw std::runtime_error("Contact response requires an unparented scenery root");
 const auto definition=TagDefinition(base,U(base,object));
 const auto tls=U(base,ctx.r13.u32),time=Ptr(tls)?U(base,tls+0xbc):0;
 if(!definition||!Ptr(time))throw std::runtime_error("Missing native contact-response world data");
 SceneryContactWorld world;
 world.objectType=type==6?6:11;
 // Only original contact-state bit20 is read/written by the scenery branch.
 // Native counterpart820FFBE0 stores it at object172 bit19.
 world.objectFlags=(U(base,object+172)&(1u<<19))?1ull<<20:0;
 world.collisionFlags=U(base,object+276);
 world.definitionRadius=F(base,definition+4);world.tickInterval=F(base,time+8);
 world.responseSettings=kH4SceneryContactSettings;
 // The original suppression branch returns before querying motion/position.
 if(!(world.collisionFlags&4)){
  world.velocity=NativeObjectMotion(ctx,base,datum);
  world.physicsPoint=NativePhysicsPoint(ctx,base,datum);
 }
 world.collect=[&](const V& point,float radius,float search){
  return CollectNativeSceneryContacts(ctx,base,datum,point,radius,search);
 };
 world.setLinearVelocity=[&](const V& velocity){
  if(ObjectPointer(base,physicsHeaders,datum)!=object)
   throw std::runtime_error("Native contact object changed during response");
  auto call=ctx;call.r1.u32-=0x100;
  const auto backchain=std::byteswap(ctx.r1.u32);
  std::memcpy(base+call.r1.u32,&backchain,4);
  const auto input=call.r1.u32+0x60;
  for(unsigned i=0;i<3;++i){
   const auto value=std::byteswap(std::bit_cast<uint32_t>(velocity[i]));
   std::memcpy(base+input+i*4,&value,4);
  }
  call.r3.u32=datum;call.r4.u32=input;call.r5.u32=0;
  // Native setter retains its ordinary body update and wake/notification path.
  __imp__sub_820F29C8(call,base);
 };
 const auto result=bridge.ResolveSceneryContact(world,cachedPoint);
 if(ObjectPointer(base,physicsHeaders,datum)!=object)
  throw std::runtime_error("Native contact object changed before response commit");
 cachedPoint=result.cachedPoint;
 const auto flags=std::byteswap((U(base,object+172)&~(1u<<19))|
                              ((result.objectFlags&(1ull<<20))?1u<<19:0u));
 std::memcpy(base+object+172,&flags,4);
 if(result.contact)return result.normal;
 return {};
}

// Companion to the scenery response: only the editor-controlled monitor uses
// H4 biped contact response. Normal player physics remains in stock H3.
MonitorContactResult ResolveNativeMonitorContact(Bridge& bridge,PPCContext& ctx,uint8_t* base,
                                                 uint32_t datum,const V& cachedPoint,const V& previousNormal){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 const auto tls=U(base,ctx.r13.u32);
 if(!object||!Ptr(tls)||!LocalForge(base,U(base,tls+0x80))||
    base[physicsHeaders+(datum&65535)*16+3]!=0||U(base,object+16)!=0xffffffff)
  throw std::runtime_error("Monitor contact response requires a local Forge biped root");
 const auto definition=TagDefinition(base,U(base,object)),time=U(base,tls+0xbc);
 if(!definition||!Ptr(time))throw std::runtime_error("Missing native monitor contact world");
 MonitorContactWorld world;
 auto& contact=world.contact;
 contact.objectType=0;
 contact.objectFlags=(U(base,object+172)&(1u<<19))?1ull<<20:0;
 contact.collisionFlags=U(base,object+276);
 contact.definitionRadius=F(base,definition+4);contact.tickInterval=F(base,time+8);
 // Original Ravine matg record, same hash as kH4SceneryContactSettings.
 world.responseSettings={45.0f,10.0f,2.0f,4.0f};
 world.previousNormal=previousNormal;
 world.movementMode=base[object+1218];world.surfaceFlags=base[object+1323];
 world.surfaceTimestamp=U(base,object+1008);world.tick=U(base,time+12);
 world.tickRate=(uint16_t(base[time+4])<<8)|base[time+5];
 if(!(contact.collisionFlags&4)){
  contact.velocity=NativeObjectMotion(ctx,base,datum);
  contact.physicsPoint=NativePhysicsPoint(ctx,base,datum);
 }
 auto requireObject=[&]{
  if(ObjectPointer(base,physicsHeaders,datum)!=object)
   throw std::runtime_error("Native monitor changed during contact response");
 };
 contact.collect=[&](const V& center,float radius,float search){
  requireObject();return CollectNativeSceneryContacts(ctx,base,datum,center,radius,search,true);
 };
 contact.setLinearVelocity=[&](const V& velocity){
  requireObject();auto call=ctx;call.r1.u32-=0x100;
  const auto backchain=std::byteswap(ctx.r1.u32);
  std::memcpy(base+call.r1.u32,&backchain,4);
  const auto input=call.r1.u32+0x60;
  for(unsigned i=0;i<3;++i){
   const auto value=std::byteswap(std::bit_cast<uint32_t>(velocity[i]));
   std::memcpy(base+input+i*4,&value,4);
  }
  call.r3.u32=datum;call.r4.u32=input;call.r5.u32=0;
  __imp__sub_820F29C8(call,base);
 };
 world.surfaceNotification=[&]{
  requireObject();
  // Exact native820FFBE0 category-bit1 action. H4 uses82943B08 then
  //8225CBA8; both latter and native820F2A78 queue the object/parent update.
  // Keep native flag encoding and notification semantics, not H4 offsets.
  const auto flags=std::byteswap(U(base,object+276)|64u);
  std::memcpy(base+object+276,&flags,4);
  auto call=ctx;call.r3.u32=datum;__imp__sub_820F2A78(call,base);
 };
 const auto result=bridge.ResolveMonitorContact(world,cachedPoint);
 requireObject();
 const auto flags=std::byteswap((U(base,object+172)&~(1u<<19))|
                       ((result.response.objectFlags&(1ull<<20))?1u<<19:0u));
 const auto timestamp=std::byteswap(result.surfaceTimestamp);
 std::memcpy(base+object+172,&flags,4);std::memcpy(base+object+1008,&timestamp,4);
 // Only source-owned surface bit1 is changed; retain unrelated native state.
 base[object+1323]=(base[object+1323]&~2u)|(result.surfaceFlags&2u);
 return result;
}

// Source phase: native820F57A8 calls820FFBE0 for the controlled unit,
// exactly where H48297F658 calls82235650 with player140/152. Replace that
// call only; never run an additional response from the held/follow update.
bool ReplaceNativeMonitorContact(PPCContext& ctx,uint8_t* base){
 if(ctx.lr!=0x820F584C||!bridge||!enabled||failed||!PhysicsWorld(ctx,base))return false;
 const auto datum=ctx.r3.u32,object=ObjectPointer(base,physicsHeaders,datum);
 if(!object||base[physicsHeaders+(datum&65535)*16+3]!=0)return false;
 const auto player=U(base,object+380),index=player&65535;
 if(player==0xffffffff||index>=nativeEditors.size())return false;
 auto& slot=nativeEditors[index];
 if(slot.player!=player||!slot.editor||!slot.ownsMonitorContact||
    slot.contactMonitor!=datum)return false;
 const auto tls=U(base,ctx.r13.u32),pool=U(base,tls+96);
 auto* contact=PlayerContact(base,tls,player,false);
 if(!contact)throw std::runtime_error("Monitor contact has no live player state");
 const auto table=Ptr(pool)?U(base,pool+68):0;
 const uint64_t record=uint64_t(table)+index*880ull;
 if(!Ptr(table)||record+880>=0xc0000000ULL||
    U(base,uint32_t(record)+40)!=datum||ctx.r4.u32!=record+64)
  throw std::runtime_error("Monitor contact caller lost controlled-player ownership");
 // Independently require the original editor and native held record to agree.
 uint32_t held;std::memcpy(&held,slot.editor->bytes.data(),4);held=std::byteswap(held);
 const auto heldObject=ObjectPointer(base,physicsHeaders,held);
 const auto nativeSlot=U(base,physicsEngine+0xe198+index*4);
 if(!heldObject||nativeSlot>=640||U(base,physicsEngine+0x1ac+nativeSlot*0x54)!=held)
  throw std::runtime_error("Monitor contact caller lost held-object ownership");
 const auto type=base[physicsHeaders+(held&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Monitor contact replacement requires held scenery");
 const auto destination=ctx.r4.u32;
 const auto result=ResolveNativeMonitorContact(*bridge,ctx,base,datum,
                                               Vec(base,destination),contact->normalKnown?contact->normal:V{});
 // Original82235650 reads this normal only after successful824863F8,
 // which writes all three components before any read of its output.
 // Unknown restored state can therefore recover in the ordinary response
 // phase. A no-response scratch value must not become a known normal.
 for(unsigned i=0;i<3;++i){
  const auto value=std::byteswap(std::bit_cast<uint32_t>(result.response.cachedPoint[i]));
  std::memcpy(base+destination+i*4,&value,4);
 }
 if(contact->normalKnown||result.response.contact){
  contact->normal=result.response.normal;
  contact->normalKnown=true;
 }
 ctx.r3.u64=result.response.contact?1:0;
 return true;
}

// Original H4 held update explicitly queries body0 for its cached pose;
// grab initialization instead queries the instance-selected body. Keep those
// choices in the callers, not inside this shared transform reader.
std::array<float,13> NativeSceneryBodyPose(PPCContext& ctx,uint8_t* base,uint32_t datum,uint32_t index){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native scenery body datum");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Body pose requires scenery or crate");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance||index>=U(base,instance+36)||U(base,instance+36)>64)
  throw std::runtime_error("Invalid native scenery body index");
 const auto bodies=U(base,instance+32);
 const uint64_t entry=uint64_t(bodies)+index*72ull;
 if(!Ptr(bodies)||entry+72>=0xc0000000ULL)
  throw std::runtime_error("Invalid native scenery body range");
 const auto body=U(base,uint32_t(entry)+64);
 if(!Ptr(body)||uint64_t(body)+240>=0xc0000000ULL)
  throw std::runtime_error("Invalid native scenery body");
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto output=call.r1.u32+0x60;
 call.r3.u32=instance;call.r4.u32=index;call.r5.u32=output;
 __imp__sub_820FFAB0(call,base);
 std::array<float,13> result;
 for(unsigned i=0;i<result.size();++i){
  result[i]=F(base,output+i*4);
  if(!std::isfinite(result[i]))throw std::runtime_error("Nonfinite native body pose");
 }
 return result;
}
// Body callbacks used by the original H4 controller. Original constructors
// map H3 motion184 (body344) to H4 encoded motion187 (body411).
ControlledBody NativeControlledBody(PPCContext& ctx,uint8_t* base,uint32_t datum,
                                    uint32_t index,bool monitorTarget=false){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native controlled object");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(monitorTarget?type!=0:(type!=6&&type!=10))
  throw std::runtime_error("Body controller object category does not match its caller");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance||index>=U(base,instance+36)||U(base,instance+36)>64)
  throw std::runtime_error("Invalid native controlled body index");
 const auto entries=U(base,instance+32);
 if(!Ptr(entries)||uint64_t(entries)+uint64_t(index+1)*72>=0xc0000000ULL)
  throw std::runtime_error("Invalid native controlled body table");
 const auto body=U(base,entries+index*72+64);
 if(!Ptr(body)||(body&15)||uint64_t(body)+416>=0xc0000000ULL)
  throw std::runtime_error("Invalid native controlled body storage");
 const auto validate=[base,datum,object,instance,index,entries,body]{
  if(ObjectPointer(base,physicsHeaders,datum)!=object||NativePhysicsInstance(base,object)!=instance||
     U(base,instance+32)!=entries||index>=U(base,instance+36)||
     U(base,entries+index*72+64)!=body)
   throw std::runtime_error("Native controlled body changed during submission");
 };
 ControlledBody result;result.angularResponseLimit=F(base,body+344);
 for(unsigned i=0;i<4;++i){
  result.position[i]=F(base,body+224+i*4);
  result.orientation[i]=F(base,body+288+i*4);
  result.linearVelocity[i]=F(base,body+384+i*4);
  result.angularVelocity[i]=F(base,body+400+i*4);
 }
 result.activate=[&ctx,base,body,validate]{
  validate();auto call=ctx;call.r3.u32=body;
  // Original native wrapper retains fixed-body/world eligibility and wake setup.
  __imp__sub_82651968(call,base);
 };
 result.relocate=[&ctx,base,body,validate](const std::array<float,4>& position,
                                         const std::array<float,4>& orientation){
  validate();auto call=ctx;call.r1.u32-=0x100;
  const auto backchain=std::byteswap(ctx.r1.u32);
  std::memcpy(base+call.r1.u32,&backchain,4);
  const auto point=call.r1.u32+0x60,rotation=point+16;
  for(unsigned i=0;i<4;++i){
   const auto p=std::byteswap(std::bit_cast<uint32_t>(position[i]));
   const auto q=std::byteswap(std::bit_cast<uint32_t>(orientation[i]));
   std::memcpy(base+point+i*4,&p,4);std::memcpy(base+rotation+i*4,&q,4);
  }
  call.r3.u32=body;call.r4.u32=point;call.r5.u32=rotation;
  // Original wrapper dispatches the native motion's relocation and then
  //8265FB88; direct position writes would omit that follow-up.
  __imp__sub_8265FD48(call,base);
 };
 const auto setMotion=[&ctx,base,body,validate](uint32_t slot,const std::array<float,4>& value){
  validate();const auto table=U(base,body+160);
  if(!Ptr(table))throw std::runtime_error("Invalid native motion dispatch table");
  auto* function=REX_KERNEL_STATE()->function_dispatcher()->GetFunction(U(base,table+slot));
  if(!function)throw std::runtime_error("Missing native motion setter");
  auto call=ctx;call.r1.u32-=0x100;
  const auto backchain=std::byteswap(ctx.r1.u32);
  std::memcpy(base+call.r1.u32,&backchain,4);
  const auto input=call.r1.u32+0x60;
  for(unsigned i=0;i<4;++i){
   const auto word=std::byteswap(std::bit_cast<uint32_t>(value[i]));
   std::memcpy(base+input+i*4,&word,4);
  }
  // Native82629000 uses these slots with motion receiver body160.
  // Resolve the actual motion vtable; do not assume all classes use82662340/50.
  call.r3.u32=body+160;call.r4.u32=input;function(call,base);
 };
 result.setLinearVelocity=[setMotion](const std::array<float,4>& value){setMotion(60,value);};
 result.setAngularVelocity=[setMotion](const std::array<float,4>& value){setMotion(64,value);};
 return result;
}

// Original82452930 scenery routing: no instance or invalid signed selected
// index means no submission. Do not silently choose body0 or move all bodies.
// Returned H4 owner flags still require explicit native notification mapping.
// H482939248 requires8298E798(root,true), then instance16 bit3.
//8298E798 tests EarlyMoverLocalizedPhysics;824A2B38 refreshes instance bit3
// from the selected body's motion4. Native82269088 selects the same body but
// does not maintain that flag, so derive it from the corresponding body6.
bool NativeAttachmentCompensationEligible(uint8_t* base,uint32_t root){
 const auto object=ObjectPointer(base,physicsHeaders,root);
 if(!object||U(base,object+16)!=0xffffffff)return false;
 const auto definition=TagDefinition(base,U(base,object));
 if(!definition)throw std::runtime_error("Missing attachment root definition");
 // Object flags: H4 definition28 bit11 -> H3 definition2 bit7.
 if(!(H(base,definition+2)&(1u<<7)))return false;
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return false;
 const auto count=U(base,instance+36);
 const int selected=int8_t(base[instance+12]);
 if(selected<0)return false;
 if(count>64||uint32_t(selected)>=count)
  throw std::runtime_error("Invalid attachment root selected body");
 const auto entries=U(base,instance+32);
 const uint64_t entry=uint64_t(entries)+uint32_t(selected)*72ull;
 if(!Ptr(entries)||entry+72>=0xc0000000ULL)
  throw std::runtime_error("Invalid attachment root body table");
 const auto body=U(base,uint32_t(entry)+64);
 if(!Ptr(body)||uint64_t(body)+169>=0xc0000000ULL)
  throw std::runtime_error("Invalid attachment root body");
 return base[body+168]==6;
}

void RememberControllerAttachment(uint8_t* base,uint32_t datum,uint64_t flags){
 if(!(flags&(1ull<<30))||!NativeAttachmentCompensationEligible(base,datum)){
  controllerAttachments.erase(datum);return;
 }
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 controllerAttachments[datum]={object,NativePhysicsInstance(base,object)};
}
std::optional<std::array<float,13>> NativeCompensatedAttachment(PPCContext& ctx,uint8_t* base){
 if(ctx.lr!=0x82331858||controllerAttachments.empty()||!bridge||failed||!enabled||
    !PhysicsWorld(ctx,base))return {};
 const auto child=ctx.r3.u32,object=ObjectPointer(base,physicsHeaders,child);
 const auto attachment=nativeDetachAttachment;
 if(!attachment||attachment->datum!=child)return {};
 if(!object||object!=attachment->object)
  throw std::runtime_error("Controlled-root attachment child changed during detach");
 const auto parent=attachment->parent;
 if(parent==0xffffffff)return {};
 uint32_t root=parent,rootObject=0;
 for(unsigned depth=0;depth<65536;++depth){
  rootObject=ObjectPointer(base,physicsHeaders,root);
  if(!rootObject)throw std::runtime_error("Invalid controlled-root attachment ancestor");
  const auto next=U(base,rootObject+16);
  if(next==0xffffffff)break;
  if(next==root||next==child||depth==65535)
   throw std::runtime_error("Cyclic controlled-root attachment ancestry");
  root=next;
 }
 const auto entry=controllerAttachments.find(root);
 if(entry==controllerAttachments.end())return {};
 if(entry->second.object!=rootObject||entry->second.instance!=NativePhysicsInstance(base,rootObject)){
  controllerAttachments.erase(entry);return {};
 }
 if(!NativeAttachmentCompensationEligible(base,root))return {};
 auto nodeAddress=[&](uint32_t owner,int index){
  const auto bytes=H(base,owner+314);
  const int offset=int16_t(H(base,owner+316));
  if(index<0||offset<0||uint32_t(index+1)*52>bytes)
   throw std::runtime_error("Invalid native attachment node index");
  const uint64_t address=uint64_t(owner)+uint32_t(offset)+uint32_t(index)*52ull;
  if(address+52>=0xc0000000ULL)throw std::runtime_error("Invalid native attachment node address");
  return uint32_t(address);
 };
 const auto parentObject=ObjectPointer(base,physicsHeaders,parent);
 if(!parentObject)throw std::runtime_error("Invalid native attachment parent");
 const auto node=nodeAddress(parentObject,attachment->node);
 if(node!=ctx.r4.u32)throw std::runtime_error("Unexpected native attachment transform argument");
 const auto rootNode=nodeAddress(rootObject,0);
 std::array<float,13> rootPose,parentPose;
 for(unsigned i=0;i<13;++i){rootPose[i]=F(base,rootNode+i*4);parentPose[i]=F(base,node+i*4);}
 const auto velocity=NativeObjectVelocities(ctx,base,root);
 const auto tls=U(base,ctx.r13.u32),time=U(base,tls+188);
 if(!Ptr(time))throw std::runtime_error("Missing attachment simulation time");
 return bridge->CompensateAttachmentPose(rootPose,parentPose,velocity[0],velocity[1],F(base,time+8));
}

std::optional<uint64_t> SubmitNativeSceneryTarget(Bridge& bridge,PPCContext& ctx,uint8_t* base,
                         uint32_t datum,const std::array<float,13>& pose,float parameter){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native controller target");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Target submission requires scenery or crate");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return {};
 const int selected=int8_t(base[instance+12]);
 const auto count=U(base,instance+36);
 if(selected<0||uint32_t(selected)>=count)return {};
 if(count>64)throw std::runtime_error("Invalid native target body count");
 const auto body=NativeControlledBody(ctx,base,datum,uint32_t(selected));
 const auto flags=bridge.ControlBody(pose,parameter,body);
 RememberControllerAttachment(base,datum,flags);return flags;
}

// H4 body-entry56 bit0 maps to native68 bit0: original constructors
//824A4D20 and8226AE28 both assign it from their seventh argument. The
// native entry has an additional12-byte array before the shared fields.
std::optional<uint64_t> SubmitNativeMonitorTarget(Bridge& bridge,PPCContext& ctx,uint8_t* base,
                         uint32_t datum,const std::array<float,13>& pose,float parameter){
 const auto tls=U(base,ctx.r13.u32);
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!Ptr(tls)||!LocalForge(base,U(base,tls+0x80))||!object||
    base[physicsHeaders+(datum&65535)*16+3]!=0||U(base,object+16)!=0xffffffff)
  throw std::runtime_error("Monitor target requires a local unparented biped");
 for(float value:pose)if(!std::isfinite(value))throw std::runtime_error("Nonfinite monitor target");
 if(!std::isfinite(parameter)||parameter<=0)throw std::runtime_error("Invalid monitor controller parameter");
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return {};
 const auto count=U(base,instance+36),entries=U(base,instance+32);
 if(count>64||(count&&(!Ptr(entries)||uint64_t(entries)+uint64_t(count)*72>=0xc0000000ULL)))
  throw std::runtime_error("Invalid native monitor body table");
 bool upright=false;
 for(uint32_t i=0;i<count;++i)upright|=(base[entries+i*72+68]&1)!=0;
 auto submission=pose;
 if(upright){
  V facing;
  submission=bridge.PrepareActiveBipedTarget(pose,facing);
  SubmitNativeMonitorOrientation(ctx,base,datum,facing);
 }
 // Original82452930 performs the orientation branch before checking the
 // selected body. Preserve that ordering even when no controller is submitted.
 if(ObjectPointer(base,physicsHeaders,datum)!=object||NativePhysicsInstance(base,object)!=instance)
  throw std::runtime_error("Monitor changed during orientation notification");
 const int selected=int8_t(base[instance+12]);
 if(selected<0||uint32_t(selected)>=U(base,instance+36))return {};
 const auto body=NativeControlledBody(ctx,base,datum,uint32_t(selected),true);
 const auto flags=bridge.ControlBody(submission,parameter,body);
 RememberControllerAttachment(base,datum,flags);return flags;
}

std::vector<uint32_t> NativeSelectionRayExclusions(PPCContext& ctx,uint8_t* base){
 if(!PhysicsWorld(ctx,base))throw std::runtime_error("Selection exclusions require local Forge");
 const auto tls=U(base,ctx.r13.u32),array=U(base,tls+168);
 const auto count=U(base,array+56),stride=U(base,array+36),headers=U(base,array+68);
 // Native82332608 validates indices against array56 and uses stride36.
 // H482268800 walks the same ascending header order and ignores zero salts.
 if(stride!=16||count>65536||!Ptr(headers)||uint64_t(headers)+uint64_t(count)*16>=0xc0000000ULL)
  throw std::runtime_error("Invalid native selection object table");
 std::vector<uint32_t> result;result.reserve(64);
 for(uint32_t index=0;index<count&&result.size()<64;++index){
  const auto header=headers+index*16;
  const auto salt=H(base,header);
  if(!salt||base[header+3]!=0)continue;
  const auto object=U(base,header+12);
  if(!Ptr(object))throw std::runtime_error("Invalid native selection biped");
  const auto definition=TagDefinition(base,U(base,object));
  if(!definition||uint64_t(definition)+676>=0xc0000000ULL)
   throw std::runtime_error("Invalid native selection biped definition");
  // Original8244C740 excludes ONLY seatless bipeds. H4 unit1364 Seats
  // count maps to stock H3 unit672; retain the original signed comparison.
  if(static_cast<int32_t>(U(base,definition+672))<1)
   result.push_back((uint32_t(salt)<<16)|index);
 }
 return result;
}

struct NativeSelectionHit {
 uint32_t category=0,datum=0xffffffff;
 float fraction=1;
 V point{},normal{};
};
// Native-world service only: callers must map H4 request flags explicitly.
// H3 consumes a displacement, not an endpoint, and its hit identity is at60
// rather than H4 batch-result40. Keep the two result layouts separate.
std::optional<NativeSelectionHit> NativeSelectionRay(PPCContext& ctx,uint8_t* base,
                       uint64_t nativeMask,uint8_t mode,const V& origin,const V& displacement,
                       const std::vector<uint32_t>& exclusions){
 if(!PhysicsWorld(ctx,base)||exclusions.size()>64)
  throw std::runtime_error("Invalid native Forge selection query");
 for(const auto& vector:{origin,displacement})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite native selection ray");
 for(const auto datum:exclusions)
  if(datum==0xffffffff||!ObjectPointer(base,physicsHeaders,datum))
   throw std::runtime_error("Invalid native selection exclusion");
 //820AD3E0 probes and allocates17504 bytes below its entry stack. Reserve
 // our inputs above that frame, beyond the native outgoing argument area.
 if(ctx.r1.u32<0x5000||ctx.r1.u32>=0xc0000000u)
  throw std::runtime_error("Invalid native selection query stack");
 auto call=ctx;call.r1.u32-=0x200;
 const auto frame=call.r1.u32,start=frame+0x80,delta=frame+0x90,output=frame+0xa0;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+frame,&backchain,4);
 for(unsigned i=0;i<3;++i){
  const auto a=std::byteswap(std::bit_cast<uint32_t>(origin[i]));
  const auto b=std::byteswap(std::bit_cast<uint32_t>(displacement[i]));
  std::memcpy(base+start+i*4,&a,4);std::memcpy(base+delta+i*4,&b,4);
 }
 std::memset(base+output,0,96);
 call.r3.u64=nativeMask;call.r4.u32=mode;
 call.r5.u32=start;call.r6.u32=delta;
 call.r7.u32=call.r8.u32=call.r9.u32=0xffffffff;
 call.r10.u32=output;
 SelectionRayExclusionScope scope(exclusions);
 __imp__sub_820AD3E0(call,base);
 if(!(call.r3.u32&255))return {};
 NativeSelectionHit hit;
 hit.category=U(base,output);hit.fraction=F(base,output+4);
 hit.point=Vec(base,output+8);
 //82281268 copies result36/40/44 into its native surface-normal cache.
 hit.normal=Vec(base,output+36);
 if(hit.category==4)hit.datum=U(base,output+60);
 if(!std::isfinite(hit.fraction))throw std::runtime_error("Nonfinite native selection fraction");
 for(const auto& vector:{hit.point,hit.normal})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite native selection hit");
 if(hit.category==4&&!ObjectPointer(base,physicsHeaders,hit.datum))
  throw std::runtime_error("Invalid native selection hit object");
 return hit;
}

std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)>
NativeMonitorObstructionQuery(PPCContext& ctx,uint8_t* base){
 return [context=ctx,base](const SelectionRayRequest& request) mutable ->std::optional<SelectionRayHit>{
  // Original83292E30/83292E50 initialize highword1009, lowword0;
  //824F5E28 uses layer27. Surface selector high bit12 maps to native bit11
  // (82416120 versus820ADFE0). Keep native H3 world geometry services.
  if(request.layer!=27||request.flags!=0x0000100900000000ull)
   throw std::runtime_error("Unmapped monitor obstruction query contract");
  V displacement;
  for(unsigned i=0;i<3;++i)
   displacement[i]=float(double(request.endpoint[i])-double(request.origin[i]));
  const auto hit=NativeSelectionRay(context,base,0x0000080900000000ull,0,
                                  request.origin,displacement,request.exclusions);
  if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
   const auto tls=U(base,context.r13.u32),time=Ptr(tls)?U(base,tls+188):0;
   if(Ptr(time)){
    const auto tick=U(base,time+12);
    static thread_local uint32_t last=0xffffffff;
    if(last==0xffffffff||tick<last||tick-last>=30){
     REXLOG_INFO("Forge monitor obstruction: tick {} origin {},{},{} endpoint {},{},{} hit {} category {} datum {:08X} fraction {} exclusions {}",
      tick,request.origin[0],request.origin[1],request.origin[2],request.endpoint[0],request.endpoint[1],request.endpoint[2],
      bool(hit),hit?hit->category:0,hit?hit->datum:0xffffffff,hit?hit->fraction:1.f,request.exclusions.size());
     last=tick;
    }
   }
  }
  if(!hit)return {};
  return SelectionRayHit{hit->category,hit->datum,hit->point,hit->fraction};
 };
}

SelectionRayWorld NativeSelectionRayWorld(PPCContext& ctx,uint8_t* base,uint32_t monitor,uint32_t held,
                                         std::optional<NativeSelectionHit>* captured=nullptr){
 if(!PhysicsWorld(ctx,base))throw std::runtime_error("Selection ray requires local Forge");
 SelectionRayWorld world;
 world.origin=NativeSelectionOrigin(ctx,base,monitor);
 world.direction=NativeMonitorRotationView(base,monitor);
 world.exclusions=NativeSelectionRayExclusions(ctx,base);
 if(held!=0xffffffff){
  const auto object=ObjectPointer(base,physicsHeaders,held);
  if(!object||(base[object+154]!=6&&base[object+154]!=10))
   throw std::runtime_error("H4 selection ray requires a scenery held object");
  // Native82281268 reads the held variant slot at24; H4 uses62.
  world.heldVariantSlot=static_cast<int16_t>(H(base,object+24));
 }
 world.query=[context=ctx,base,captured](const SelectionRayRequest& request) mutable ->std::optional<SelectionRayHit>{
  if(request.layer!=26||request.flags!=0x000000090000179full)
   throw std::runtime_error("Unmapped H4 selection ray contract");
  V displacement;
  for(unsigned i=0;i<3;++i)
   displacement[i]=float(double(request.endpoint[i])-double(request.origin[i]));
  // Stock H3 Forge82281268 world/surface flags are retained. The shared
  // object-category mask maps H4 crate11->H3 crate10 and includes controls
  // and bipeds; dispenser has no native H3 category. H4's hcfd layer table
  // is not copied onto H3's differently defined physics groups. Native
  // collision eligibility is the explicit stock-H3 integration boundary.
  constexpr uint64_t nativeMask=0x0010000900000b9full;
  const auto hit=NativeSelectionRay(context,base,nativeMask,0,request.origin,displacement,request.exclusions);
  if(captured)*captured=hit;
  if(!hit)return {};
  return SelectionRayHit{hit->category,hit->datum,hit->point,hit->fraction};
 };
 return world;
}

struct NativeSceneryOwner {uint32_t monitor,localIndex;};
NativeSceneryOwner ResolveNativeSceneryOwner(PPCContext& ctx,uint8_t* base,
                                            uint32_t player,uint32_t held,
                                            bool allowAttached=false){
 if(player==0xffffffff||(player&65535)>=16||!PhysicsWorld(ctx,base))
  throw std::runtime_error("Invalid native scenery owner");
 const auto tls=U(base,ctx.r13.u32);
 // Ownership needs a live salted player record, not a collision sample.
 const auto contact=PlayerContact(base,tls,player,false);
 if(!contact)throw std::runtime_error("Missing native scenery player lifetime");
 const auto slot=U(base,physicsEngine+0xe198+(player&65535)*4);
 if(slot>=640||U(base,physicsEngine+0x1ac+slot*0x54)!=held)
  throw std::runtime_error("Native scenery holder changed");
 const auto heldObject=ObjectPointer(base,physicsHeaders,held);
 if(!heldObject||(!allowAttached&&U(base,heldObject+16)!=0xffffffff)||
    (base[physicsHeaders+(held&65535)*16+3]!=6&&base[physicsHeaders+(held&65535)*16+3]!=10))
  throw std::runtime_error("Native scenery ownership has invalid scenery or attachment");
 const auto monitor=U(base,contact->record+40);
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object||base[physicsHeaders+(monitor&65535)*16+3]!=0||
    U(base,object+16)!=0xffffffff||U(base,object+380)!=player)
  throw std::runtime_error("Native scenery monitor ownership changed");
 const auto controls=U(base,tls+120);
 if(!Ptr(controls)||uint64_t(controls)+4*236>=0xc0000000ULL)
  throw std::runtime_error("Invalid local scenery controls");
 uint32_t localIndex=0xffffffff;
 for(uint32_t i=0;i<4;++i)if(U(base,controls+i*236+16)==monitor){
  if(localIndex!=0xffffffff)throw std::runtime_error("Ambiguous local scenery control owner");
  localIndex=i;
 }
 if(localIndex==0xffffffff)throw std::runtime_error("Scenery owner has no local control slot");
 return {monitor,localIndex};
}
// Read the contact snapshot produced in the native unit-update phase.
// Never recompute contact here: that would apply its velocity response twice.
MonitorFollowWorld NativeMonitorFollowWorld(PPCContext& ctx,uint8_t* base,
                                            uint32_t player,uint32_t monitor){
 if(player==0xffffffff||(player&65535)>=nativeEditors.size()||!PhysicsWorld(ctx,base))
  throw std::runtime_error("Invalid native monitor-follow owner");
 const auto& slot=nativeEditors[player&65535];
 const auto object=ObjectPointer(base,physicsHeaders,monitor);
 if(!object||slot.player!=player||!slot.editor||!slot.ownsMonitorContact||
    slot.contactMonitor!=monitor||U(base,object+380)!=player)
  throw std::runtime_error("Monitor-follow contact state is not initialized for this owner");
 MonitorFollowWorld world;
 world.contactActive=(U(base,object+172)&(1u<<19))!=0;
 // Original8244AF48 gates player152..160 on object256 bit20 before
 // loading the normal. Native bit19 is that contact flag. An inactive
 // contact needs identity only; the private scratch normal is unread.
 const auto contact=PlayerContact(base,U(base,ctx.r13.u32),player,world.contactActive);
 if(!contact)throw std::runtime_error("Monitor-follow player contact lifetime or active normal is missing");
 world.contactNormal=world.contactActive?contact->normal:V{};
 world.query=NativeMonitorObstructionQuery(ctx,base);
 return world;
}

HeldSelectionWorld NativeHeldSelectionWorld(PPCContext& ctx,uint8_t* base,uint32_t player,
                                           bool localHolder,const std::function<void(const std::string&)>& eventSink){
 if(player==0xffffffff||(player&65535)>=16||!PhysicsWorld(ctx,base)||!eventSink)
  throw std::runtime_error("Invalid native held selection world");
 HeldSelectionWorld world;world.localHolder=localHolder;world.eventSink=eventSink;
 world.objectPoint=[context=ctx,base](uint32_t datum) mutable {
  return NativePhysicsPoint(context,base,datum);
 };
 world.objectReferenceVector=[context=ctx,base](uint32_t datum) mutable {
  return NativeObjectOrigin(context,base,datum);
 };
 world.focusObject=[context=ctx,base,player](uint32_t requested){
  if(requested!=player)throw std::runtime_error("Held selection player changed");
  const auto tls=U(base,context.r13.u32),players=Ptr(tls)?U(base,tls+96):0;
  const auto table=Ptr(players)?U(base,players+68):0;
  const uint64_t record=uint64_t(table)+(player&65535)*880ull;
  if(!Ptr(table)||record+880>=0xc0000000ULL)
   throw std::runtime_error("Invalid native selection player table");
  //82505DE8(player,false) reads H4 player36: the controlled unit,
  // not the selected object or an aiming/raycast result. Native uses40.
  const auto unit=U(base,uint32_t(record)+40);
  if(unit!=0xffffffff&&!ObjectPointer(base,physicsHeaders,unit))
   throw std::runtime_error("Invalid native selection controlled unit");
  return unit;
 };
 return world;
}

NativeEditorSlot& NativeEditor(Bridge& original,PPCContext& ctx,uint8_t* base,uint32_t player,
                               const std::function<void(const std::string&)>& eventSink){
 if(player==0xffffffff||(player&65535)>=nativeEditors.size()||!PhysicsWorld(ctx,base))
  throw std::runtime_error("Invalid native editor owner");
 auto& slot=nativeEditors[player&65535];
 if(slot.player!=player||!slot.editor){
  // Zero backing allocation is not the initialized editor. Execute original
  //82449DD8 to establish its sentinels, defaults, vectors and event.
  const std::array<uint8_t,336> storage{};
  auto initialized=original.InitializeHeldEditorState(storage,eventSink);
  // Player contact data has a separate allocation lifetime. Constructing an
  // editor must not reset it, including after a world/editor reset.
  if(slot.player!=player){slot=NativeEditorSlot{};slot.player=player;}
  slot.editor=std::move(initialized);
 }
 return slot;
}
std::vector<uint32_t> SelectNativeHeldEditor(Bridge& original,PPCContext& ctx,uint8_t* base,
                            uint32_t player,uint32_t datum,bool localHolder,
                            const std::function<void(const std::string&)>& eventSink){
 auto& slot=NativeEditor(original,ctx,base,player,eventSink);
 const auto world=NativeHeldSelectionWorld(ctx,base,player,localHolder,eventSink);
 // Selection is a transaction stage, never a frame update. Passing -1 runs
 // original release/reset while retaining original preference fields.
 auto visible=original.SelectHeldObject(*slot.editor,player,datum,world);
 if(datum==0xffffffff){
  // Original82449ED8 resets editor fields, not player1888..1907.
  // The input producer82368CE0 owns active/axis updates, including its
  // deliberate retention of axis values when eligibility or trigger fails.
  slot.ownsMonitorContact=false;slot.contactMonitor=0xffffffff;
  ClearPlayerAnchors(player);
 }
 return visible;
}

// Build one synchronous held-update world from native services. Ownership is
// supplied by the native holder transaction; it must not be inferred from a
// camera/player index. Each callback owns a context copy so nested original
// calls cannot overwrite the caller's registers or borrow a dead stack object.
HeldUpdateWorld NativeHeldUpdateWorld(Bridge& original,PPCContext& ctx,uint8_t* base,
                                     uint32_t held,uint32_t monitor,bool localHolder){
 if(!PhysicsWorld(ctx,base))throw std::runtime_error("Native held world requires local Forge");
 const auto object=ObjectPointer(base,physicsHeaders,held);
 if(!object||(base[object+154]!=6&&base[object+154]!=10)||U(base,object+16)!=0xffffffff)
  throw std::runtime_error("Native held world requires unparented scenery");
 const auto tls=U(base,ctx.r13.u32),time=Ptr(tls)?U(base,tls+188):0;
 if(!Ptr(time))throw std::runtime_error("Missing native held simulation time");
 const auto instance=NativePhysicsInstance(base,object);
 HeldUpdateWorld world;
 world.localHolder=localHolder;world.hasInstance=instance!=0;
 world.bodyCount=instance?U(base,instance+36):0;
 world.tick=U(base,time+12);world.tickInterval=F(base,time+8);
 world.monitorDatum=monitor;world.desiredView=NativeMonitorDesiredView(base,monitor);
 world.movementFlag=NativeMonitorMovementFlag(base,monitor);
 const auto boost=ReadNativeMonitorBoost(ctx,base,monitor);
 world.definitionMovementMultiplier=boost.peakPower;world.movementMultiplierFraction=boost.fraction;
 world.variantBounds=NativeVariantBounds(base);
 world.heldDefinitionRadius=NativeHeldDefinitionRadius(base,held);
 world.objectMotion=[context=ctx,base](uint32_t datum) mutable {
  return NativeObjectMotion(context,base,datum);
 };
 world.objectVelocities=[context=ctx,base](uint32_t datum) mutable {
  return NativeObjectVelocities(context,base,datum);
 };
 world.objectReferencePoint=[context=ctx,base](uint32_t datum) mutable {
  return NativeHeldReferencePoint(context,base,datum);
 };
 world.objectPhysicsPoint=[context=ctx,base](uint32_t datum) mutable {
  return NativePhysicsPoint(context,base,datum);
 };
 world.objectPredictionLocalPoint=[base](uint32_t datum){
  return NativePredictionLocalPoint(base,datum);
 };
 world.objectOrientation=[context=ctx,base](uint32_t datum) mutable {
  return NativeObjectOrientation(context,base,datum);
 };
 world.pointOutsideWorld=[context=ctx,base](const V& point) mutable {
  return NativeHeldWorldPointBlocked(context,base,point);
 };
 world.geometryContainsObject=[context=ctx,base](uint32_t datum) mutable {
  return NativeHeldGeometryBlocked(context,base,datum);
 };
 world.bodyTransform=[context=ctx,base,held](uint32_t index) mutable {
  return NativeSceneryBodyPose(context,base,held,index);
 };
 world.resolveContact=[context=ctx,base,&original](uint32_t datum,V& cachedPoint) mutable {
  return ResolveNativeSceneryContact(original,context,base,datum,cachedPoint);
 };
 return world;
}

// Commit ownership only after original selection/physics/grab placement and
// native holder/dequeue have completed. Do not synthesize another contact
// response here: the unit phase has already run for the current frame.
void ActivateNativeSceneryHold(PPCContext& ctx,uint8_t* base,uint32_t player,uint32_t datum){
 // Original grab keeps selection even when its detach predicate is false.
 // The held tick independently skips movement/follow while attached.
 const auto owner=ResolveNativeSceneryOwner(ctx,base,player,datum,true);
 auto& slot=nativeEditors[player&65535];
 if(slot.player!=player||!slot.editor)
  throw std::runtime_error("Scenery activation lacks initialized editor");
 uint32_t selected;std::memcpy(&selected,slot.editor->bytes.data(),4);
 if(std::byteswap(selected)!=datum)
  throw std::runtime_error("Scenery activation selection mismatch");
 const auto object=physicsObjects.find(datum);
 if(object==physicsObjects.end()||!PhysicsValid(base,datum,object->second))
  throw std::runtime_error("Scenery activation lacks original physics metadata");
 // ResolveNativeSceneryOwner validates the allocation-lifetime contact cache,
 // controlled monitor and local input slot before either ownership field changes.
 slot.contactMonitor=owner.monitor;
 slot.ownsMonitorContact=true;
}

void PublishNativeHeldAnchors(PPCContext& ctx,uint8_t* base,uint32_t localIndex,
                              uint32_t player,const Scene& scene,const HeldUpdateResult& result){
 if(localIndex>=4||scene.objects.empty())throw std::runtime_error("Invalid marker view owner");
 const auto tls=U(base,ctx.r13.u32),observers=U(base,tls+716);
 if(!Ptr(observers)){ClearPlayerAnchors(player);return;}
 // Native82141300 and821421E4: observer stride968, result position272.
 // TLS604 is a separately allocated one-byte state, not an observer block.
 const auto camera=uint64_t(observers)+localIndex*968+272;
 if(camera+12>=0xc0000000ULL)throw std::runtime_error("Invalid marker camera address");
 AnchorView view;view.player=player;view.updated=std::chrono::steady_clock::now();view.time=float(physicsTick)/30.f;
 view.camera.position=Vec(base,uint32_t(camera));
 for(float value:view.camera.position)if(!std::isfinite(value)){
  ClearPlayerAnchors(player);return;
 }
 for(const auto datum:result.visibleObjects){
  // Visibility outlives one nearby query. Never append an old target to the
  // candidate scene just to draw it: that would change original query order.
  if(!ObjectPointer(base,physicsHeaders,datum))continue;
  const auto data=ReadNativeMarkerData(*bridge,base,datum);
  for(const auto& marker:data.rootMarkers){
   VisibleAnchor anchor;anchor.datum=datum;anchor.held=datum==scene.objects.front().datum;
   // Re-read the live node/permutation transform after controller submission.
   // This also covers retained visible targets absent from scene.objects.
   for(unsigned i=0;i<3;++i){
    uint32_t bits;std::memcpy(&bits,marker.data()+0x60+i*4,4);
    anchor.position[i]=std::bit_cast<float>(std::byteswap(bits));
    if(!std::isfinite(anchor.position[i]))throw std::runtime_error("Nonfinite visible marker");
   }
   view.anchors.push_back(anchor);
  }
 }
 std::lock_guard lock(anchorMutex);anchorViews[localIndex]=std::move(view);
}

// Coupled local stage from8244D5CC..D618. The enclosing native tick owns
// selection/eligibility; the stage collects the current native scene. This is not a
// replacement for the native prefix/suffix or a second magnet evaluation.
HeldUpdateResult RunNativeCoupledSceneryStage(PPCContext& ctx,uint8_t* base,
    uint32_t player,uint32_t datum,uint32_t monitor,uint32_t localIndex){
 if(!bridge||!PhysicsWorld(ctx,base)||player==0xffffffff||(player&65535)>=16||
    localIndex>=4||!NativeCoupledSceneryEligible(base,datum))
  throw std::runtime_error("Invalid coupled scenery stage");
 const auto owner=ResolveNativeSceneryOwner(ctx,base,player,datum);
 if(owner.monitor!=monitor||owner.localIndex!=localIndex)
  throw std::runtime_error("Coupled scenery local ownership changed");
 auto& slot=nativeEditors[player&65535];
 const auto nativeSlot=U(base,physicsEngine+0xe198+(player&65535)*4);
 const auto monitorObject=ObjectPointer(base,physicsHeaders,monitor);
 const auto tls=U(base,ctx.r13.u32),controls=U(base,tls+120);
 if(slot.player!=player||!slot.editor||nativeSlot>=640||
    U(base,physicsEngine+0x1ac+nativeSlot*0x54)!=datum||!monitorObject||
    U(base,monitorObject+380)!=player||!Ptr(controls)||
    U(base,controls+localIndex*236+16)!=monitor)
  throw std::runtime_error("Coupled scenery ownership changed");
 uint32_t selected;std::memcpy(&selected,slot.editor->bytes.data(),4);
 if(std::byteswap(selected)!=datum)
  throw std::runtime_error("Coupled scenery original selection changed");
 // Validate contact lifetime before the rotation/contact/controller stages
 // mutate anything. Re-read the actual contact snapshot at follow time.
 NativeMonitorFollowWorld(ctx,base,player,monitor);
 auto world=NativeHeldUpdateWorld(*bridge,ctx,base,datum,monitor,true);
 const bool traceMotion=!REXCVAR_GET(halo3mp_advanced_forge_trace).empty();
 const auto incomingVelocity=traceMotion?NativeObjectMotion(ctx,base,datum):V{};
 RotateNativeScenery(ctx,base,*slot.editor,monitor,slot.input);
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 bridge->AdvanceHeldPlacement(*slot.editor,slot.input,F(base,object+44));
 // H4 initializes editor+82 to false (82449DD8); its magnet caller
 // 8244EED8 skips selection until the editor preference enables it.
 // Map Spartan's existing controls into private H4 state, not H3 save data.
 slot.editor->bytes[82]=enabled.load()?1:0;
 const auto magnetSensitivity=std::byteswap(uint32_t(sensitivity.load()));
 std::memcpy(slot.editor->bytes.data()+268,&magnetSensitivity,4);
 const auto scene=BuildNativeMagnetScene(*bridge,ctx,base,*slot.editor,datum,monitor);
 // Observe the callbacks actually consumed by this held update. Do not run
 // contact response a second time merely to diagnose its result.
 bool geometryBlocked=false,heldContact=false;
 V heldContactNormal{};
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  const auto geometryQuery=world.geometryContainsObject;
  world.geometryContainsObject=[&,geometryQuery](uint32_t id){return geometryBlocked=geometryQuery(id);};
  const auto contactQuery=world.resolveContact;
  world.resolveContact=[&,contactQuery](uint32_t id,V& point){
   auto result=contactQuery(id,point);
   heldContact=result.has_value();heldContactNormal=result.value_or(V{});
   return result;
  };
 }
 auto held=bridge->UpdateHeld(*slot.editor,scene,world);
 if(held.submitted){
  if(held.submittedDatum!=datum)
   throw std::runtime_error("Original held stage submitted a different object");
  SubmitNativeSceneryTarget(*bridge,ctx,base,datum,held.pose,held.controllerParameter);
 }
 // Original follow runs after the scenery controller, so its world queries
 // see any body/velocity changes from that submission.
 const auto followWorld=NativeMonitorFollowWorld(ctx,base,player,monitor);
 const auto follow=bridge->UpdateMonitorFollow(*slot.editor,scene,world,followWorld);
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  struct TraceState{uint32_t datum=0xffffffff,target=0xffffffff,tick=0;bool moving=false;};
  static thread_local std::array<TraceState,16> traced;
  auto& prior=traced[player&65535];
  const bool moving=std::any_of(scene.processedMovement.begin(),scene.processedMovement.end(),[](float v){return v!=0;});
  if(prior.datum!=datum||prior.target!=held.targetDatum||prior.moving!=moving||world.tick<prior.tick||world.tick-prior.tick>=30){
   REXLOG_INFO("Forge held flow: tick {} held {:08X} target {:08X} moving {} movement {},{},{} submitted {} pose {},{},{} candidates {}",
    world.tick,datum,held.targetDatum,moving,scene.processedMovement[0],scene.processedMovement[1],scene.processedMovement[2],held.submitted,
    held.pose[10],held.pose[11],held.pose[12],scene.nearbyOrder?scene.nearbyOrder->size():scene.objects.size());
   std::array<float,3> unsnapped{};
   for(unsigned axis=0;axis<3;++axis){
    uint32_t word;std::memcpy(&word,slot.editor->bytes.data()+124+axis*4,4);
    unsnapped[axis]=std::bit_cast<float>(std::byteswap(word));
   }
   const auto monitorPoint=NativePhysicsPoint(ctx,base,monitor);
   const auto heldPoint=NativePhysicsPoint(ctx,base,datum);
   const auto heldVelocity=NativeObjectMotion(ctx,base,datum);
   REXLOG_INFO("Forge held actual: tick {} center {},{},{} velocity {},{},{}",
    world.tick,heldPoint[0],heldPoint[1],heldPoint[2],heldVelocity[0],heldVelocity[1],heldVelocity[2]);
   REXLOG_INFO("Forge held incoming velocity: tick {} velocity {},{},{}",
    world.tick,incomingVelocity[0],incomingVelocity[1],incomingVelocity[2]);
   REXLOG_INFO("Forge held constraints: tick {} geometry {} contact {} normal {},{},{}",
    world.tick,geometryBlocked,heldContact,heldContactNormal[0],heldContactNormal[1],heldContactNormal[2]);
   const auto heldInstance=NativePhysicsInstance(base,object);
   const int heldBodyIndex=heldInstance?int8_t(base[heldInstance+12]):-1;
   if(heldBodyIndex>=0&&uint32_t(heldBodyIndex)<U(base,heldInstance+36)){
    const auto heldBody=U(base,U(base,heldInstance+32)+uint32_t(heldBodyIndex)*72+64);
    if(Ptr(heldBody)){
     const auto rawPosition=Vec(base,heldBody+224);
     const auto rawVelocity=Vec(base,heldBody+384);
     REXLOG_INFO("Forge held physics: tick {} flags {:08X} body {} motion {} raw position {},{},{} raw velocity {},{},{}",
      world.tick,U(base,object+172),heldBodyIndex,unsigned(base[heldBody+168]),
      rawPosition[0],rawPosition[1],rawPosition[2],rawVelocity[0],rawVelocity[1],rawVelocity[2]);
     // Native8265F4F0 stores constructor f2/f3 at motion180/184.
     REXLOG_INFO("Forge held motion limits: tick {} linear {} angular {}",
      world.tick,F(base,heldBody+340),F(base,heldBody+344));
    }
   }
   REXLOG_INFO("Forge held reference: tick {} unsnapped {},{},{} monitor {},{},{}",
    world.tick,unsnapped[0],unsnapped[1],unsnapped[2],monitorPoint[0],monitorPoint[1],monitorPoint[2]);
   REXLOG_INFO("Forge held bounds: tick {} X [{},{}] Y [{},{}] Z [{},{}]",
    world.tick,world.variantBounds[0],world.variantBounds[1],world.variantBounds[2],
    world.variantBounds[3],world.variantBounds[4],world.variantBounds[5]);
   REXLOG_INFO("Forge held accumulation: tick {} prior {},{},{} delta {},{},{} reference {},{},{}",
    world.tick,held.priorTarget[0],held.priorTarget[1],held.priorTarget[2],
    held.movementDelta[0],held.movementDelta[1],held.movementDelta[2],
    held.referencePoint[0],held.referencePoint[1],held.referencePoint[2]);
   REXLOG_INFO("Forge follow request: tick {} submitted {} target {},{},{} parameter {} contact {} normal {},{},{}",
    world.tick,follow.submitted,follow.pose[10],follow.pose[11],follow.pose[12],follow.controllerParameter,
    followWorld.contactActive,followWorld.contactNormal[0],followWorld.contactNormal[1],followWorld.contactNormal[2]);
   // One overwritten raw scene for inspecting actual marker positions.
   // Cursor/basis are not populated for standalone selector replay here.
   if(scene.objects.size()>1)SaveScene(REXCVAR_GET(halo3mp_advanced_forge_trace),scene);
   prior={datum,held.targetDatum,world.tick,moving};
  }
 }

 if(follow.submitted){
  if(follow.submittedDatum!=monitor)
   throw std::runtime_error("Original follow stage submitted a different monitor");
  SubmitNativeMonitorTarget(*bridge,ctx,base,monitor,follow.pose,follow.controllerParameter);
 }
 if(follow.viewDirection)
  SubmitNativeMonitorView(ctx,base,localIndex,monitor,*follow.viewDirection);
 PublishNativeHeldAnchors(ctx,base,localIndex,player,scene,held);
 // Native menus keep their own distance cache. Original editor state remains
 // authoritative, including unsnapped target and the previous magnet pair.
 std::memcpy(base+physicsEngine+0xe1d8+(player&65535)*4,slot.editor->bytes.data()+28,4);
 return held;
}

// H4 82452820 scenery branch: selected-body transform, then object transform.
// This query is distinct from the center returned by NativePhysicsPoint.
// Native body reader820FFAB0 corresponds to H4 822AD348; native object
// reader820D8FA0 corresponds to H4 82251B38, including parent transforms.
std::array<float,13> NativeSceneryGrabPose(PPCContext& ctx,uint8_t* base,uint32_t datum){
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native scenery pose datum");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Grab pose requires scenery or crate");
 const auto instance=NativePhysicsInstance(base,object);
 int selected=-1;
 if(instance){
  selected=int8_t(base[instance+12]);
  if(selected<0||uint32_t(selected)>=U(base,instance+36))selected=-1;
 }
 if(selected>=0)return NativeSceneryBodyPose(ctx,base,datum,uint32_t(selected));
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto output=call.r1.u32+0x60;
 call.r3.u32=datum;call.r4.u32=output;
 __imp__sub_820D8FA0(call,base);
 std::array<float,13> result;
 for(unsigned i=0;i<result.size();++i){
  result[i]=F(base,output+i*4);
  if(!std::isfinite(result[i]))throw std::runtime_error("Nonfinite native scenery pose");
 }
 return result;
}
struct NativeSceneryInput {
 uint32_t held=0xffffffff;
 ManipulationInput value;
};
// Read before native821F04C0 consumes the frame packet. Eligibility remains
// stock H3; only scenery/crate input is eligible for the H4 manipulation path.
std::optional<NativeSceneryInput> ReadNativeSceneryInput(PPCContext& ctx,uint8_t* base,
                                                       uint32_t player,uint32_t packet){
 if(player==0xffffffff||(player&65535)>=16||!Ptr(packet)||uint64_t(packet)+116>=0xc0000000ULL)
  throw std::runtime_error("Invalid native manipulation frame");
 if(!PhysicsWorld(ctx,base))return {};
 auto call=ctx;call.r1.u32-=0x100;
 const auto backchain=std::byteswap(ctx.r1.u32);
 std::memcpy(base+call.r1.u32,&backchain,4);
 const auto heldOutput=call.r1.u32+0x60;
 const uint32_t none=0xffffffff;
 std::memcpy(base+heldOutput,&none,4);
 call.r3.u32=player;call.r4.u32=heldOutput;call.r5.u32=0;
 __imp__sub_820B06A0(call,base);
 if(!(call.r3.u32&255))return {};
 NativeSceneryInput result;
 result.held=U(base,heldOutput);
 const auto object=ObjectPointer(base,physicsHeaders,result.held);
 if(!object)return {};
 const auto type=base[physicsHeaders+(result.held&65535)*16+3];
 if(type!=6&&type!=10)return {};
 result.value.eligible=true;result.value.hasHeldObject=true;
 // Both original unit producers copy these semantic forward/left axes
 // without inversion. The H4 distance consumer intentionally subtracts
 // forward input; do not compensate for H3's different distance consumer.
 result.value.movement={F(base,packet+20),F(base,packet+24)};
 result.value.trigger=F(base,packet+44);
 result.value.rotationAvailable=base[packet+28]!=0;
 // Native82281A98 and H4 8244A7D0 pass first/second look as f1/f2,
 // and negate the second movement axis as f3. Preserve those input signs;
 // original H4 rotation constructs its own axes and applies the roll negation.
 if(result.value.rotationAvailable)result.value.look={F(base,packet+32),F(base,packet+36)};
 return result;
}
// Replacement stage for the native edit-input producer, once the complete
// held lifecycle is wired. True means the caller must skip821F04C0; false
// preserves stock H3 handling for every non-scenery/invalid editing context.
bool ConsumeNativeSceneryInput(PPCContext& ctx,uint8_t* base,uint32_t player,
                                uint32_t packet,ManipulationInputState& persistent){
 const auto frame=ReadNativeSceneryInput(ctx,base,player,packet);
 if(!frame){persistent.active=false;return false;}
 if(!bridge)throw std::runtime_error("Original H4 input bridge unavailable");
 const auto& editor=nativeEditors[player&65535];
 if(editor.player!=player||!editor.editor||!editor.ownsMonitorContact||
    &persistent!=&editor.input)
  throw std::runtime_error("Scenery input lacks original lifecycle ownership");
 uint32_t selected;std::memcpy(&selected,editor.editor->bytes.data(),4);
 if(std::byteswap(selected)!=frame->held)
  throw std::runtime_error("Scenery input refers to a different held object");
 const auto tls=U(base,ctx.r13.u32),pool=U(base,tls+96);
 if(!Ptr(pool))throw std::runtime_error("Invalid native player pool");
 const auto entries=U(base,pool+68);
 const uint64_t address=uint64_t(entries)+(player&65535)*880ull;
 if(!Ptr(entries)||address+880>=0xc0000000ULL)
  throw std::runtime_error("Invalid native player input record");
 const auto result=bridge->ConsumeManipulationInput(persistent,frame->value);
 // The original H4 producer consumes only these movement components.
 // Leave look/trigger/action data for ordinary native processing unchanged.
 for(unsigned i=0;i<2;++i){
  const auto value=std::byteswap(std::bit_cast<uint32_t>(result.remainingMovement[i]));
  std::memcpy(base+packet+20+i*4,&value,4);
 }
 // H4 private state owns edit distance/rotation now. Disarm the old H3
 // consumer rather than allowing it to apply a second distance change.
 base[uint32_t(address)+764]=0;
 persistent=result.state;
 return true;
}
// Collect post-transition world data for the bridge's grab initializer.
// Distance input must already have a source-backed H4 mapping; do not
// substitute raw keys. Radius comes from the live native bounding sphere.
GrabPlacement NativeGrabPlacement(PPCContext& ctx,uint8_t* base,uint32_t datum,
                                   uint32_t monitor,bool inputActive,float distanceInput){
 if(!PhysicsWorld(ctx,base))throw std::runtime_error("Grab world is not native local Forge");
 const auto object=ObjectPointer(base,physicsHeaders,datum);
 if(!object)throw std::runtime_error("Invalid native grab object");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Grab world requires scenery or crate");
 GrabPlacement result;
 result.datum=datum;
 const auto instance=NativePhysicsInstance(base,object);
 result.hasBodies=instance&&U(base,instance+36)!=0;
 if(!result.hasBodies)return result;
 result.pose=NativeSceneryGrabPose(ctx,base,datum);
 result.variantBounds=NativeVariantBounds(base);
 result.heldPoint=NativePhysicsPoint(ctx,base,datum);
 result.monitorPoint=NativePhysicsPoint(ctx,base,monitor);
 result.monitorForward=NativeObjectOrientation(ctx,base,monitor)[0];
 // H3 runtime sphere32/44 corresponds to H4 sphere64/76. This is
 // the live radius, not822835E0's authored model-placement radius.
 result.radius=F(base,object+44);
 if(!std::isfinite(result.radius)||result.radius<0)
  throw std::runtime_error("Invalid native runtime bounding radius");
 result.inputActive=inputActive;result.distanceInput=distanceInput;
 return result;
}
// Only active during the original H4 transition's native create/rebuild call.
// H4 runtime keyframed4 maps to H3 runtime keyframed6; this is not a world
// disconnect. Other objects and ordinary H3 body creation remain untouched.
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
 // Explicit restoration must override the retained editor request too.
 if(sceneryBodyConstruction&&sceneryBodyConstruction->datum==datum)return sceneryBodyConstruction;
 const auto found=physicsObjects.find(datum);
 if(found==physicsObjects.end()||!found->second.keyframedOverride||
    !PhysicsValid(base,datum,found->second))return {};
 // H3 can rebuild a body again after the original transition has returned.
 // Its flags have no H4 force-keyframed bit, so retain that request through
 // the same native constructor boundary until the original transition clears it.
 return SceneryBodyConstruction{datum,true};
}
PhysicsBodyUpdate RebuildSceneryPhysics(PPCContext& ctx,uint8_t* base,uint32_t datum,
                                       PhysicsObject& object,uint64_t h4Flags,bool create){
 // Original823885D0 and native821CB5B8 traverse parents before body
 // construction; retained attachments are not an invalid transition.
 if(!PhysicsValid(base,datum,object))
  throw std::runtime_error("Invalid scenery physics transition object");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Physics transition requires scenery or crate");
 const auto definition=TagDefinition(base,object.tag);
 if(!definition||(H(base,definition+2)&(1u<<11)))
  throw std::runtime_error("Authored object disallows Forge physics override");
 const auto oldFlags=U(base,object.pointer+172);
 // Source mapping: H4 frozen6 -> H3 frozen6; H4 force-dynamic21 -> H3 bit20.
 // Bit22 is consumed by the scoped native body constructor below.
 auto nativeFlags=oldFlags&~(kFrozen|kForceDynamic);
 if(h4Flags&(1ull<<6))nativeFlags|=kFrozen;
 if(h4Flags&(1ull<<21))nativeFlags|=kForceDynamic;
 auto encoded=std::byteswap(nativeFlags);
 std::memcpy(base+object.pointer+172,&encoded,4);
 object.keyframedOverride=(h4Flags&(1ull<<22))!=0;
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty())
  REXLOG_INFO("Forge physics rebuild: datum {:08X} original flags {:016X} keyframed {} create {}",datum,h4Flags,object.keyframedOverride,create);
 SceneryBodyConstructionScope scope(datum,object.keyframedOverride);
 auto call=ctx;call.r3.u32=datum;call.r4.u32=create?1:0;
 if(create){call.r5.u32=1;__imp__sub_821CBB88(call,base);}
 else __imp__sub_821CB8D8(call,base);
 if(!PhysicsValid(base,datum,object))throw std::runtime_error("Scenery invalidated during physics rebuild");
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  const auto instance=NativePhysicsInstance(base,object.pointer);
  if(instance){
   const auto count=U(base,instance+36),entries=U(base,instance+32);
   if(count>64||(count&&!Ptr(entries)))throw std::runtime_error("Invalid rebuilt scenery body table");
   for(uint32_t i=0;i<count;++i){
    const auto body=U(base,entries+i*72+64);
    if(!Ptr(body)||uint64_t(body)+416>=0xc0000000ULL)throw std::runtime_error("Invalid rebuilt scenery body");
    REXLOG_INFO("Forge rebuilt body: datum {:08X} index {} selected {} address {:08X} motion {}",datum,i,int8_t(base[instance+12]),body,base[body+168]);
   }
  }
 }
 // H4 queries the selected physics-body point, not the object origin.
 // Native820AFA98 preserves selected-body and fixed-body query semantics.
 const auto point=NativePhysicsPoint(ctx,base,datum);
 for(float component:point)if(!std::isfinite(component))
  throw std::runtime_error("Nonfinite native physics-body point");
 PhysicsBodyUpdate result{h4Flags,point,U(base,object.pointer+160)!=0xffffffff};
 const auto actual=U(base,object.pointer+172);
 result.flags&=~((1ull<<6)|(1ull<<10)|(1ull<<21));
 if(actual&kFrozen)result.flags|=1ull<<6;
 if(actual&(1u<<9))result.flags|=1ull<<10;
 if(actual&kForceDynamic)result.flags|=1ull<<21;
 return result;
}
// H482939248 resets overrides after pose/visibility reconnection, before
// body activation and velocity. Only the prepared scenery grab owns this stage.
void ResetNativeDetachPhysics(PPCContext& ctx,uint8_t* base){
 auto* attachment=nativeDetachAttachment;
 auto* grab=nativeGrabTransaction;
 if(!attachment||!attachment->deferVelocity||attachment->physicsReset||
    !grab||grab->datum!=attachment->datum||!grab->error.empty()||failed||
    !enabled.load()||!bridge)return;
 try{
  // Visibility reconnection can delete an out-of-world object. Resolve its
  // salted identity again before accessing either runtime or private state.
  const auto datum=attachment->datum;
  const auto pointer=ObjectPointer(base,physicsHeaders,datum);
  auto found=physicsObjects.find(datum);
  if(!pointer||pointer!=attachment->object||found==physicsObjects.end()||
     !PhysicsValid(base,datum,found->second)||U(base,pointer+16)!=0xffffffff)
   throw std::runtime_error("Detached scenery invalidated before physics reset");
  const auto flags=U(base,pointer+172);
  const bool overrides=(flags&(kFrozen|kForceDynamic))||found->second.keyframedOverride;
  // Original rebuild accumulator starts with the PRE-unlink connected flag;
  // current override bits additionally force rebuild. Preserve other H3 flags.
  if(attachment->rebuildAfterUnlink||overrides)
   RebuildSceneryPhysics(ctx,base,datum,found->second,0,false);
  attachment->physicsReset=true;
 }catch(const std::exception& e){grab->error=e.what();}
}
// Native boundary for the entire original8244A2A0 transition, including its
// post-rebuild flag and held-offset writes. The lifecycle supplies the state
// from original8244A180 and the confirmed native holder; this function does
// not infer ownership or replace the native variant/deferred-release transaction.
PhysicsTransition TransitionNativeSceneryPhysics(Bridge& original,PPCContext& ctx,
    uint8_t* base,uint32_t datum,PhysicsObject& object,uint32_t state,
    bool localHolder,HeldEditorState* heldEditor){
 // The caller synchronizes PhysicsWorld before obtaining this map entry.
 // Do not clear physicsObjects here while holding a reference into it.
 const auto tls=U(base,ctx.r13.u32);
 if(state>3||!Ptr(tls)||!LocalForge(base,U(base,tls+0x80))||
    U(base,tls+0x64)!=physicsEngine||!PhysicsValid(base,datum,object))
  throw std::runtime_error("Invalid native scenery transition");
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if(type!=6&&type!=10)throw std::runtime_error("Native transition requires scenery");
 const auto definition=TagDefinition(base,object.tag);
 if(!definition||(H(base,definition+2)&(1u<<11)))
  throw std::runtime_error("Authored object disallows Forge physics override");
 const auto model=TagDefinition(base,U(base,definition+0x40));
 const auto phmo=model?TagDefinition(base,U(base,model+0x3c)):0;
 const auto flags=U(base,object.pointer+172);
 if(heldEditor){
  uint32_t selected;std::memcpy(&selected,heldEditor->bytes.data(),4);
  if(std::byteswap(selected)!=datum)
   throw std::runtime_error("Original editor holds a different scenery object");
 }
 PhysicsTransition current;
 current.state=state;current.held=heldEditor!=nullptr;
 current.localHolder=localHolder;current.hasPhysicsModel=phmo!=0;
 current.hasInstance=NativePhysicsInstance(base,object.pointer)!=0;
 if(flags&kFrozen)current.flags|=1ull<<6;
 if(flags&(1u<<9))current.flags|=1ull<<10;
 if(flags&kForceDynamic)current.flags|=1ull<<21;
 if(object.keyframedOverride)current.flags|=1ull<<22;
 // Every valid state rewrites H4 bit22 before rebuilding. Keep its prior
 // request as private state for other lifecycle consumers, never an H3 flag.
 if(current.held&&current.hasPhysicsModel)
  current.point=NativePhysicsPoint(ctx,base,datum);
 auto update=[&](uint64_t requested,bool create){
  return RebuildSceneryPhysics(ctx,base,datum,object,requested,create);
 };
 auto result=heldEditor?original.TransitionHeldPhysics(*heldEditor,current,update):
                         original.TransitionPhysics(current,update);
 if(!PhysicsValid(base,datum,object))
  throw std::runtime_error("Scenery invalidated during original transition");
 // Original sets H4 bit10 AFTER rebuild when frozen. Both velocity readers
 // (H4 82260CF0 / H3 820AC960) consume this gate; the native counterpart is
 // bit9. Preserve every other native flag, including changes made by rebuild.
 const auto actual=U(base,object.pointer+172);
 const auto updated=(actual&~(1u<<9))|((result.flags&(1ull<<10))?(1u<<9):0u);
 const auto encoded=std::byteswap(updated);
 std::memcpy(base+object.pointer+172,&encoded,4);
 return result;
}
void RestoreRuntimePhysics(PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,
                           bool frozen,bool forceDynamic){
 if(!PhysicsValid(base,datum,object))return;
 const bool removeKeyframed=object.keyframedOverride;
 // An editor-forced keyframed body may have the same native flags as its
 // authored body. Clearing private metadata alone cannot restore that body.
 // Disable our constructor override for this datum throughout restoration.
 SceneryBodyConstructionScope authoredConstruction(datum,false);
 const auto before=U(base,object.pointer+0xac);
 const auto changed=frozen?(before|kFrozen):(before&~kFrozen);
 if(changed!=before){auto value=std::byteswap(changed);std::memcpy(base+object.pointer+0xac,&value,4);}
 // Retail 822D3A58 rebuilds after changing the freeze bit. Force-dynamic's
 // original setter already rebuilds when its bit changes, so do not do twice.
 if(bool(before&kForceDynamic)!=forceDynamic)
  PhysicsCall(ctx,base,datum,__imp__sub_8232EB28,forceDynamic);
 else if(changed!=before||removeKeyframed)
  PhysicsCall(ctx,base,datum,__imp__sub_821CB8D8);
 // Keep this true if a rebuild throws, so a later restoration can retry.
 object.keyframedOverride=false;
}
bool PhysicsHeld(uint8_t* base,uint32_t datum){
 for(unsigned i=0;i<16;++i){const auto slot=U(base,physicsEngine+0xe198+i*4);
  if(slot<640&&U(base,physicsEngine+0x1ac+slot*0x54)==datum)return true;
 }return false;
}
// Mode is the existing editor property; native H3 variant bytes are never
// interpreted as H4's flags. Read native ownership only after its transaction
// has committed, then execute original8244A180 followed by8244A2A0.
uint32_t SelectNativeSceneryPhysics(Bridge& original,
    PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,
    PhysicsMode mode,HeldEditorState* heldEditor){
 if(!PhysicsValid(base,datum,object))
  throw std::runtime_error("Invalid scenery physics selection");
 const bool held=PhysicsHeld(base,datum);
 if(held!=(heldEditor!=nullptr))
  throw std::runtime_error("Native holder transaction disagrees with original editor");
 const auto variantSlot=H(base,object.pointer+24);
 const bool variantObject=variantSlot!=65535;
 if(variantObject&&(variantSlot>=640||
    U(base,physicsEngine+0x1ac+variantSlot*0x54)!=datum))
  throw std::runtime_error("Native scenery variant slot does not identify this object");
 bool keyframed=false,normalOverride=false;
 // Match the original selector's predicate branches. The authored body query
 // is not the current runtime motion class, which grabbing may have changed.
 if(variantObject&&!held&&(mode==PhysicsMode::Fixed||mode==PhysicsMode::Phased)){
  const auto authored=AuthoredKeyframedBody(base,object.pointer);
  if(!authored)throw std::runtime_error("Invalid authored physics body table");
  keyframed=*authored;
 }else if(variantObject&&!held&&mode==PhysicsMode::Normal){
  // Native8227EB28 preserves session/state gates as well as queue membership.
  // A raw queue bit alone is insufficient for original8244A5F0's boundary.
  if(U(base,physicsEngine+59560)>64)
   throw std::runtime_error("Invalid native deferred-release queue");
  auto query=ctx;query.r3.u32=datum;__imp__sub_8227EB28(query,base);
  normalOverride=(query.r3.u32&255)!=0;
 }
 return original.SelectPhysicsState(mode,held,keyframed,normalOverride,variantObject);
}
PhysicsTransition SelectAndTransitionNativeSceneryPhysics(Bridge& original,
    PPCContext& ctx,uint8_t* base,uint32_t datum,PhysicsObject& object,
    PhysicsMode mode,bool localHolder,HeldEditorState* heldEditor){
 const auto state=SelectNativeSceneryPhysics(original,ctx,base,datum,object,mode,heldEditor);
 return TransitionNativeSceneryPhysics(original,ctx,base,datum,object,state,localHolder,heldEditor);
}
// Post-ownership grab stage: native822800B0 must already have assigned the
// holder and removed the object from the deferred queue. The outer lifecycle
// must call this instead of the old forced-dynamic/distance workaround, and
// arm monitor contact only after the complete held tick is installed.
bool InitializeNativeSceneryHold(Bridge& original,PPCContext& ctx,uint8_t* base,
    uint32_t player,uint32_t datum,PhysicsMode mode,
    const std::function<void(const std::string&)>& eventSink){
 if(player==0xffffffff||(player&65535)>=16||!PhysicsWorld(ctx,base))
  throw std::runtime_error("Invalid native scenery grab owner");
 const auto nativeSlot=U(base,physicsEngine+0xe198+(player&65535)*4);
 if(nativeSlot>=640||U(base,physicsEngine+0x1ac+nativeSlot*0x54)!=datum)
  throw std::runtime_error("Scenery grab precedes native ownership commit");
 const auto count=U(base,physicsEngine+59560);
 if(count>64)throw std::runtime_error("Invalid native deferred-release queue");
 for(uint32_t i=0;i<count;++i)
  if(U(base,physicsEngine+58536+i*4)==datum)
   throw std::runtime_error("Scenery grab precedes native dequeue");
 const auto selection=NativeHeldSelectionWorld(ctx,base,player,true,eventSink);
 const auto monitor=selection.focusObject(player);
 auto& slot=nativeEditors[player&65535];
 // Original selection/reset must run BEFORE native dequeue, at the inner
 // ownership boundary. Never manufacture/reset selection here afterwards.
 if(slot.player!=player||!slot.editor)
  throw std::runtime_error("Scenery grab lacks original selection state");
 uint32_t selected;std::memcpy(&selected,slot.editor->bytes.data(),4);
 if(std::byteswap(selected)!=datum)
  throw std::runtime_error("Scenery grab disagrees with original selection");
 // Input state belongs to the player; do not reset it on a re-grab.
 const auto object=physicsObjects.find(datum);
 if(object==physicsObjects.end()||!PhysicsValid(base,datum,object->second))
  throw std::runtime_error("Scenery grab lacks pre-grab physics metadata");
 SelectAndTransitionNativeSceneryPhysics(original,ctx,base,datum,object->second,
                                       mode,true,&*slot.editor);
 const auto placement=NativeGrabPlacement(ctx,base,datum,monitor,
                                          slot.input.active,slot.input.distance);
 const auto initialized=original.InitializeGrabPlacement(*slot.editor,placement);
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  uint32_t distanceWord;std::memcpy(&distanceWord,slot.editor->bytes.data()+28,4);
  const float distance=std::bit_cast<float>(std::byteswap(distanceWord));
  REXLOG_INFO("Forge grab placement: held {:08X} point {},{},{} monitor {},{},{} forward {},{},{} radius {} distance {} initialized {}",
   datum,placement.heldPoint[0],placement.heldPoint[1],placement.heldPoint[2],
   placement.monitorPoint[0],placement.monitorPoint[1],placement.monitorPoint[2],
   placement.monitorForward[0],placement.monitorForward[1],placement.monitorForward[2],placement.radius,distance,initialized);
 }
 return initialized;
}
// Original82451250 performs selection reset first, native pose/velocity/queue
// release next, then8244A180 ->8244A2A0. This is ONLY the last physics stage;
// callers must establish successful local release, not merely a return from
// the native release routine (which can instead queue a network request).
void FinalizeNativeSceneryRelease(Bridge& original,PPCContext& ctx,uint8_t* base,
                                  uint32_t player,uint32_t datum){
 if(player==0xffffffff||(player&65535)>=16||!PhysicsWorld(ctx,base))
  throw std::runtime_error("Invalid native scenery release owner");
 const auto& slot=nativeEditors[player&65535];
 if(slot.player!=player||!slot.editor)
  throw std::runtime_error("Scenery release lacks original selection state");
 uint32_t selected;std::memcpy(&selected,slot.editor->bytes.data(),4);
 if(std::byteswap(selected)!=0xffffffff||slot.ownsMonitorContact||
    slot.contactMonitor!=0xffffffff)
  throw std::runtime_error("Scenery release precedes original selection reset");
 if(U(base,physicsEngine+0xe198+(player&65535)*4)!=0xffffffff||
    PhysicsHeld(base,datum))
  throw std::runtime_error("Scenery release precedes native ownership clear");
 const auto object=physicsObjects.find(datum);
 if(object==physicsObjects.end()||!PhysicsValid(base,datum,object->second))
  throw std::runtime_error("Scenery release lacks surviving physics metadata");
 const auto pointer=object->second.pointer;
 if(base[pointer+154]!=6&&base[pointer+154]!=10)
  throw std::runtime_error("Scenery release requires scenery");
 const auto mode=object->second.mode.value_or(object->second.authoredMode);
 // Query native deferred-release membership AFTER its enqueue. Normal mode
 // depends on this state; a held-mode transition here would use the wrong arm.
 SelectAndTransitionNativeSceneryPhysics(original,ctx,base,datum,object->second,
                                        mode,true,nullptr);
 object->second.originalReleasedPhysics=true;
}
HeldEditorState* OwnedOriginalSceneryEditor(uint32_t datum){
 HeldEditorState* result=nullptr;
 for(auto& slot:nativeEditors){
  if(!slot.editor||!slot.ownsMonitorContact)continue;
  uint32_t held;std::memcpy(&held,slot.editor->bytes.data(),4);
  if(std::byteswap(held)!=datum)continue;
  if(result)throw std::runtime_error("Multiple original editors own one scenery object");
  result=&*slot.editor;
 }
 return result;
}
bool EligibleKeyframedSceneryPose(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!bridge||failed||!OwnedOriginalSceneryEditor(datum)||!PhysicsWorld(ctx,base))return false;
 const auto found=physicsObjects.find(datum);
 if(found==physicsObjects.end()||!found->second.keyframedOverride||
    !PhysicsValid(base,datum,found->second))return false;
 const auto object=found->second.pointer;
 const auto type=base[physicsHeaders+(datum&65535)*16+3];
 if((type!=6&&type!=10)||U(base,object+16)!=0xffffffff)return false;
 const auto instance=NativePhysicsInstance(base,object);
 if(!instance)return false;
 const int selected=int8_t(base[instance+12]);
 if(selected<0||uint32_t(selected)>=U(base,instance+36))return false;
 const auto entries=U(base,instance+32);
 if(!Ptr(entries))return false;
 const auto body=U(base,entries+uint32_t(selected)*72+64);
 return Ptr(body)&&base[body+168]==6;
}
// Bounded provenance for native writers that can supersede the original H4
// controller. Observe only; never suppress a native synchronization operation.
void TraceNativeHeldWriter(PPCContext& ctx,uint8_t* base,uint32_t datum,const char* kind){
 if(REXCVAR_GET(halo3mp_advanced_forge_trace).empty()||!OwnedOriginalSceneryEditor(datum))return;
 const auto tls=U(base,ctx.r13.u32),time=Ptr(tls)?U(base,tls+188):0;
 if(!Ptr(time))return;
 const auto tick=U(base,time+12);
 struct Entry{uint32_t datum=0xffffffff,caller=0,tick=0;const char* kind=nullptr;};
 static thread_local std::array<Entry,16> records{};
 auto found=std::find_if(records.begin(),records.end(),[&](const Entry& e){return e.datum==datum&&e.caller==ctx.lr&&e.kind==kind;});
 if(found==records.end()){
  found=std::min_element(records.begin(),records.end(),[](const Entry& a,const Entry& b){return a.tick<b.tick;});
 }else if(tick>=found->tick&&tick-found->tick<30)return;
 REXLOG_INFO("Forge native writer: tick {} held {:08X} kind {} caller {:08X}",tick,datum,kind,uint32_t(ctx.lr));
 *found={datum,uint32_t(ctx.lr),tick,kind};
}
void ApplyPhysics(PPCContext& ctx,uint8_t* base,uint32_t datum){
 auto it=physicsObjects.find(datum);
 if(it==physicsObjects.end()||!it->second.mode||!PhysicsValid(base,datum,it->second))return;
 const auto mode=*it->second.mode;
 auto* editor=OwnedOriginalSceneryEditor(datum);
 if(editor||it->second.originalReleasedPhysics){
  if(!bridge)throw std::runtime_error("Original scenery physics lost original bridge");
  SelectAndTransitionNativeSceneryPhysics(*bridge,ctx,base,datum,it->second,mode,true,editor);
  return;
 }
 // Metadata capture is not ownership. A pending native grab/create still
 // belongs to its native transaction until original selection is installed.
 // Never substitute freeze/disconnect for the missing original transition.
}
// Original824515C8 snapshots the selected runtime state before editing the
// property and only transitions when the new selection differs. Comparing
// menu labels alone would miss cases where two modes select the same state.
void ChangeNativeSceneryPhysicsMode(PPCContext& ctx,uint8_t* base,uint32_t datum,
                                    PhysicsMode requested){
 auto it=physicsObjects.find(datum);
 if(!bridge||it==physicsObjects.end()||!PhysicsValid(base,datum,it->second))
  throw std::runtime_error("Physics property changed without valid scenery metadata");
 auto& object=it->second;
 const auto previous=object.mode.value_or(object.authoredMode);
 auto* editor=OwnedOriginalSceneryEditor(datum);
 // The original selector validates held ownership before the menu value
 // changes. Unheld scenery is valid even if it has never been grabbed here.
 const auto before=SelectNativeSceneryPhysics(*bridge,ctx,base,datum,object,previous,editor);
 object.mode=static_cast<PhysicsMode>(bridge->EditPhysics(static_cast<uint16_t>(previous),requested)&0xc0);
 const auto after=SelectNativeSceneryPhysics(*bridge,ctx,base,datum,object,*object.mode,editor);
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty())
  REXLOG_INFO("Forge physics property: datum {:08X} mode {:02X}->{:02X} state {}->{}",datum,static_cast<uint16_t>(previous),static_cast<uint16_t>(*object.mode),before,after);
 if(after!=before)
  TransitionNativeSceneryPhysics(*bridge,ctx,base,datum,object,after,true,editor);
 if(!editor)object.originalReleasedPhysics=true;
}
void SyncPhysicsPose(PPCContext& ctx,uint8_t* base,uint32_t datum,const PhysicsObject& object){
 if(!PhysicsValid(base,datum,object)||U(base,object.pointer+0x10)!=0xffffffff)return;
 const auto slot=H(base,object.pointer+0x18);
 if(slot>=640)return;
 const auto record=physicsEngine+0x1a8+slot*0x54;
 if(U(base,record+4)!=datum)return;
 // Retail 820A9E58/820B1928 read these unparented pose vectors. Only ask
 // H3 to serialize them when they differ; no per-frame redundant save writes.
 if(std::memcmp(base+object.pointer+0x54,base+record+0x10,36)==0)return;
 auto sync=ctx;sync.r3.u32=0;sync.r4.u32=datum;__imp__sub_82284078(sync,base);
}
void RestorePhysics(PPCContext& ctx,uint8_t* base){
 // This is the existing global restoration path (exit/error), not a release.
 // Revoke editor/contact/controller ownership before native rebuild callbacks
 // can run. Keeping these slots alive would route later unit input/contact
 // through a held lifecycle whose physics metadata has already been erased.
 ClearNativeEditors();controllerAttachments.clear();
 coordinates.Reset();physics.Reset();
 fixedSnap=0xffffffff;ClearAnchorWorld();
 if(!PhysicsWorld(ctx,base)){
  physicsObjects.clear();physics.Reset();coordinates.Reset();ClearAnchors();return;
 }
 restoringPhysics=true;
 struct RestoreGuard{~RestoreGuard(){restoringPhysics=false;}} guard;
 for(auto& [datum,object]:physicsObjects){
  if(!object.mode||!PhysicsValid(base,datum,object))continue;
  RestoreRuntimePhysics(ctx,base,datum,object,bool(object.original&kFrozen),
                        bool(object.original&kForceDynamic));
  SyncPhysicsPose(ctx,base,datum,object);
  REXLOG_INFO("Advanced Forge physics restored: {:08X} flags {:08X} original {:08X}",datum,U(base,object.pointer+0xac),object.original);
 }
 physicsObjects.clear();physics.Reset();coordinates.Reset();ClearAnchors();
}
void UpdatePhysics(PPCContext& ctx,uint8_t* base,uint32_t datum){
 if(!PhysicsWorld(ctx,base))return;
 auto it=physicsObjects.find(datum);
 if(it==physicsObjects.end()||!PhysicsValid(base,datum,it->second)){physics.Reset();return;}
 auto& object=it->second;
 auto mode=object.mode.value_or(object.authoredMode);
 auto request=physics.Update(datum,mode);
 const auto test=REXCVAR_GET(halo3mp_advanced_forge_test_physics);
 if(!test.empty()){
  if(REXCVAR_GET(halo3mp_advanced_forge_trace).empty()||REXCVAR_QUERY(std::string,input_state_replay).empty())
   throw std::runtime_error("Diagnostic physics requires exclusive replay and scene tracing");
  static uint32_t startTick=physicsTick;static size_t lastStep=~size_t(0);
  const size_t step=(physicsTick-startTick)/90; // native 30 Hz simulation
  if(step!=lastStep){
   std::istringstream sequence(test);std::string name;
   for(size_t i=0;i<=step&&std::getline(sequence,name,',');++i)if(i==step){
    if(name=="normal")request=PhysicsMode::Normal;
    else if(name=="fixed")request=PhysicsMode::Fixed;
    else if(name=="phased")request=PhysicsMode::Phased;
    else throw std::runtime_error("Unknown diagnostic physics mode");
   }
   lastStep=step;
  }
 }
 if(request){
  ChangeNativeSceneryPhysicsMode(ctx,base,datum,*request);
  physics.Publish(datum,*object.mode);
  REXLOG_INFO("Advanced Forge physics selected: {:08X} mode {:02X} flags {:08X} held {}",datum,static_cast<uint16_t>(*object.mode),U(base,object.pointer+0xac),PhysicsHeld(base,datum));
 }
}
std::optional<CoordinatePose> Evaluate(PPCContext& ctx,uint8_t* base,bool livePose=false){
 if(nativePoseSyncDatum&&*nativePoseSyncDatum==(livePose?ctx.r3.u32:ctx.r4.u32))return {};
 if(restoringPhysics)return {};
 if(livePose&&placementDepth)return {};
 if(!enabled.load()&&!coordinates.Locked()&&REXCVAR_GET(halo3mp_advanced_forge_test_coordinates).empty()&&REXCVAR_GET(halo3mp_advanced_forge_test_physics).empty())return {};
 if(failed)return {};
 uint32_t tls=U(base,ctx.r13.u32);if(!Ptr(tls))return {};
 static thread_local bool wasLocalForge=false;
 if(!LocalForge(base,U(base,tls+0x80))){
  if(wasLocalForge){
   coordinates.Reset();physics.Reset();physicsObjects.clear();
   ClearNativeEditors();controllerAttachments.clear();fixedSnap=0xffffffff;
   ClearAnchorWorld();wasLocalForge=false;
  }
  return {};
 }
 wasLocalForge=true;
 uint32_t engine=U(base,tls+0x64);if(!Ptr(engine))return {};
 uint32_t datum=livePose?ctx.r3.u32:ctx.r4.u32;
 uint32_t position=livePose?ctx.r4.u32:ctx.r5.u32;
 uint32_t forward=livePose?ctx.r5.u32:ctx.r6.u32;
 uint32_t up=livePose?ctx.r6.u32:ctx.r7.u32;
 static bool reportedEntry=false;
 if(!reportedEntry){reportedEntry=true;REXLOG_INFO("Advanced Forge placement hook: held {:08X}, engine {:08X}, edited {:08X}, map {}",datum,engine,U(base,engine+0xe198),U(base,engine+0x178));}
 // Retail 82280BFC..82280C20 resolves this table entry as a variant slot,
 // then reads its live object datum at engine + 0x1AC + slot * 0x54.
 bool editing=false;uint32_t heldSlot=0,heldPlayer=0;
 for(unsigned i=0;i<16;++i){
  uint32_t slot=U(base,engine+0xe198+i*4);
  if(slot<640&&U(base,engine+0x1ac+slot*0x54)==datum){editing=true;heldSlot=slot;heldPlayer=i;break;}
 }
 if(!editing)return {};
 fixedSnap=0xffffffff;
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty())diagnosticDatum=datum;
 uint32_t game=U(base,tls+0x80);
 static bool reportedEditing=false;
 if(!reportedEditing&&Ptr(game)){reportedEditing=true;REXLOG_INFO("Advanced Forge editing gate: simulation {} network {}",base[game+0x14],base[game+0x15]);}
 // Simulation 1 is local; 2..5 are synchronous/distributed clients/servers.
 // The adjacent network-type byte is also 1 in a normal offline session.
 if(!Ptr(game)||base[game+0x14]!=1){ClearAnchors();Status("Offline Forge only");return {};}
 Load();uint32_t variant=engine+0x78,mid=U(base,variant+0x100);
 // The original held lifecycle consumes its own property queue each tick.
 // Pose callbacks can occur inside a body rebuild; do not recursively consume
 // another request or publish a transient selection from that callback.
 if(!OwnedOriginalSceneryEditor(datum))UpdatePhysics(ctx,base,datum);
 uint32_t array=U(base,tls+0xa8);if(!Ptr(array))return {};
 uint32_t headers=U(base,array+0x44);if(!Ptr(headers))return {};
 V queryPosition{};float heldRadius=0;
 auto make=[&](uint32_t id,V pos,M basis)->Object{
  Object o;o.datum=id;o.position=pos;
  uint32_t h=headers+(id&65535)*16;
  if(H(base,h)!=id>>16)return o;
  uint32_t obj=U(base,h+12);if(!Ptr(obj))return o;
  auto it=bindings.find((uint64_t(mid)<<32)|U(base,obj));if(it==bindings.end())return o;
  o.radius=it->second.radius;
  if(id!=datum){
   float distance2=0;for(unsigned j=0;j<3;++j){const auto delta=pos[j]-queryPosition[j];distance2+=delta*delta;}
   const auto range=heldRadius+o.radius;
   if(distance2>range*range)return o;
  }
  for(const auto& a:it->second.anchors)o.markers.push_back(MakeMarker(a,basis,pos));
  return o;
 };
 if(!Ptr(position))return {};
 // Process-local test input, before marker collection and original H4 logic.
 // It supplies a drag request; it never selects a marker or changes a result.
 auto testPosition=REXCVAR_GET(halo3mp_advanced_forge_test_position);
 if(!testPosition.empty()){
  if(REXCVAR_GET(halo3mp_advanced_forge_trace).empty()||REXCVAR_QUERY(std::string,input_state_replay).empty())
   throw std::runtime_error("Diagnostic drag requires exclusive replay and scene tracing");
  std::istringstream input(testPosition);V requested{};char comma1,comma2;
  if(!(input>>requested[0]>>comma1>>requested[1]>>comma2>>requested[2])||comma1!=','||comma2!=','||!(input>>std::ws).eof())
   throw std::runtime_error("Invalid diagnostic drag request");
  for(unsigned i=0;i<3;++i){
   if(!std::isfinite(requested[i]))throw std::runtime_error("Nonfinite diagnostic drag request");
   auto value=std::byteswap(std::bit_cast<uint32_t>(requested[i]));std::memcpy(base+position+i*4,&value,4);
  }
 }
 // Original placement preserves each absent axis (82283850..8228388C).
 // Translation-only events must use the existing variant orientation too.
 uint32_t heldPose=variant+0x130+heldSlot*0x54;
 if((forward&&!Ptr(forward))||(up&&!Ptr(up)))return {};
 Scene scene;scene.sensitivity=sensitivity.load();scene.cursor=Vec(base,position);
 // Only consume movement inside this player's original held-update call.
 // Numeric/menu placements outside that call keep their stationary semantics.
 if(heldMovement&&(heldMovement->player&65535)==heldPlayer)
  scene.processedMovement=heldMovement->value;
 scene.heldBasis=Basis(Vec(base,forward?forward:heldPose+0x1c),Vec(base,up?up:heldPose+0x28));
 auto exact=coordinates.Update(mid,datum,{scene.cursor,scene.heldBasis},*bridge);
 const auto testCoordinates=REXCVAR_GET(halo3mp_advanced_forge_test_coordinates);
 static bool coordinateTestSent=false;
 if(!testCoordinates.empty()&&!coordinateTestSent){
  if(REXCVAR_GET(halo3mp_advanced_forge_trace).empty()||REXCVAR_QUERY(std::string,input_state_replay).empty())
   throw std::runtime_error("Diagnostic coordinates require exclusive replay and scene tracing");
  std::istringstream input(testCoordinates);std::array<float,6> values{};
  for(unsigned i=0;i<6;++i){char comma;if((i&&(!(input>>comma)||comma!=','))||!(input>>values[i]))throw std::runtime_error("Invalid coordinate test request");}
  if(!(input>>std::ws).eof())throw std::runtime_error("Trailing coordinate test data");
  coordinates.Queue(coordinates.Read(),{values[0],values[1],values[2]},{values[3],values[4],values[5]});
  exact=coordinates.Update(mid,datum,{scene.cursor,scene.heldBasis},*bridge);coordinateTestSent=true;
  REXLOG_INFO("Advanced Forge coordinate command applied: datum {:08X}, position {},{},{} angles {},{},{} magnets {}",datum,values[0],values[1],values[2],values[3],values[4],values[5],enabled.load());
 }
 // Owned scenery already receives menu event13 in its persistent editor.
 // A native placement callback must not reapply that target over the original
 // controller (including while the numeric submenu is previewing a choice).
 if(OwnedOriginalSceneryEditor(datum))return {};
 if(exact){
  // Exact coordinates take precedence until the user resumes ordinary dragging.
  // The caller supplies this pose to the unmodified native placement function.
  ClearAnchors();Status("Coordinates held");
  auto h=headers+(datum&65535)*16,obj=U(base,h+12);
  if(H(base,h)==datum>>16&&Ptr(obj)){
   auto binding=bindings.find((uint64_t(mid)<<32)|U(base,obj));
   if(binding!=bindings.end()&&binding->second.fixed)fixedSnap=datum;
  }
  return exact;
 }
 if(!enabled.load()){ClearAnchors();return {};}
 scene.objects.push_back(make(datum,scene.cursor,scene.heldBasis));
 queryPosition=scene.cursor;heldRadius=scene.objects[0].radius;
 if(scene.objects[0].markers.empty()){ClearAnchors();Status("This piece has no marker binding");return {};}
 static bool reportedBinding=false;
 if(!reportedBinding){reportedBinding=true;REXLOG_INFO("Advanced Forge bound held piece: map {} datum {:08X}, {} markers, position {},{},{}",mid,datum,scene.objects[0].markers.size(),scene.cursor[0],scene.cursor[1],scene.cursor[2]);}
 for(unsigned i=0;i<640;++i){uint32_t slot=variant+0x130+i*0x54;
  if(!(H(base,slot)&1))continue;uint32_t id=U(base,slot+4);if(id==datum||id==0xffffffff)continue;
  auto o=make(id,Vec(base,slot+0x10),Basis(Vec(base,slot+0x1c),Vec(base,slot+0x28)));
  if(o.markers.empty())continue;
  if(scene.objects.size()==64){Status("Too many nearby objects for H4 query");return {};}
  scene.objects.push_back(std::move(o));
 }
 auto r=bridge->Evaluate(scene);auto checks=++evaluations;
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  static uint32_t priorDatum=0xffffffff;static bool priorSnap=false,priorMoving=false;
  const bool moving=std::any_of(scene.processedMovement.begin(),scene.processedMovement.end(),[](float v){return v!=0;});
  if(priorDatum!=datum||priorSnap!=r.snapped||priorMoving!=moving){
   REXLOG_INFO("Advanced Forge movement gate: held {:08X} player {} scoped {} input {},{},{} candidate {:08X} snapped {} live {}",datum,heldPlayer,bool(heldMovement),scene.processedMovement[0],scene.processedMovement[1],scene.processedMovement[2],r.targetDatum,r.snapped,livePose);
   priorDatum=datum;priorSnap=r.snapped;priorMoving=moving;
  }
 }

 const auto visible=bridge->UpdateVisibility(datum,r.targetDatum,true);
 // The native observer result supplies the camera; no desktop/window capture.
 // Publish a value snapshot so the UI never reads guest memory concurrently.
 const auto observer=U(base,tls+716);
 if(Ptr(observer)){
  const auto camera=observer+272;
  AnchorView view;view.updated=std::chrono::steady_clock::now();view.time=float(physicsTick)/30.f;
  view.camera={Vec(base,camera),Vec(base,camera+0x28),Vec(base,camera+0x34),F(base,camera+0x40),F(base,camera+0x58)};
  for(const auto& o:scene.objects){
   if(std::find(visible.begin(),visible.end(),o.datum)==visible.end())continue;
   for(const auto& marker:o.markers){
    VisibleAnchor anchor;anchor.held=o.datum==datum;
    V local{};
    for(unsigned i=0;i<3;++i){uint32_t bits;std::memcpy(&bits,marker.data()+0x60+i*4,4);
     anchor.position[i]=std::bit_cast<float>(std::byteswap(bits));
     std::memcpy(&bits,marker.data()+0x2c+i*4,4);local[i]=std::bit_cast<float>(std::byteswap(bits));
    }
    if(anchor.held&&r.snapped){const auto rotated=Transform(Quaternion(r.rotation.data()),local);for(unsigned i=0;i<3;++i)anchor.position[i]=rotated[i]+r.position[i];}
    view.anchors.push_back(anchor);
   }
  }
  std::lock_guard lock(anchorMutex);anchorViews[0]=std::move(view);
 }
 if(!livePose&&!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  static std::deque<std::string> poseRecords;
  std::ostringstream row;row.precision(9);
  row<<checks<<','<<datum<<','<<heldSlot<<','<<r.snapped;
  for(float v:scene.cursor)row<<','<<v;
  for(float v:scene.heldBasis)row<<','<<v;
  for(float v:r.position)row<<','<<v;
  for(float v:r.rotation)row<<','<<v;
  poseRecords.push_back(row.str());if(poseRecords.size()>128)poseRecords.pop_front();
  std::ofstream out(REXCVAR_GET(halo3mp_advanced_forge_trace)+".placement.csv",std::ios::trunc);
  for(const auto& record:poseRecords)out<<record<<'\n';
 }
 if(scene.objects.size()>1&&(checks==1||checks%30==0)){
  auto path=REXCVAR_GET(halo3mp_advanced_forge_trace);
  if(!path.empty())SaveScene(path,scene);
 }
 if(checks==1||checks%120==0)REXLOG_INFO("Advanced Forge original H4 evaluation: {} objects, snapped {}, live {}",scene.objects.size(),r.snapped,livePose);
 if(r.snapped){
  uint32_t h=headers+(datum&65535)*16,obj=U(base,h+12);
  if(bindings.at((uint64_t(mid)<<32)|U(base,obj)).fixed)fixedSnap=datum;
  for(float v:r.position)if(!std::isfinite(v))throw std::runtime_error("Nonfinite H4 placement");
  for(unsigned i=0;i<3;++i){auto v=std::byteswap(std::bit_cast<uint32_t>(r.position[i]));std::memcpy(base+position+i*4,&v,4);}
  auto n=++snaps;if(n==1||n%120==0)REXLOG_INFO("Advanced Forge original H4 snap: held {:08X} target {:08X}",datum,r.targetDatum);
  Status("Magnet connected");
  return CoordinatePose{r.position,Quaternion(r.rotation.data())};
 }else Status("Searching for a matching marker");
 return {};
}
// Both native pose entry points use register arguments only. Reserve a guest
// stack frame for the optional pose; the native callee grows below this frame.
// Never borrow adjacent caller data when an axis argument is null.
class PoseArguments {
 PPCContext& ctx_;uint32_t stack_;bool active_=false;
public:
 PoseArguments(PPCContext& ctx,uint8_t* base,const std::optional<CoordinatePose>& pose,bool live=false):ctx_(ctx),stack_(ctx.r1.u32){
  if(!pose)return;
  if(stack_<0x10200||stack_>=0xc0000000)throw std::runtime_error("Invalid placement stack");
  ctx.r1.u32-=0x100;active_=true;
  const auto point=ctx.r1.u32+0x60,forward=point+12,up=forward+12;
  auto put=[&](uint32_t at,float f){auto bits=std::byteswap(std::bit_cast<uint32_t>(f));std::memcpy(base+at,&bits,4);};
  const auto backchain=std::byteswap(stack_);std::memcpy(base+ctx.r1.u32,&backchain,4);
  for(unsigned i=0;i<3;++i){put(point+i*4,pose->position[i]);put(forward+i*4,pose->basis[i]);put(up+i*4,pose->basis[6+i]);}
  if(live){ctx.r4.u32=point;ctx.r5.u32=forward;ctx.r6.u32=up;}
  else{ctx.r5.u32=point;ctx.r6.u32=forward;ctx.r7.u32=up;}
 }
 ~PoseArguments(){if(active_)ctx_.r1.u32=stack_;}
};
class Controls final:public rex::ui::ImGuiDialog {
public: explicit Controls(rex::ui::ImGuiDrawer* d):ImGuiDialog(d){}
 void OnDraw(ImGuiIO&) override {
  // Marker snapshots are published by native camera submission, in command
  // order. The UI thread must not replace a queued view with a newer one.
 }
};
}
bool OwnsKeyframedSceneryPose(PPCContext& ctx,uint8_t* base,uint32_t datum){
 return EligibleKeyframedSceneryPose(ctx,base,datum);
}
void AttachControls(rex::ui::ImGuiDrawer* d){
 // Earlier releases persisted false for the F7 opt-in panel. That legacy
 // setting must not disable the new automatic Forge behavior. A command-line
 // override remains available for isolated diagnostic comparisons only.
 enabled=rex::cvar::GetFlagSource("halo3mp_advanced_forge")==rex::cvar::Source::kCommandLine?
     REXCVAR_GET(halo3mp_advanced_forge):true;
 new Controls(d);
}
void AttachRenderer(rex::graphics::CommandProcessor* renderer){markerRenderer=renderer;}
}
// Keep H3's object/ancestor/seat eligibility rules as the native-world
// boundary. Repeating its read-only predicate over triples is the conjunction
// of the same exclusions, without truncating H4's up-to64-entry list. All
// ordinary queries take exactly the original path. The selection query must
// establish SelectionRayExclusionScope; native Forge ray/grab hooks use it.
extern "C" void __imp__sub_82333388(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_821F04C0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821F04C0){
 using namespace advanced_forge;
 const auto player=ctx.r3.u32;
 if(enabled.load()&&!failed&&bridge&&player!=0xffffffff&&(player&65535)<16&&PhysicsWorld(ctx,base)){
  auto& slot=nativeEditors[player&65535];
  // The complete held lifecycle owns this flag. Until that lifecycle is
  // armed, preserve stock input consumption rather than partially taking over.
  if(slot.player==player&&slot.editor&&slot.ownsMonitorContact){
   try{
    if(ConsumeNativeSceneryInput(ctx,base,player,ctx.r4.u32,slot.input))return;
   }catch(const std::exception& e){
    RestorePhysics(ctx,base);ClearNativeEditors();failed=true;
    REXLOG_ERROR("Original scenery input failed: {}",e.what());
   }
  }else if(slot.player==player&&slot.editor){
   // Player input outlives each hold. Observe the original producer while
   // H3 owns the packet, discarding its movement-consumption output. This
   // keeps release/re-grab input current without taking over native input.
   try{
    const auto frame=ReadNativeSceneryInput(ctx,base,player,ctx.r4.u32);
    if(frame)slot.input=bridge->ConsumeManipulationInput(slot.input,frame->value).state;
    else slot.input.active=false; // original82368DD8 writes only this byte
   }catch(const std::exception& e){
    RestorePhysics(ctx,base);ClearNativeEditors();failed=true;
    REXLOG_ERROR("Original scenery input observation failed: {}",e.what());
   }
  }
 }
 __imp__sub_821F04C0(ctx,base);
}

REX_HOOK_RAW(sub_82333388){
 // Native counterpart of H48293E878/8293E1B0: clear transient controller
 // ownership before object/physics synchronization, including recursive calls.
 advanced_forge::controllerAttachments.erase(ctx.r3.u32);
 __imp__sub_82333388(ctx,base);
}
extern "C" void __imp__sub_823316D8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_823316D8){
 const bool detachWithoutReconnect=ctx.lr==0x82331858&&(ctx.r28.u32&255)==0;
 struct FinishDetachPose {
  PPCContext& ctx;uint8_t* base;bool reset;
  ~FinishDetachPose(){if(reset)advanced_forge::ResetNativeDetachPhysics(ctx,base);}
 } finish{ctx,base,detachWithoutReconnect};
 std::optional<std::array<float,13>> pose;
 try{pose=advanced_forge::NativeCompensatedAttachment(ctx,base);}
 catch(const std::exception& e){
  if(auto* grab=advanced_forge::nativeGrabTransaction)grab->error=e.what();
  else{
   advanced_forge::failed=true;
   REXLOG_ERROR("Original H4 attachment compensation failed: {}",e.what());
  }
 }
 // Complete native unlink/notifications even when compensation cannot be mapped.
 if(!pose){__imp__sub_823316D8(ctx,base);return;}
 const auto stack=ctx.r1.u32;
 ctx.r1.u32-=0x100;
 const auto backchain=std::byteswap(stack),input=ctx.r1.u32+0x60;
 std::memcpy(base+ctx.r1.u32,&backchain,4);
 for(unsigned i=0;i<13;++i){
  const auto value=std::byteswap(std::bit_cast<uint32_t>((*pose)[i]));
  std::memcpy(base+input+i*4,&value,4);
 }
 struct RestoreStack {PPCContext& ctx;uint32_t stack;~RestoreStack(){ctx.r1.u32=stack;}} restore{ctx,stack};
 ctx.r4.u32=input;
 __imp__sub_823316D8(ctx,base);
}

extern "C" void __imp__sub_82330778(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82330778){
 // Preserve H3's incoming true: it selects spatial-tree update82348E28.
 // H3 false only copies cached bounds820F3A98, whereas H4's false selects
 // the broader824F5880/82482858 service. These booleans are not equivalent.
 const bool detachReconnect=ctx.lr==0x82331870;
 __imp__sub_82330778(ctx,base);
 if(detachReconnect)advanced_forge::ResetNativeDetachPhysics(ctx,base);
}
REX_HOOK_RAW(sub_82330B20){
 using namespace advanced_forge;
 const auto* attachment=nativeDetachAttachment;
 const auto* grab=nativeGrabTransaction;
 // Native detach already excludes native bit8. H4 additionally excludes its
 // connected bit8 (native bit7), including a body just reconnected by rebuild.
 if(ctx.lr==0x823318AC&&attachment&&attachment->physicsReset&&
    attachment->datum==ctx.r3.u32&&grab&&grab->error.empty()){
  const auto object=ObjectPointer(base,physicsHeaders,attachment->datum);
  if(object==attachment->object&&object&&(U(base,object+172)&kConnected))return;
 }
 __imp__sub_82330B20(ctx,base);
}

extern "C" void __imp__sub_821FCA48(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821FCA48){
 // Native821E74C8 clears TLS96's datum array. Ignore every other pool.
 const auto tls=advanced_forge::U(base,ctx.r13.u32);
 const bool players=advanced_forge::Ptr(tls)&&ctx.r3.u32==advanced_forge::U(base,tls+96);
 __imp__sub_821FCA48(ctx,base);
 if(players)advanced_forge::ClearNativePlayerContacts();
}

extern "C" void __imp__sub_821E7A90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821E7A90){
 __imp__sub_821E7A90(ctx,base);
 // Native counterpart of H482355698: successful allocation returns the
 // complete salted player datum. Failure must not clear another editor slot.
 advanced_forge::InitializeNativePlayerContact(ctx,base,ctx.r3.u32);
}

extern "C" void __imp__sub_821EF708(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821EF708){
 const auto player=ctx.r3.u32;
 const auto tls=advanced_forge::U(base,ctx.r13.u32);
 const auto* contact=advanced_forge::PlayerContact(base,tls,player,false);
 const auto record=contact?contact->record:0;
 __imp__sub_821EF708(ctx,base);
 // Only discard host lifetime state after the native departure committed.
 // Native object/unit removal, physics and variant actions remain native.
 if(record&&advanced_forge::H(base,record)==(player>>16)&&
    (advanced_forge::U(base,record+4)&2)){
  auto& state=advanced_forge::nativePlayerContacts[player&65535];
  if(state.player==player&&state.record==record)state={};
  auto& editor=advanced_forge::nativeEditors[player&65535];
  if(editor.player==player){advanced_forge::ClearPlayerAnchors(player);editor=advanced_forge::NativeEditorSlot{};}
  if(advanced_forge::completedMonitorExitPlayer==player)
   advanced_forge::completedMonitorExitPlayer.reset();
 }
}

extern "C" void __imp__sub_820FFBE0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_820FFBE0){
 if(advanced_forge::ReplaceNativeMonitorContact(ctx,base))return;
 // While stock H3 owns movement, observe its actual selected plane without
 // changing velocity, flags, geometry queries or notification behavior.
 auto observation=advanced_forge::ObserveNativeContact(ctx,base);
 struct Scope {
  advanced_forge::NativeContactObservation* previous;
  ~Scope(){advanced_forge::nativeContactObservation=previous;}
 } scope{advanced_forge::nativeContactObservation};
 advanced_forge::nativeContactObservation=observation?&*observation:nullptr;
 __imp__sub_820FFBE0(ctx,base);
 if(observation&&observation->normal){
  if(auto* state=advanced_forge::PlayerContact(base,observation->tls,observation->player,false)){
   state->normal=*observation->normal;state->normalKnown=true;
  }
 }
}
extern "C" void __imp__sub_82237E58(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82237E58){
 const auto observation=advanced_forge::nativeContactObservation;
 const bool primary=observation&&ctx.lr==0x820FFED0&&ctx.r9.u32==0;
 const auto normal=ctx.r6.u32;
 __imp__sub_82237E58(ctx,base);
 if(primary&&(ctx.r3.u32&255)&&advanced_forge::Ptr(normal)&&uint64_t(normal)+12<0xc0000000ULL){
  const auto value=advanced_forge::Vec(base,normal);
  if(std::all_of(value.begin(),value.end(),[](float v){return std::isfinite(v);}))
   observation->normal=value;
 }
}

REX_HOOK_RAW(sub_820AF170){
 const auto exclusions=advanced_forge::selectionRayExclusions;
 if(!exclusions||exclusions->empty()){
  __imp__sub_820AF170(ctx,base);return;
 }
 const auto entry=ctx;
 __imp__sub_820AF170(ctx,base);
 if(!ctx.r3.u32)return;
 for(size_t i=0;i<exclusions->size();i+=3){
  auto call=entry;
  call.r7.u32=(*exclusions)[i];
  call.r8.u32=i+1<exclusions->size()?(*exclusions)[i+1]:0xffffffff;
  call.r9.u32=i+2<exclusions->size()?(*exclusions)[i+2]:0xffffffff;
  __imp__sub_820AF170(call,base);
  if(!call.r3.u32){ctx.r3.u32=0;return;}
 }
}

REX_HOOK_RAW(sub_822837C8){
 uint32_t captureVariant=0;
 const uint32_t placementDatum=ctx.r4.u32;
 const uint32_t caller=ctx.lr;
 auto trace=REXCVAR_GET(halo3mp_advanced_forge_trace);
 if(!trace.empty()){
  auto tls=advanced_forge::U(base,ctx.r13.u32);
  if(advanced_forge::Ptr(tls)){
   auto engine=advanced_forge::U(base,tls+0x64);
   auto game=advanced_forge::U(base,tls+0x80);
   if(advanced_forge::Ptr(engine)&&advanced_forge::Ptr(game)&&base[game+0x14]==1)
    captureVariant=engine+0x78;
  }
 }
 std::optional<advanced_forge::CoordinatePose> exact;
 try{exact=advanced_forge::Evaluate(ctx,base);}catch(const std::exception& e){advanced_forge::RestorePhysics(ctx,base);advanced_forge::failed=true;advanced_forge::coordinates.Reset();advanced_forge::Status(e.what());REXLOG_ERROR("Advanced Forge disabled: {}",e.what());}
 {advanced_forge::PoseArguments args(ctx,base,exact);advanced_forge::PlacementScope scope;__imp__sub_822837C8(ctx,base);}
 if(captureVariant&&placementDatum==advanced_forge::diagnosticDatum){
  // Keep the most recent changed native poses, including calls after the
  // edited-object slot clears. This separates snapping from release physics.
  static std::deque<std::string> nativeRecords;
  static std::string previousPose;
  for(unsigned slot=0;slot<640;++slot){
   auto address=captureVariant+0x130+slot*0x54;
   if(advanced_forge::U(base,address+4)!=placementDatum)continue;
   std::ostringstream pose;pose.precision(9);
   pose<<placementDatum<<','<<slot;
   for(unsigned i=0;i<9;++i)pose<<','<<advanced_forge::F(base,address+0x10+i*4);
   if(pose.str()!=previousPose){
    previousPose=pose.str();
    nativeRecords.push_back(std::to_string(caller)+','+previousPose+','+std::to_string(advanced_forge::syncCaller));
    if(nativeRecords.size()>128)nativeRecords.pop_front();
    std::ofstream out(trace+".native.csv",std::ios::trunc);
    for(const auto& record:nativeRecords)out<<record<<'\n';
   }
   break;
  }
  // Read-only diagnostic after the original H3 map-variant update. Export
  // tooling clears runtime handles before wrapping this native saved format.
  std::ofstream file(trace+".variant",std::ios::binary|std::ios::trunc);
  file.write(reinterpret_cast<const char*>(base+captureVariant),0xe090);
  if(!file)REXLOG_WARN("Could not capture Advanced Forge native variant");
 }
}
// Shared native object-pose setter. The call at 82280B60 moves the player's
// controlled unit during a mode-change event, not a held-object preview.
// Final placement calls it at 8228390C after updating the map variant.
REX_HOOK_RAW(sub_8232E8B8){
 advanced_forge::TraceNativeHeldWriter(ctx,base,ctx.r3.u32,"pose");
 std::optional<advanced_forge::CoordinatePose> exact;
 try{exact=advanced_forge::Evaluate(ctx,base,true);}catch(const std::exception& e){advanced_forge::RestorePhysics(ctx,base);advanced_forge::failed=true;advanced_forge::coordinates.Reset();advanced_forge::Status(e.what());REXLOG_ERROR("Advanced Forge disabled: {}",e.what());}
 advanced_forge::PoseArguments args(ctx,base,exact,true);
 __imp__sub_8232E8B8(ctx,base);
}

// Retain pose-sync provenance; phased release maps the original H4 true
// synchronization argument only at the exact native local-release call.
REX_HOOK_RAW(sub_82284078){
 if(ctx.lr==0x8227FEC4&&advanced_forge::nativePhasedReleaseDatum==ctx.r4.u32)
  ctx.r3.u32=1;
 const auto previous=advanced_forge::syncCaller;
 advanced_forge::syncCaller=ctx.lr;
 struct Restore {uint32_t value;~Restore(){advanced_forge::syncCaller=value;}} restore{previous};
 __imp__sub_82284078(ctx,base);
}

extern "C" void __imp__sub_820F2DD0(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82283950(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_820F2DD0){
 if(ctx.lr==0x8227FED0&&advanced_forge::nativePhasedReleaseDatum==ctx.r3.u32)
  ctx.r4.u32=1;
 __imp__sub_820F2DD0(ctx,base);
}
REX_HOOK_RAW(sub_82283950){
 // Original82451250 skips8244F300 when variant physics bit7 is set.
 // Native r5 has a different meaning; do not use it to skip the whole drop.
 if(ctx.lr==0x8227FFC8&&advanced_forge::nativePhasedReleaseDatum==ctx.r3.u32)return;
 __imp__sub_82283950(ctx,base);
}
// Native variant removal clears every matching holder through8227E710.
// H482450CD8 likewise runs82449ED8(-1) for matching editors BEFORE deleting
// the object. Preserve native variant/deletion notifications; reset only the
// private original controller here, without a release/settling transition.
extern "C" void __imp__sub_8227E710(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227E710){
 const auto variant=ctx.r3.u32;
 auto selectionContext=ctx;
 bool cleared=false;
 if(variant<640&&advanced_forge::bridge&&!advanced_forge::failed&&
    advanced_forge::PhysicsWorld(selectionContext,base)){
  const auto engine=advanced_forge::physicsEngine;
  const auto datum=advanced_forge::U(base,engine+0x1ac+variant*0x54);
  for(uint32_t i=0;i<advanced_forge::nativeEditors.size();++i){
   auto& editor=advanced_forge::nativeEditors[i];
   if(!editor.editor||!editor.ownsMonitorContact||
      advanced_forge::U(base,engine+0xe198+i*4)!=variant)continue;
   try{
    uint32_t selected;std::memcpy(&selected,editor.editor->bytes.data(),4);
    if(editor.player==0xffffffff||(editor.player&65535)!=i||
       datum==0xffffffff||std::byteswap(selected)!=datum||
       !advanced_forge::PlayerContact(base,advanced_forge::U(base,ctx.r13.u32),editor.player,false))
     throw std::runtime_error("Native removal selection identity changed");
    advanced_forge::SelectNativeHeldEditor(*advanced_forge::bridge,selectionContext,base,
     editor.player,0xffffffff,true,
     [](const std::string& event){REXLOG_INFO("Original H4 Forge event: {}",event);});
    cleared=true;
   }catch(const std::exception& e){
    advanced_forge::failed=true;
    REXLOG_ERROR("Original scenery removal selection failed: {}",e.what());
   }
  }
 }
 __imp__sub_8227E710(ctx,base);
 if(cleared){
  advanced_forge::coordinates.Reset();
  advanced_forge::physics.Reset();
 }
}
// Native engine deletion callback, counterpart of H4 engine vtable208 /
//8244C000. Variant removal has a separate earlier reset and is idempotent here.
extern "C" void __imp__sub_82280860(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280860){
 const auto datum=ctx.r4.u32;
 auto deletion=ctx;
 using namespace advanced_forge;
 if(datum!=0xffffffff&&bridge&&!failed&&PhysicsWorld(deletion,base)){
  for(auto& slot:nativeEditors){
   if(slot.player==0xffffffff||!slot.editor)continue;
   const auto read=[&](unsigned offset){
    uint32_t value;std::memcpy(&value,slot.editor->bytes.data()+offset,4);return std::byteswap(value);
   };
   if(read(0)!=datum&&read(4)!=datum&&read(24)!=datum)continue;
   try{
    if(!PlayerContact(base,U(base,ctx.r13.u32),slot.player,false))
     throw std::runtime_error("Deleted-object editor player lifetime changed");
    const auto world=NativeHeldSelectionWorld(deletion,base,slot.player,true,
      [](const std::string& event){REXLOG_INFO("Original H4 Forge event: {}",event);});
    const bool selected=bridge->NotifyObjectDeleted(*slot.editor,slot.player,datum,world);
    if(selected){
     slot.ownsMonitorContact=false;slot.contactMonitor=0xffffffff;
     coordinates.Reset();physics.Reset();
    }
    // Keep surviving held/target marker visibility from the original setters.
    std::lock_guard lock(anchorMutex);
    for(auto& view:anchorViews)if(view.player==slot.player)
     std::erase_if(view.anchors,[&](const VisibleAnchor& anchor){
      return std::find(slot.editor->visibleObjects.begin(),slot.editor->visibleObjects.end(),anchor.datum)==slot.editor->visibleObjects.end();
     });
   }catch(const std::exception& error){
    failed=true;ClearPlayerAnchors(slot.player);
    REXLOG_ERROR("Original scenery deletion cleanup failed: {}",error.what());
   }
  }
 }
 // Preserve H3's session-specific holder updates, target references and
 // deferred-object cleanup. Private cleanup never edits native holder slots.
 __imp__sub_82280860(ctx,base);
}

extern "C" void __imp__sub_8227FDF8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82283CF8(PPCContext& __restrict,uint8_t*);
// Finalize a magnet placement through H3's own deferred-object cleanup.
// Fixed pieces recover their authored physics; dynamic pieces and throws
// continue through unmodified H3 settling. No snap transform is invented here.
REX_HOOK_RAW(sub_8227FDF8){
 const auto releasePlayer=ctx.r3.u32;
 const auto clearancePlayer=releasePlayer&65535;
 const bool skipPlacement=(ctx.r5.u32&255)!=0;
 uint32_t engine=0,datum=0xffffffff,heldBefore=0xffffffff;
 if((advanced_forge::enabled.load()||advanced_forge::coordinates.Locked()||!advanced_forge::physicsObjects.empty())&&!advanced_forge::failed){
  auto tls=advanced_forge::U(base,ctx.r13.u32);
  if(advanced_forge::Ptr(tls)){
   auto game=advanced_forge::U(base,tls+0x80);
   engine=advanced_forge::U(base,tls+0x64);
   if(advanced_forge::LocalForge(base,game)&&advanced_forge::Ptr(engine)&&
      clearancePlayer<16){
    const auto slot=advanced_forge::U(base,engine+0xe198+clearancePlayer*4);
    if(slot<640){
     heldBefore=advanced_forge::U(base,engine+0x1ac+slot*0x54);
     if(ctx.f1.f64<=advanced_forge::F(base,0x8202496c))datum=heldBefore;
    }
   }
  }
 }
 // Complete H4 lifecycle ownership is armed by the coupled tick, never by
 // ordinary H3 editing. Reset original selection before native release work.
 bool originalRelease=false,originalPlacementRelease=false;
 if(heldBefore!=0xffffffff&&clearancePlayer<16){
  auto& editor=advanced_forge::nativeEditors[clearancePlayer];
  if(editor.player==releasePlayer&&editor.ownsMonitorContact){
   try{
    if(!advanced_forge::bridge||!editor.editor)
     throw std::runtime_error("Owned scenery release lacks original editor");
    uint32_t selected;std::memcpy(&selected,editor.editor->bytes.data(),4);
    if(std::byteswap(selected)!=heldBefore)
     throw std::runtime_error("Owned scenery release selection mismatch");
    // H4 byte280 is populated by its history-delivered per-player object
    // record (82888DA0), not local scenery manipulation. Spartan retains
    // native H3 transport/application; H4 records must never enter this
    // private editor. Reject unexpected state before selection erases it.
    if(editor.editor->bytes[280]!=0)
     throw std::runtime_error("Unexpected H4 history pose in native H3 release");
    const auto pointer=advanced_forge::ObjectPointer(base,advanced_forge::physicsHeaders,heldBefore);
    if(!pointer)throw std::runtime_error("Owned scenery release lost native object");
    originalPlacementRelease=!skipPlacement&&advanced_forge::U(base,pointer+16)==0xffffffff;
    // Original82939170 is parent detachment, not a general monitor reset.
    // It is a no-op for the unparented monitor required by this lifecycle.
    // Check before selection reset clears the retained monitor identity.
    const auto monitor=advanced_forge::ObjectPointer(base,advanced_forge::physicsHeaders,
                                                   editor.contactMonitor);
    const bool completedExit=ctx.lr==0x82280818&&
        advanced_forge::completedMonitorExitPlayer==releasePlayer;
    if(!completedExit&&(!monitor||advanced_forge::U(base,monitor+16)!=0xffffffff||
       advanced_forge::U(base,monitor+380)!=releasePlayer))
     throw std::runtime_error("Owned scenery release monitor changed");
    advanced_forge::SelectNativeHeldEditor(*advanced_forge::bridge,ctx,base,
     releasePlayer,0xffffffff,true,
     [](const std::string& event){REXLOG_INFO("Original H4 Forge event: {}",event);});
    originalRelease=true;
   }catch(const std::exception& e){
    advanced_forge::failed=true;
    REXLOG_ERROR("Original scenery release selection failed: {}",e.what());
   }
  }
 }
 if(originalRelease&&!skipPlacement){
  try{
   if(!advanced_forge::NativeSceneryReleasePositionValid(ctx,base,heldBefore)){
    // H482451250 rejects placement after selection reset and before pose
    // serialization/settling. Native deletion takes a VARIANT SLOT, not datum.
    const auto slot=advanced_forge::U(base,engine+0xe198+clearancePlayer*4);
    if(slot>=640||advanced_forge::U(base,engine+0x1ac+slot*0x54)!=heldBefore)
     throw std::runtime_error("Rejected scenery release lost variant ownership");
    const auto flags=advanced_forge::H(base,engine+0x1a8+slot*0x54);
    if(!(flags&1)||(flags&0x20))
     throw std::runtime_error("Rejected scenery release has invalid variant record");
    auto removal=ctx;removal.r3.u32=releasePlayer;removal.r4.u32=slot;
    __imp__sub_822802D0(removal,base);
    advanced_forge::coordinates.Reset();advanced_forge::physics.Reset();
    advanced_forge::ClearPlayerAnchors(releasePlayer);
    if(advanced_forge::fixedSnap==heldBefore)advanced_forge::fixedSnap=0xffffffff;
    // Deletion uses native variant/object notifications and holder cleanup.
    // Do not enqueue or rebuild the rejected object after that transaction.
    return;
   }
  }catch(const std::exception& e){
   advanced_forge::failed=true;
   REXLOG_ERROR("Original scenery release validation failed: {}",e.what());
  }
 }
 const auto physicsObject=advanced_forge::physicsObjects.find(datum);
 const bool normalOverride=physicsObject!=advanced_forge::physicsObjects.end()&&physicsObject->second.mode==advanced_forge::PhysicsMode::Normal;
 const bool finalize=datum!=0xffffffff&&datum==advanced_forge::fixedSnap&&!normalOverride;
 {
  // The original H4 tick has already submitted its target. Native release
  // serializes that pose; it must not invoke the legacy magnet pass again.
  struct ReleasePoseScope {
   std::optional<uint32_t> previous=advanced_forge::nativePoseSyncDatum;
   std::optional<uint32_t> previousPhased=advanced_forge::nativePhasedReleaseDatum;
   ReleasePoseScope(bool active,bool placement,uint32_t held){
    if(active)advanced_forge::nativePoseSyncDatum=held;
    advanced_forge::nativePhasedReleaseDatum.reset();
    if(active&&placement){
     const auto it=advanced_forge::physicsObjects.find(held);
     if(it!=advanced_forge::physicsObjects.end()&&
        it->second.mode.value_or(it->second.authoredMode)==advanced_forge::PhysicsMode::Phased)
      advanced_forge::nativePhasedReleaseDatum=held;
    }
   }
   ~ReleasePoseScope(){
    advanced_forge::nativePoseSyncDatum=previous;
    advanced_forge::nativePhasedReleaseDatum=previousPhased;
   }
  } scope(originalRelease,originalPlacementRelease,heldBefore);
  __imp__sub_8227FDF8(ctx,base);
 }
 // Retail8227FDF8 also handles rejected/no-op releases and queued network
 // requests. Only its local transaction clears engine57752[player].
 // Do not discard held state or finalize physics merely because it returned.
 // Capture throws too: they release ownership although fixed-snap cleanup
 // deliberately remains limited to the non-throw branch above.
 if(heldBefore==0xffffffff||clearancePlayer>=16||
    advanced_forge::U(base,engine+0xe198+clearancePlayer*4)!=0xffffffff)return;
 advanced_forge::coordinates.Reset();
 advanced_forge::physics.Reset();
 if(originalRelease)advanced_forge::ClearPlayerAnchors(releasePlayer);
 else advanced_forge::ClearAnchors();
 if(originalRelease){
  // Original82451250 branches past placement/queue work for an attached
  // object, but still reaches824513A4 (selector + final transition). H3 r5
  // is ownership-only removal, a separate boundary that must stay skipped.
  if(!skipPlacement){
   try{
    advanced_forge::FinalizeNativeSceneryRelease(*advanced_forge::bridge,ctx,base,
                                               releasePlayer,heldBefore);
   }catch(const std::exception& e){
    advanced_forge::failed=true;
    REXLOG_ERROR("Original scenery release physics failed: {}",e.what());
   }
  }
  if(advanced_forge::fixedSnap==heldBefore)advanced_forge::fixedSnap=0xffffffff;
  return;
 }
 if(finalize){
  advanced_forge::fixedSnap=0xffffffff;
  const auto count=advanced_forge::U(base,engine+0xe8a8);
  if(count<=64)for(uint32_t i=0;i<count;++i){
   if(advanced_forge::U(base,engine+0xe4a8+i*4)!=datum)continue;
   auto cleanup=ctx;cleanup.r3.u32=datum;cleanup.r4.u32=i;cleanup.r5.u32=0;
   __imp__sub_82283CF8(cleanup,base);
   REXLOG_INFO("Advanced Forge finalized original H4 placement via native H3 fixed-object cleanup: {:08X}",datum);
   break;
  }
 }
 if(datum!=0xffffffff)advanced_forge::ApplyPhysics(ctx,base,datum);
 if(!REXCVAR_GET(halo3mp_advanced_forge_test_physics).empty()){
  auto it=advanced_forge::physicsObjects.find(datum);
  if(it!=advanced_forge::physicsObjects.end()&&it->second.mode&&advanced_forge::PhysicsValid(base,datum,it->second))
   REXLOG_INFO("Advanced Forge physics released: {:08X} mode {:02X} flags {:08X} held {}",datum,static_cast<uint16_t>(*it->second.mode),advanced_forge::U(base,it->second.pointer+0xac),advanced_forge::PhysicsHeld(base,datum));
 }
}

extern "C" void __imp__sub_8227E770(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_822843A8(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82283A30(PPCContext& __restrict,uint8_t*);
// Capture the authored runtime state before retail Forge forces a grabbed
// object dynamic. Never infer its original state from an already-held object.
REX_HOOK_RAW(sub_8227E770){
 const auto datum=ctx.r3.u32;
 // Complete original physics transition runs after this public grab returns.
 // Avoid H3's extra forced-dynamic rebuild between selection and that stage.
 const auto grab=advanced_forge::nativeGrabTransaction;
 if(grab&&grab->selected&&grab->error.empty()&&grab->datum==datum&&
    (ctx.r4.u32&255)==1&&ctx.lr==0x8227E9F0)return;
 bool initialized=false;
 const bool world=!advanced_forge::restoringPhysics&&!advanced_forge::failed&&advanced_forge::PhysicsWorld(ctx,base);
 // Native82283CF8 has already dequeued and passed its exclusion/skip
 // gates at this exact call. Original8244F740 performs selector+transition
 // here, before pose synchronization and possible world-bound deletion.
 if(world&&ctx.lr==0x82283D50&&(ctx.r4.u32&255)==0){
  auto it=advanced_forge::physicsObjects.find(datum);
  if(it!=advanced_forge::physicsObjects.end()&&it->second.originalReleasedPhysics&&
     advanced_forge::PhysicsValid(base,datum,it->second)){
   try{
    if(!advanced_forge::bridge)throw std::runtime_error("Original settling bridge unavailable");
    const auto mode=it->second.mode.value_or(it->second.authoredMode);
    advanced_forge::SelectAndTransitionNativeSceneryPhysics(*advanced_forge::bridge,
     ctx,base,datum,it->second,mode,true,nullptr);
   }catch(const std::exception& e){
    advanced_forge::failed=true;
    REXLOG_ERROR("Original scenery settling transition failed: {}",e.what());
   }
   return;
  }
 }
 if(!REXCVAR_GET(halo3mp_advanced_forge_test_physics).empty()){
  const auto tls=advanced_forge::U(base,ctx.r13.u32);
  if(advanced_forge::Ptr(tls)){
   const auto array=advanced_forge::U(base,tls+0xa8);
   const auto headers=advanced_forge::Ptr(array)?advanced_forge::U(base,array+0x44):0;
   const auto pointer=advanced_forge::ObjectPointer(base,headers,datum);
   REXLOG_INFO("Advanced Forge physics capture: world {} datum {:08X} force {} time {:08X} object {:08X} type {} flags {:08X} parent {:08X}",world,datum,ctx.r4.u32,advanced_forge::U(base,tls+0xbc),pointer,pointer?base[headers+(datum&65535)*16+3]:255,pointer?advanced_forge::U(base,pointer+0xac):0,pointer?advanced_forge::U(base,pointer+0x10):0);
  }
 }
 if(world&&(ctx.r4.u32&255)==1){
  const auto pointer=advanced_forge::ObjectPointer(base,advanced_forge::physicsHeaders,datum);
  const auto header=advanced_forge::physicsHeaders+(datum&65535)*16;
  const auto definition=pointer?advanced_forge::TagDefinition(base,advanced_forge::U(base,pointer)):0;
  // Scenery and crates only. Vehicles/units have additional attachment and
  // character-controller lifecycles and are intentionally not opted in.
  // Retail H3 enum: scenery=6, crate=10 (the PC reference enum differs).
  if(pointer&&(base[header+3]==6||base[header+3]==10)&&
     definition&&!(advanced_forge::H(base,definition+2)&(1u<<11))&&
     advanced_forge::U(base,pointer+0x10)==0xffffffff&&
     (advanced_forge::U(base,pointer+0xac)&advanced_forge::kConnected)){
   auto it=advanced_forge::physicsObjects.find(datum);
   if(it==advanced_forge::physicsObjects.end()||!advanced_forge::PhysicsValid(base,datum,it->second)){
    const auto authored=advanced_forge::AuthoredPhysics(base,pointer);
    // Capture authored state before native grab changes the body. Original
    // mode application belongs to the completed ownership transaction;
    // metadata capture alone must not activate a legacy physics override.
    advanced_forge::physicsObjects[datum]={pointer,advanced_forge::U(base,pointer),advanced_forge::U(base,pointer+0xac),authored,authored,false};
    initialized=true;
   }
  }
 }
 __imp__sub_8227E770(ctx,base);
 if(world){
  advanced_forge::ApplyPhysics(ctx,base,datum);
  if(initialized){
   const auto& object=advanced_forge::physicsObjects.at(datum);
   REXLOG_INFO("Advanced Forge captured physics: {:08X} mode {:02X} native flags {:08X}",datum,
    static_cast<uint16_t>(*object.mode),advanced_forge::U(base,object.pointer+0xac));
  }
 }
}
// Monitor teardown precedes native mode commit and held release. Preserve
// original-held state until that release, instead of globally resetting it.
REX_HOOK_RAW(sub_822843A8){
 const auto player=ctx.r3.u32;
 bool owned=false,ownerRejected=false;
 if(player!=0xffffffff&&(player&65535)<advanced_forge::nativeEditors.size()){
  const auto& slot=advanced_forge::nativeEditors[player&65535];
  owned=slot.player==player&&slot.editor&&slot.ownsMonitorContact;
  if(owned){
   try{
    uint32_t datum;std::memcpy(&datum,slot.editor->bytes.data(),4);
    auto validation=ctx;
    advanced_forge::ResolveNativeSceneryOwner(validation,base,player,std::byteswap(datum),true);
   }catch(const std::exception& error){
    // A host adapter invariant must not prevent the native mode transaction.
    // Do not grant the completed-monitor exception to an unvalidated owner.
    advanced_forge::failed=true;ownerRejected=true;owned=false;
    REXLOG_ERROR("Original scenery exit ownership failed: {}",error.what());
   }
  }
 }
 __imp__sub_822843A8(ctx,base);
 if(ctx.r3.u32&255){
  if(owned)advanced_forge::completedMonitorExitPlayer=player;
  else if(ownerRejected){
   // The native teardown committed. Quarantine only the failed player's
   // private controller; keep all native release/serialization work intact.
   auto& slot=advanced_forge::nativeEditors[player&65535];
   if(slot.player==player)slot=advanced_forge::NativeEditorSlot{};
   advanced_forge::ClearPlayerAnchors(player);
  }
 }
}
extern "C" void __imp__sub_82280720(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280720){
 const bool requestedPlay=ctx.r5.u32==1;
 struct ExitScope {
  std::optional<uint32_t> prior=advanced_forge::completedMonitorExitPlayer;
  ExitScope(){advanced_forge::completedMonitorExitPlayer.reset();}
  ~ExitScope(){advanced_forge::completedMonitorExitPlayer=prior;}
 } scope;
 __imp__sub_82280720(ctx,base);
 // Original82280720 commits the edit-player mask at engine57748, releases
 // the held object, then applies native world mode. Restore stock gameplay
 // physics only after that transaction and only when its edit mask is empty.
 if(requestedPlay&&!advanced_forge::physicsObjects.empty()){
  auto maintenance=ctx;
  if(advanced_forge::PhysicsWorld(maintenance,base)&&
     advanced_forge::H(base,advanced_forge::physicsEngine+57748)==0)
   advanced_forge::RestorePhysics(maintenance,base);
 }
}
// Native deferred updates own settling and pose serialization. Original H4
// physics transitions run at grab/property/release and the exact settling
// callback above, not as a host override applied again every frame.
REX_HOOK_RAW(sub_82283A30){
 const bool world=advanced_forge::PhysicsWorld(ctx,base);
 __imp__sub_82283A30(ctx,base);
 if(world&&!advanced_forge::restoringPhysics){
  for(auto it=advanced_forge::physicsObjects.begin();it!=advanced_forge::physicsObjects.end();){
   if(!advanced_forge::PhysicsValid(base,it->first,it->second))it=advanced_forge::physicsObjects.erase(it);
   else ++it;
  }
 }
}

// Native render-view setup binds the render ordinal to the actual local
// observer index (r7). Read its completed rectangle, not a guessed split layout.
extern "C" void __imp__sub_821582B0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821582B0){
 const auto renderView=ctx.r3.u32,localView=ctx.r7.u32;
 __imp__sub_821582B0(ctx,base);
 using namespace advanced_forge;
 if(localView>=anchorViewports.size()||!Ptr(renderView)||
    uint64_t(renderView)+10720>=0xc0000000ULL)return;
 AnchorViewport viewport;viewport.renderView=renderView;viewport.updated=std::chrono::steady_clock::now();
 //82158678 reads signed width/height at8275A248/24C, writes a short
 // top/left/bottom/right rectangle.821582B0 rebases camera48..54 to
 // zero and retains left/top in camera64/66 (camera is renderView+4).
 const int width=int16_t(U(base,0x8275a248)),height=int16_t(U(base,0x8275a24c));
 const int left=int16_t(H(base,renderView+68)),top=int16_t(H(base,renderView+70));
 const int viewWidth=int16_t(H(base,renderView+58)),viewHeight=int16_t(H(base,renderView+56));
 if(width>0&&height>0&&left>=0&&top>=0&&viewWidth>0&&viewHeight>0&&
    left+viewWidth<=width&&top+viewHeight<=height){
  viewport.rect={float(left)/width,float(top)/height,
                 float(left+viewWidth)/width,float(top+viewHeight)/height};
  viewport.valid=true;
 }
 std::lock_guard lock(anchorMutex);anchorViewports[localView]=viewport;
}

// A stream can fail after its last camera packet. Reclaim host marker data at
// native allocation/finalization, not only at the next camera publication.
// Successful deferred lists remain queued; native flags and return values stay
// untouched. The renderer performs logical invalidation on its own thread.
static void DiscardFailedNativeMarkerStream(uint8_t* base,uint32_t state){
 using namespace advanced_forge;
 if(!Ptr(state)||uint64_t(state)+10942>=0xc0000000ULL||
    state!=U(base,0x828e66f0)||!(base[state+10941]&0x20))return;
 if(auto* renderer=markerRenderer.load())renderer->DiscardQueuedSceneMarkers();
}
extern "C" void __imp__sub_82182D90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82182D90){
 const auto state=ctx.r3.u32;
 __imp__sub_82182D90(ctx,base);
 DiscardFailedNativeMarkerStream(base,state);
}
extern "C" void __imp__sub_825C13B8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_825C13B8){
 const auto state=ctx.r3.u32;
 __imp__sub_825C13B8(ctx,base);
 DiscardFailedNativeMarkerStream(base,state);
}

// Camera constants are produced by82162398 and later flushed by8215EB28.
// Attach an inert NOP metadata token in the same command buffer so the host
// renderer consumes this view snapshot in draw order, including view clears.
extern "C" void __imp__sub_82162398(PPCContext& __restrict,uint8_t*);
extern "C" void __imp__sub_82157688(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82162398){
 const auto camera=ctx.r3.u32,projection=ctx.r4.u32;
 __imp__sub_82162398(ctx,base);
 using namespace advanced_forge;
 auto* renderer=markerRenderer.load();if(!renderer)return;
 const auto state=U(base,0x828e66f0);
 if(!Ptr(state)||uint64_t(state)+14924>=0xc0000000ULL)return;
 // Native82157948 sets state10941 bit5 after allocation failure;
 //82158040 skips submission in that state. Do not retain host snapshots
 // for commands that the native stream will abandon.
 if(base[state+10941]&0x20){renderer->DiscardQueuedSceneMarkers();return;}
 rex::graphics::SceneMarkers markers;markers.local_view=UINT32_MAX;
 {
  std::lock_guard lock(anchorMutex);
  const auto now=std::chrono::steady_clock::now();
  for(uint32_t i=0;i<anchorViewports.size();++i){
   const auto& viewport=anchorViewports[i];const auto& view=anchorViews[i];
   if(!viewport.valid||camera!=viewport.renderView+4||
      projection!=viewport.renderView+140||
      now-viewport.updated>=std::chrono::milliseconds(250))continue;
   markers.local_view=i;markers.output_rect=viewport.rect;
   markers.camera=Vec(base,state+2032);
   for(unsigned j=0;j<16;++j)markers.world_to_clip[j]=F(base,state+1920+j*4);
   if(enabled.load()&&controlState.showAnchors.load()&&
      now-view.updated<std::chrono::milliseconds(250)){
    markers.material=markerMaterial;markers.time=view.time;
    for(const auto& anchor:view.anchors)
     markers.points.push_back({anchor.position,{1.f,1.f,1.f,1.f}});
   }
   break;
  }
 }
 // state48 denotes the last written word, state52 the buffer limit. Native
 // allocation can submit/rebuild the buffer, so re-read both afterwards.
 auto cursor=U(base,state+48),limit=U(base,state+52);
 if(uint64_t(cursor)+20>=limit){
  auto allocation=ctx;allocation.r3.u64=state;
  __imp__sub_82157688(allocation,base);
  cursor=U(base,state+48);limit=U(base,state+52);
 }
 if(base[state+10941]&0x20){renderer->DiscardQueuedSceneMarkers();return;}
 if(!Ptr(cursor)||(cursor&3)||uint64_t(cursor)+20>=limit||
    uint64_t(cursor)+20>=0xc0000000ULL)return;
 const auto token=markers.local_view==UINT32_MAX?0:renderer->QueueSceneMarkers(std::move(markers));
 const uint32_t words[]={0xc0031000,
  rex::graphics::kSceneMarkerPacketSignature,rex::graphics::kSceneMarkerPacketVersion,
  uint32_t(token>>32),uint32_t(token)};
 for(auto word:words){cursor+=4;const auto value=std::byteswap(word);std::memcpy(base+cursor,&value,4);}
 const auto value=std::byteswap(cursor);std::memcpy(base+state+48,&value,4);
}

extern "C" void __imp__sub_82281268(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82281268){
 const auto player=ctx.r3.u32;
 const bool forgeTick=ctx.lr==0x82281B0C;
 const auto targetOutput=ctx.r4.u32;
 auto rayContext=ctx;
 // Preserve native targeting for non-scenery objects and non-Forge callers.
 __imp__sub_82281268(ctx,base);
 using namespace advanced_forge;
 if(!forgeTick||!enabled.load()||failed||player==0xffffffff||(player&65535)>=16||
    !PhysicsWorld(rayContext,base))return;
 try{
  const auto contact=PlayerContact(base,U(base,rayContext.r13.u32),player,false);
  if(!contact)return;
  const auto monitor=U(base,contact->record+40);
  const auto unit=ObjectPointer(base,physicsHeaders,monitor);
  if(!unit||base[physicsHeaders+(monitor&65535)*16+3]!=0||
     U(base,unit+16)!=0xffffffff||U(base,unit+380)!=player)return;
  const auto variant=U(base,physicsEngine+0xe198+(player&65535)*4);
  uint32_t held=0xffffffff;
  if(variant!=0xffffffff){
   if(variant>=640)throw std::runtime_error("Invalid selection ray holder slot");
   held=U(base,physicsEngine+0x1ac+variant*0x54);
   const auto object=ObjectPointer(base,physicsHeaders,held);
   if(!object||(base[object+154]!=6&&base[object+154]!=10))return;
   const auto& owner=nativeEditors[player&65535];
   if(owner.player!=player||!owner.editor||!owner.ownsMonitorContact)return;
  }
  Load();
  auto& editor=NativeEditor(*bridge,rayContext,base,player,
   [](const std::string& event){REXLOG_INFO("Original H4 Forge event: {}",event);});
  uint32_t selected;std::memcpy(&selected,editor.editor->bytes.data(),4);
  if(std::byteswap(selected)!=held)
   throw std::runtime_error("Original selection ray disagrees with native holder");
  // Counterpart of8244D154: refresh original hit-or-endpoint state in the
  // selection prefix, before the coupled held movement block runs.
  std::optional<NativeSelectionHit> captured;
  const auto rayWorld=NativeSelectionRayWorld(rayContext,base,monitor,held,&captured);
  const auto ray=bridge->UpdateSelectionRay(*editor.editor,rayWorld);
  if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty())try{
   const auto time=U(base,U(base,rayContext.r13.u32)+188);
   if(!Ptr(time))throw std::runtime_error("Missing selection trace clock");
   const auto tick=U(base,time+12);
   static thread_local std::array<uint32_t,16> lastSelectionTrace{};
   auto& previous=lastSelectionTrace[player&65535];
   if(tick<previous||tick-previous>=60){
    previous=tick;
    REXLOG_INFO("Forge selection position: tick {} monitor {:08X} origin {},{},{} direction {},{},{} hit {} target {:08X}",
     tick,monitor,rayWorld.origin[0],rayWorld.origin[1],rayWorld.origin[2],
     rayWorld.direction[0],rayWorld.direction[1],rayWorld.direction[2],ray.hit,ray.datum);
    unsigned reported=0;
    for(unsigned i=0;i<640&&reported<4;++i){
     const auto record=physicsEngine+0x78+0x130+i*0x54;
     if(!(H(base,record)&1)||(H(base,record)&32))continue;
     const auto candidate=U(base,record+4),object=ObjectPointer(base,physicsHeaders,candidate);
     if(!object||(base[object+154]!=6&&base[object+154]!=10))continue;
     const auto pose=NativeSceneryGrabPose(rayContext,base,candidate);
     REXLOG_INFO("Forge selection scenery: tick {} datum {:08X} tag {:08X} live {},{},{} saved {},{},{}",
      tick,candidate,U(base,object),pose[10],pose[11],pose[12],
      F(base,record+16),F(base,record+20),F(base,record+24));
     ++reported;
    }
   }
  }catch(const std::exception& e){REXLOG_WARN("Forge selection trace unavailable: {}",e.what());}
  const auto isScenery=[base](uint32_t datum){
   const auto object=ObjectPointer(base,physicsHeaders,datum);
   return object&&(base[object+154]==6||base[object+154]==10);
  };
  const auto nativeTarget=targetOutput?U(base,targetOutput):0xffffffff;
  // A scenery hit uses H4 ray range/exclusions. A miss or world hit must
  // also remove an H3-only scenery target. Weapon/vehicle target behavior
  // remains native, including when the original ray hits those categories.
  const bool originalScenery=ray.hit&&isScenery(ray.datum);
  const bool worldOrMiss=!ray.hit||ray.datum==0xffffffff;
  if(originalScenery||(worldOrMiss&&isScenery(nativeTarget))){
   if(ray.hit&&!captured)
    throw std::runtime_error("Original selection hit lacks native surface data");
   const auto index=player&65535;
   // Exact destinations written by native82281268. Copy the original
   // hit-or-endpoint bits; do not recompute a different endpoint here.
   std::memcpy(base+physicsEngine+57880+index*12,editor.editor->bytes.data()+44,12);
   if(captured){
    for(unsigned i=0;i<3;++i){
     const auto normal=std::byteswap(std::bit_cast<uint32_t>(captured->normal[i]));
     std::memcpy(base+physicsEngine+58072+index*12+i*4,&normal,4);
    }
   }else{
    // Native miss path copies its stock default normal from8203B0E0.
    std::memcpy(base+physicsEngine+58072+index*12,base+0x8203b0e0,12);
   }
   if(targetOutput){
    const auto target=std::byteswap(ray.datum);
    std::memcpy(base+targetOutput,&target,4);
   }
   ctx.r3.u32=ray.hit?1:0;
  }
 }catch(const std::exception& e){
  failed=true;
  REXLOG_ERROR("Original scenery selection ray failed: {}",e.what());
 }
}

// Original Forge initializer clears all16 native holder slots. Mirror that
// lifecycle directly: pointer/map/tick reuse is not evidence of a surviving
// private held editor. Do not restore old physics flags into the new state.
extern "C" void __imp__sub_82280D80(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280D80){
 __imp__sub_82280D80(ctx,base);
 using namespace advanced_forge;
 ClearNativeEditors();controllerAttachments.clear();physicsObjects.clear();
 coordinates.Reset();physics.Reset();fixedSnap=0xffffffff;ClearAnchorWorld();
 // Player contact state has its own allocation lifetime, not this initializer.
}

// H48244C440 calls82449DD8 for every editor after variant bookkeeping.
// Its native event counterpart82280F98 lacks that editor-reset stage. Reset
// only private H4 editor ownership and its matching native scenery holder;
// never manufacture a grab/release or change stock weapon/vehicle ownership.
extern "C" void __imp__sub_82280F98(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82280F98){
 __imp__sub_82280F98(ctx,base);
 using namespace advanced_forge;
 if(!enabled.load()||failed||!bridge)return;
 try{
  if(!PhysicsWorld(ctx,base))return;
  for(unsigned i=0;i<nativeEditors.size();++i){
   auto& slot=nativeEditors[i];
   if(!slot.editor)continue;
   uint32_t encoded;std::memcpy(&encoded,slot.editor->bytes.data(),4);
   const auto selected=std::byteswap(encoded);
   // Compute the original reset before committing either side. It preserves
   // fields not touched by82449DD8 rather than zeroing the whole editor.
   auto reset=bridge->InitializeHeldEditorState(slot.editor->bytes,
     [](const std::string& event){REXLOG_INFO("Original H4 Forge reset event: {}",event);});
   const auto nativeSlot=U(base,physicsEngine+0xe198+i*4);
   if(selected!=0xffffffff&&nativeSlot<640&&
      U(base,physicsEngine+0x1ac+nativeSlot*0x54)==selected){
    const auto object=ObjectPointer(base,physicsHeaders,selected);
    if(object&&(base[object+154]==6||base[object+154]==10)){
     const uint32_t none=0xffffffff;
     std::memcpy(base+physicsEngine+0xe198+i*4,&none,4);
     std::memcpy(base+physicsEngine+0xe1d8+i*4,reset.bytes.data()+28,4);
    }
   }
   slot.editor=std::move(reset);
   // Original reset does not reset player input or contact-normal history.
   slot.ownsMonitorContact=false;slot.contactMonitor=0xffffffff;
   ClearPlayerAnchors(slot.player);
  }
  controllerAttachments.clear();coordinates.Reset();fixedSnap=0xffffffff;
  // Keep physics metadata for the existing authored-state restoration path.
  // Original82449DD8 does not perform a physics release or rebuild.
 }catch(const std::exception& e){
  failed=true;REXLOG_ERROR("Original scenery editor reset failed: {}",e.what());
 }
}

// State replacement rebinds all allocation groups through821ABAB0. Ordinary
// buffer acquire/release also invokes82344A78, so that callback must not reset
// shared observations (another thread may only be binding a read snapshot).
extern "C" void __imp__sub_821ABAB0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821ABAB0){
 __imp__sub_821ABAB0(ctx,base);
 using namespace advanced_forge;
 {
  std::lock_guard lock(nativeHistoryMutex);
  nativeHistoryPhases={};
 }
 // Same-address restoration can preserve datum salts, allocation pointers and
 // even the tick. These private observations belong to the replaced state.
 // Do not call RestorePhysics: its old flag snapshots must not overwrite the
 // authoritative objects which the native restore has just loaded.
 ClearNativeEditors();controllerAttachments.clear();physicsObjects.clear();
 for(auto& contact:nativePlayerContacts)contact.normalKnown=false;
 coordinates.Reset();physics.Reset();fixedSnap=0xffffffff;ClearAnchorWorld();
}
// Native disposal unpublishes TLS264 without freeing individual history slots.
extern "C" void __imp__sub_82344AE0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344AE0){
 __imp__sub_82344AE0(ctx,base);
 std::lock_guard lock(advanced_forge::nativeHistoryMutex);
 advanced_forge::nativeHistoryPhases={};
}
// Both native initializers zero the complete 9864-byte history allocation.
// Invalidate private phases at the same lifecycle, even if addresses/tick repeat.
extern "C" void __imp__sub_82344A88(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344A88){
 __imp__sub_82344A88(ctx,base);
 std::lock_guard lock(advanced_forge::nativeHistoryMutex);
 advanced_forge::nativeHistoryPhases={};
}
extern "C" void __imp__sub_82344AF8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344AF8){
 __imp__sub_82344AF8(ctx,base);
 std::lock_guard lock(advanced_forge::nativeHistoryMutex);
 advanced_forge::nativeHistoryPhases={};
}
extern "C" void __imp__sub_821224C0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_821224C0){
 using namespace advanced_forge;
 const auto datum=ctx.r3.u32,tls=U(base,ctx.r13.u32);
 const auto history=Ptr(tls)?U(base,tls+264):0;
 uint32_t count=0,index=32,lastDatum=0xffffffff;
 if(Ptr(history)&&uint64_t(history)+9864<0xc0000000ULL){
  count=U(base,history+9856);
  if(count&&count<=32){
   lastDatum=U(base,history+9728+(count-1)*4);
   for(uint32_t i=0;i<count;++i)
    if(U(base,history+9728+i*4)==datum){index=i;break;}
  }
 }
 __imp__sub_821224C0(ctx,base);
 // Observe a completed native removal, not merely an attempted removal.
 // Native code zeroes the removed history; it moves only the last list datum.
 if(index>=32||U(base,history+9856)!=count-1||
    U(base,history+9728+index*4)!=lastDatum)return;
 std::lock_guard lock(nativeHistoryMutex);
 for(const auto slot:{index,count-1})
  if(nativeHistoryPhases[slot].identity.history==history)
   nativeHistoryPhases[slot]={};
}

extern "C" void __imp__sub_82345A80(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82345A80){
 const auto caller=ctx.lr;
 __imp__sub_82345A80(ctx,base);
 if(caller==0x82344DCC&&advanced_forge::nativeFirstHistorySampled)
  *advanced_forge::nativeFirstHistorySampled=(ctx.r3.u32&255)!=0;
}
extern "C" void __imp__sub_82344D50(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344D50){
 const auto datum=ctx.r3.u32,index=ctx.r4.u32;
 bool sampled=false;
 {
  struct Scope {
   bool* prior=advanced_forge::nativeFirstHistorySampled;
   explicit Scope(bool& value){advanced_forge::nativeFirstHistorySampled=&value;}
   ~Scope(){advanced_forge::nativeFirstHistorySampled=prior;}
  } scope(sampled);
  __imp__sub_82344D50(ctx,base);
 }
 advanced_forge::RecordNativeHistoryPhase(ctx,base,datum,index,true,sampled);
}
extern "C" void __imp__sub_82344E90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82344E90){
 const auto datum=ctx.r3.u32,index=ctx.r4.u32;
 __imp__sub_82344E90(ctx,base);
 advanced_forge::RecordNativeHistoryPhase(ctx,base,datum,index,false,true);
}

// Only the prepared scenery detach may defer this native setter. All other
// velocity updates retain their original body wake and notification behavior.
REX_HOOK_RAW(sub_820F29C8){
 using namespace advanced_forge;
 TraceNativeHeldWriter(ctx,base,ctx.r3.u32,"velocity");
 auto* attachment=nativeDetachAttachment;
 auto* grab=nativeGrabTransaction;
 if(ctx.lr==0x823318CC&&attachment&&attachment->deferVelocity&&grab&&
    grab->datum==attachment->datum&&grab->error.empty()&&
    ctx.r3.u32==attachment->datum){
  try{
   if(attachment->fallbackVelocity)throw std::runtime_error("Repeated deferred detach velocity");
   const auto linear=ctx.r4.u32,angular=ctx.r5.u32;
   if(!Ptr(linear)||!Ptr(angular)||uint64_t(linear)+12>=0xc0000000ULL||
      uint64_t(angular)+12>=0xc0000000ULL)
    throw std::runtime_error("Invalid native detach velocity arguments");
   const std::array<V,2> velocity{Vec(base,linear),Vec(base,angular)};
   for(const auto& vector:velocity)for(float value:vector)
    if(!std::isfinite(value))throw std::runtime_error("Nonfinite native detach fallback");
   attachment->fallbackVelocity=velocity;
   return; // Void call; the native caller immediately replaces r3.
  }catch(const std::exception& e){
   grab->error=e.what();
   attachment->fallbackVelocity.reset(); // The native setter below owns this failure path.
  }
 }
 __imp__sub_820F29C8(ctx,base);
}

extern "C" void __imp__sub_823317C0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_823317C0){
 using namespace advanced_forge;
 const auto caller=ctx.lr;
 const auto datum=ctx.r3.u32;
 const auto grab=nativeGrabTransaction;
 std::optional<NativeDetachAttachment> attachment;
 if(enabled.load()&&!failed&&bridge&&PhysicsWorld(ctx,base)){
  const auto object=ObjectPointer(base,physicsHeaders,datum);
  if(object){
   const auto type=base[physicsHeaders+(datum&65535)*16+3];
   if((type==6||type==10)&&U(base,object+16)!=0xffffffff)
    attachment=NativeDetachAttachment{datum,object,U(base,object+16),int8_t(base[object+20])};
  }
 }
 if(attachment){
  attachment->deferVelocity=caller==0x82120A18&&grab&&
    grab->datum==datum&&grab->error.empty();
  attachment->rebuildAfterUnlink=(U(base,attachment->object+172)&kConnected)!=0;
 }
 {
  struct Scope {
   NativeDetachAttachment* prior=nativeDetachAttachment;
   explicit Scope(NativeDetachAttachment* value){nativeDetachAttachment=value;}
   ~Scope(){nativeDetachAttachment=prior;}
  } scope(attachment?&*attachment:nullptr);
  __imp__sub_823317C0(ctx,base);
 }
 if(!attachment||!attachment->fallbackVelocity)return;
 bool applied=false;
 if(grab&&grab->error.empty()&&!failed&&enabled.load()&&bridge){
  try{applied=ApplyNativeDetachPointVelocity(ctx,base,datum);}
  catch(const std::exception& e){grab->error=e.what();}
 }
 if(!applied){
  // H4 queries the former parent here, after association/maintenance, when
  // localized history rejects. Retain the captured native values only on error.
  if(grab&&grab->error.empty()&&!failed&&enabled.load()&&bridge){
   try{attachment->fallbackVelocity=NativeObjectVelocities(ctx,base,attachment->parent);}
   catch(const std::exception& e){grab->error=e.what();}
  }
  try{ApplyNativeDetachFallback(ctx,base,*attachment);}
  catch(const std::exception& e){
   if(grab)grab->error=e.what();
   else{failed=true;REXLOG_ERROR("Deferred detach velocity failed: {}",e.what());}
  }
 }
}

// H482450E10 calls8298E798(root,false), which accepts a valid root datum.
// H3's corresponding82345288 additionally requires managed-list membership.
// Restrict that difference to child detachment in our scenery grab transaction;
// native82120960 still owns detachment, notifications and variant bookkeeping.
extern "C" void __imp__sub_82345288(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82345288){
 using namespace advanced_forge;
 const auto caller=ctx.lr;
 const auto root=ctx.r3.u32,flag=ctx.r4.u32;
 const auto grab=nativeGrabTransaction;
 __imp__sub_82345288(ctx,base);
 if(caller!=0x822801F8||flag||!grab||!grab->error.empty()||failed||
    !enabled.load()||!bridge||ctx.r27.u32!=grab->datum||ctx.r23.u32!=grab->player||
    root==grab->datum||root==0xffffffff)return;
 const auto object=ObjectPointer(base,physicsHeaders,grab->datum);
 if(!object||U(base,object+16)==0xffffffff||!ObjectPointer(base,physicsHeaders,root))return;
 ctx.r3.u32=1;
}

extern "C" void __imp__sub_82283B90(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82283B90){
 using namespace advanced_forge;
 auto grab=nativeGrabTransaction;
 if(grab&&grab->error.empty()&&ctx.lr==0x822802A8&&ctx.r3.u32==grab->datum&&ctx.r4.u32==0xffffffff){
  try{
   const auto slot=U(base,physicsEngine+0xe198+(grab->player&65535)*4);
   if(slot>=640||U(base,physicsEngine+0x1ac+slot*0x54)!=grab->datum)
    throw std::runtime_error("Native grab did not commit expected ownership");
   // H4824511B0/8244E2C0 consume the last editor ray state; neither
   // re-runs8244C740 at grab. The native prefix hook supplies that state.
   const auto object=ObjectPointer(base,physicsHeaders,grab->datum);
   if(!object)throw std::runtime_error("Native committed grab lost its object");
   // Original82450E10 performs selection/dequeue/physics/grab setup after
   // either result of its detach predicate. A retained parent suppresses the
   // later movement stage, not this ownership transaction.
   SelectNativeHeldEditor(*bridge,ctx,base,grab->player,grab->datum,true,
     [](const std::string& event){REXLOG_INFO("Original H4 Forge event: {}",event);});
   grab->selected=true;
  }catch(const std::exception& e){grab->error=e.what();}
 }
 // Never omit H3's queue removal/notification, including on a bridge failure.
 __imp__sub_82283B90(ctx,base);
}
// Original H4 creation8244EF80 moves a non-phased spawn point toward the
// monitor before collision placement. Stock H3 has no authored Phased flag;
// its unrelated multiplayer bit1 must never be interpreted as that flag.
extern "C" void __imp__sub_8227F2A0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227F2A0){
 using namespace advanced_forge;
 NativeCreatePlacement creation{ctx.r3.u32,ctx.r4.u32,ctx.r5.u32!=0,{}};
 NativeCreatePlacementScope scope(&creation);
 __imp__sub_8227F2A0(ctx,base);
}
extern "C" void __imp__sub_822836D8(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_822836D8){
 using namespace advanced_forge;
 auto creation=nativeCreatePlacement;
 if(creation&&creation->hasPoint&&ctx.lr==0x8227F344&&
    creation->tag==ctx.r3.u32&&creation->player!=0xffffffff&&
    (creation->player&65535)<16&&enabled.load()&&!failed&&PhysicsWorld(ctx,base)){
  const auto definition=TagDefinition(base,creation->tag);
  const auto type=definition?H(base,definition):0xffff;
  if((type==6||type==10)&&!(H(base,definition+2)&(1u<<11))){
   try{
    if(!Ptr(ctx.r4.u32))throw std::runtime_error("Invalid scenery creation point");
    Load();
    std::optional<V> monitor;
    if(ctx.r5.u32!=0xffffffff)monitor=NativePhysicsPoint(ctx,base,ctx.r5.u32);
    const auto requested=Vec(base,ctx.r4.u32);
    const auto placement=bridge->PrepareSpawnPlacement(requested,monitor,
                                                      F(base,definition+4));
    if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty())
     REXLOG_INFO("Forge spawn query: tag {:08X} requested {},{},{} adjusted {},{},{} radius {}",
      creation->tag,requested[0],requested[1],requested[2],placement.point[0],placement.point[1],placement.point[2],placement.radius);
    // Write only after the whole original prefix completed successfully.
    for(unsigned i=0;i<3;++i){
     const auto value=std::byteswap(std::bit_cast<uint32_t>(placement.point[i]));
     std::memcpy(base+ctx.r4.u32+i*4,&value,4);
    }
    creation->radius=placement.radius;
   }catch(const std::exception& e){
    failed=true;REXLOG_ERROR("Original scenery creation placement failed: {}",e.what());
   }
  }
 }
 // Original H3 owns query success, output propagation, and budget rejection.
 const auto queryPoint=ctx.r4.u32;
 const bool traceCreation=creation&&creation->radius&&!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()&&Ptr(queryPoint);
 __imp__sub_822836D8(ctx,base);
 if(traceCreation){
  const auto placed=Vec(base,queryPoint);
  REXLOG_INFO("Forge spawn query result: tag {:08X} success {} point {},{},{}",
   creation->tag,ctx.r3.u32,placed[0],placed[1],placed[2]);
 }
}
extern "C" void __imp__sub_822835E0(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_822835E0){
 using namespace advanced_forge;
 const auto creation=nativeCreatePlacement;
 const bool overrideRadius=creation&&creation->radius&&ctx.lr==0x822836FC&&
                           ctx.r3.u32==creation->tag;
 __imp__sub_822835E0(ctx,base);
 if(overrideRadius)ctx.f1.f64=*creation->radius;
}

// Successful native creation8227F2A0 reaches this same transaction after
//821E2898 returns a valid variant object. Keep one ownership/grab initializer
// for both new objects and re-grabs; pre-creation point adjustment is separate.
extern "C" void __imp__sub_8227E810(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_8227E810){
 const auto player=ctx.r3.u32,slot=ctx.r4.u32;
 using namespace advanced_forge;
 std::optional<NativeGrabTransaction> grab;
 if(enabled.load()&&!failed&&slot<640&&player!=0xffffffff&&(player&65535)<16&&
    PhysicsWorld(ctx,base)){
  const auto datum=U(base,physicsEngine+0x1ac+slot*0x54);
  const auto pointer=ObjectPointer(base,physicsHeaders,datum);
  const auto definition=pointer?TagDefinition(base,U(base,pointer)):0;
  const auto type=pointer?base[physicsHeaders+(datum&65535)*16+3]:255;
  if(pointer&&(type==6||type==10)&&definition&&
     !(H(base,definition+2)&(1u<<11))){
   try{
    if(nativeGrabTransaction)throw std::runtime_error("Nested native scenery grab");
    Load();
    auto existing=physicsObjects.find(datum);
    if(existing==physicsObjects.end()||!PhysicsValid(base,datum,existing->second)){
     const auto authored=AuthoredPhysics(base,pointer);
     physicsObjects[datum]={pointer,U(base,pointer),U(base,pointer+172),authored,authored,false};
    }
    grab=NativeGrabTransaction{player,datum};
   }catch(const std::exception& e){
    failed=true;REXLOG_ERROR("Original scenery grab preparation failed: {}",e.what());
   }
  }
 }
 {
  NativeGrabTransactionScope scope(grab?&*grab:nullptr);
  __imp__sub_8227E810(ctx,base);
 }
 if(grab){
  const auto abortGrab=[&](const char* stage,const std::string& error){
   failed=true;
   // Native ownership/dequeue already ran. Revoke private editor/controller
   // state on either failure path, preserving the native return registers.
   auto cleanup=ctx;
   try{RestorePhysics(cleanup,base);}
   catch(const std::exception& restoration){
    // RestorePhysics revokes private ownership before rebuilding bodies.
    // Retain remaining physics metadata rather than claim it was restored.
    REXLOG_ERROR("Original scenery grab restoration failed: {}",restoration.what());
   }
   REXLOG_ERROR("Original scenery {} failed: {}",stage,error);
  };
  if(!grab->error.empty()){
   abortGrab("selection",grab->error);return;
  }
  // A rejected transaction has no original selection.
  if(!grab->selected)return;
  try{
   auto object=physicsObjects.find(grab->datum);
   if(object==physicsObjects.end())throw std::runtime_error("Missing scenery grab metadata");
   const auto mode=object->second.mode.value_or(object->second.authoredMode);
   const bool placement=InitializeNativeSceneryHold(*bridge,ctx,base,player,grab->datum,mode,
    [](const std::string& event){REXLOG_INFO("Original H4 Forge event: {}",event);});
   if(placement){
    // H3's cache is consumed by native menus; keep it synchronized with the
    // original projected/clamped distance, never the old radius*2+1 heuristic.
    const auto& editor=*nativeEditors[player&65535].editor;
    std::memcpy(base+physicsEngine+0xe1d8+(player&65535)*4,editor.bytes.data()+28,4);
   }
   ActivateNativeSceneryHold(ctx,base,player,grab->datum);
  }catch(const std::exception& e){
   abortGrab("grab initialization",e.what());
  }
  return;
 }
}

// The extracted native prefix/suffix retain all non-movement H3 behavior.
// This dispatch replaces the entire held controller block, never one of its
// inner calls (which would leave a second native controller running).
#include "../../work/h4-forge-research/isolated/native_forge_tick.inl"
static bool DispatchOriginalSceneryHeldStage(PPCContext& ctx,uint8_t* base,
                                            uint32_t player,uint32_t datum){
 using namespace advanced_forge;
 if(player==0xffffffff||(player&65535)>=nativeEditors.size())return false;
 auto& slot=nativeEditors[player&65535];
 if(slot.player!=player||!slot.editor||!slot.ownsMonitorContact)return false;
 try{
  if(!enabled.load()||failed||!bridge)
   throw std::runtime_error("Owned scenery tick lost original lifecycle");
  const auto owner=ResolveNativeSceneryOwner(ctx,base,player,datum,true);
  if(owner.monitor!=slot.contactMonitor)
   throw std::runtime_error("Owned scenery tick changed monitor");
  uint32_t selected;std::memcpy(&selected,slot.editor->bytes.data(),4);
  if(std::byteswap(selected)!=datum)
   throw std::runtime_error("Owned scenery tick changed original selection");
  // The replacement controller no longer calls native placement every frame.
  // Keep the UI selection fresh and consume queued Normal/Fixed/Phased changes
  // here, before testing instance eligibility: a transition may rebuild it.
  UpdatePhysics(ctx,base,datum);
  // Original8244D514..D5A8 skips movement/follow for attached objects or
  // disconnected instances, but8244D628 still refreshes editor+8 through
  // the parent-aware origin query. Selection and ownership survive the skip.
  const bool coupled=NativeCoupledSceneryEligible(base,datum);
  if(coupled)
   RunNativeCoupledSceneryStage(ctx,base,player,datum,owner.monitor,owner.localIndex);
  const auto origin=NativeObjectOrigin(ctx,base,datum);
  for(unsigned i=0;i<3;++i){
   const auto encoded=std::byteswap(std::bit_cast<uint32_t>(origin[i]));
   std::memcpy(slot.editor->bytes.data()+8+i*4,&encoded,4);
  }
  if(!coupled)return true;
  // The skipped native block marks changes while manipulation is active,
  // then serializes once when it stops. Keep that stock variant bookkeeping,
  // using the original input state (native input764 is deliberately disarmed).
  const auto dirty=physicsEngine+58520+(player&65535);
  if(slot.input.active)base[dirty]=1;
  else if(base[dirty]){
   SyncNativeSceneryPose(ctx,base,datum);
   base[dirty]=0;
  }
 }catch(const std::exception& e){
  RestorePhysics(ctx,base);ClearNativeEditors();failed=true;
  REXLOG_ERROR("Original scenery held lifecycle failed: {}",e.what());
 }
 // Once this stage owns the frame, even a late failure must not execute the
 // native spring controller after partially submitting an original target.
 return true;
}
extern "C" void __imp__sub_82281A98(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_82281A98){
 using namespace advanced_forge;
 const auto player=ctx.r4.u32,index=player&65535;
 HeldMovementScope movementScope;
 // Original tick820B37D0 runs unit input before this Forge callback.
 // H3 player+40 identifies the controlled unit; its processed movement is
 // unit+496/+500/+504 (821EC0E0 ->820B8608), not raw keyboard/stick input.
 const auto movementTls=U(base,ctx.r13.u32);
 if(index<16&&Ptr(movementTls)){
  const auto players=U(base,movementTls+0x60),objects=U(base,movementTls+0xa8);
  if(Ptr(players)&&Ptr(objects)){
   const auto playerTable=U(base,players+0x44),headers=U(base,objects+0x44);
   if(Ptr(playerTable)&&Ptr(headers)){
    const auto unit=ObjectPointer(base,headers,U(base,playerTable+index*880+40));
    if(unit){
     const auto movement=Vec(base,unit+496);
     if(std::all_of(movement.begin(),movement.end(),[](float v){return std::isfinite(v);}))
      heldMovement=HeldMovement{player,movement};
    }
   }
  }
 }
 RunNativeForgeTick(ctx,base,DispatchOriginalSceneryHeldStage);
}

#include "advanced_forge_menu.inl"
extern "C" void __imp__sub_824F5D40(PPCContext& __restrict,uint8_t*);
REX_HOOK_RAW(sub_824F5D40){
 const auto screen=ctx.r3.u32;
 __imp__sub_824F5D40(ctx,base);
 try{advanced_forge::AddPhysicsMenu(ctx,base,screen);}
 catch(const std::exception& e){
  advanced_forge::RestorePhysics(ctx,base);advanced_forge::failed=true;
  REXLOG_ERROR("Advanced Forge native menu unavailable: {}",e.what());
 }
 if(!REXCVAR_GET(halo3mp_advanced_forge_trace).empty()){
  const auto source=advanced_forge::U(base,screen+0x1a88);
  REXLOG_INFO("Advanced Forge native properties: screen {:08X} slot {} source {:08X}",screen,advanced_forge::U(base,screen+0x1a8c),source);
 }
}

// Override the motion array before H3 derives compound shape, group and
// body configuration. Overriding only the final constructor's motion word
// would leave those earlier decisions inconsistent with a keyframed body.
REX_HOOK_RAW(sub_82267DD8){
 const auto request=advanced_forge::SceneryConstructionRequest(base,ctx.r3.u32);
 if(request&&!REXCVAR_GET(halo3mp_advanced_forge_trace).empty())
  REXLOG_INFO("Forge physics constructor: requested {:08X} owner {:08X} keyframed {}",request->datum,advanced_forge::Ptr(ctx.r3.u32)?advanced_forge::U(base,ctx.r3.u32+8):0xffffffff,request->keyframed);
 if(!request||!request->keyframed||!advanced_forge::Ptr(ctx.r3.u32)||
    advanced_forge::U(base,ctx.r3.u32+8)!=request->datum){
  __imp__sub_82267DD8(ctx,base);return;
 }
 if(!advanced_forge::Ptr(ctx.r4.u32)||!advanced_forge::Ptr(ctx.r8.u32))
  throw std::runtime_error("Invalid scenery body creation descriptor");
 const auto phmo=advanced_forge::U(base,ctx.r4.u32+72);
 if(!advanced_forge::Ptr(phmo))throw std::runtime_error("Missing scenery body physics model");
 const auto count=advanced_forge::U(base,phmo+88),address=ctx.r8.u32;
 // Original82267A88 reserves64 bytes for this per-body array at stack224.
 if(count>64||uint64_t(address)+count>=0xc0000000ULL)
  throw std::runtime_error("Scenery body motion array exceeds native capacity");
 struct RestoreMotion {
  uint8_t* destination;std::vector<uint8_t> original;
  ~RestoreMotion(){std::copy(original.begin(),original.end(),destination);}
 } restore{base+address,std::vector<uint8_t>(base+address,base+address+count)};
 std::fill_n(base+address,count,uint8_t(6));
 __imp__sub_82267DD8(ctx,base);
}


