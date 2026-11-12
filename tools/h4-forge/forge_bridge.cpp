#include "forge_bridge.h"
#include "forge_original.h"
#include <windows.h>
#include <fstream>
#include <filesystem>
#include <stdexcept>
#include <bit>
#include <cmath>
#include <set>
namespace {
// Scene indices0..64 accommodate held storage plus all64 query results.
//65 is the standalone-object adapter,66 a prior target outside the query.
constexpr uint32_t monitorIndex=67;
thread_local const advanced_forge::Scene* active=nullptr;
struct MonitorViewCall {std::array<float,3> angles{},direction{};bool notified=false;};
thread_local MonitorViewCall* monitorView=nullptr;
thread_local std::set<uint32_t>* visibleObjects=nullptr;
struct CoordinateEdit {uint32_t datum;advanced_forge::CoordinatePose result;};
thread_local CoordinateEdit* coordinateEdit=nullptr;
struct PhysicsSelection {bool held,keyframed,normalStateOverride;};
thread_local const PhysicsSelection* physicsSelection=nullptr;
struct PhysicsTransitionCall {
 const advanced_forge::PhysicsTransition& input;
 const advanced_forge::PhysicsBodyAdapter& update;
 std::array<float,3> point;
};
thread_local PhysicsTransitionCall* physicsTransition=nullptr;
thread_local const std::function<void(const std::string&)>* editorEventSink=nullptr;
struct HeldSelectionCall {uint32_t player;const advanced_forge::HeldSelectionWorld& world;};
thread_local const HeldSelectionCall* heldSelection=nullptr;
struct SelectionRayCall {const advanced_forge::SelectionRayWorld& world;size_t next=0;};
thread_local SelectionRayCall* selectionRay=nullptr;
thread_local const std::function<std::optional<advanced_forge::SelectionRayHit>(const advanced_forge::SelectionRayRequest&)>* obstructionRay=nullptr;
thread_local const advanced_forge::ManipulationInput* manipulationInput=nullptr;
struct HeldMagnetCall {bool localHolder;uint32_t previousTarget;};
thread_local const HeldMagnetCall* heldMagnet=nullptr;
struct HeldUpdateCall {
 const advanced_forge::HeldUpdateWorld& world;
 advanced_forge::HeldUpdateResult result;
 bool monitorFollow=false;
};
thread_local HeldUpdateCall* heldUpdate=nullptr;
thread_local const advanced_forge::SceneryContactWorld* sceneryContact=nullptr;
thread_local const advanced_forge::MonitorContactWorld* monitorContact=nullptr;
thread_local const advanced_forge::ControlledBody* controlledBody=nullptr;
constexpr uint32_t controlledBodyAddress=0x150000;
std::array<float,4> ControllerVector(uint8_t* base,uint32_t address){
 std::array<float,4> result;
 for(unsigned i=0;i<4;++i){
  result[i]=std::bit_cast<float>(REX_LOAD_U32(address+i*4));
  if(!std::isfinite(result[i]))throw std::runtime_error("Nonfinite original controller output");
 }
 return result;
}
HeldUpdateCall& CurrentHeldUpdate(){
 if(!heldUpdate)throw std::runtime_error("H4 held world query outside held update");
 return *heldUpdate;
}
uint32_t HeldWorldDatum(uint32_t index){
 if(!active)throw std::runtime_error("H4 held world query outside scene");
 if(index==monitorIndex)return CurrentHeldUpdate().world.monitorDatum;
 if(index>=active->objects.size())throw std::runtime_error("Invalid held world datum");
 return active->objects[index].datum;
}
void StoreVector(uint8_t* base,uint32_t address,const std::array<float,3>& vector){
 for(unsigned i=0;i<3;++i){
  if(!std::isfinite(vector[i]))throw std::runtime_error("Nonfinite H4 world query result");
  REX_STORE_U32(address+i*4,std::bit_cast<uint32_t>(vector[i]));
 }
}
uint32_t VisibleDatum(uint32_t index){
 if(!heldMagnet)return index;
 if(index==66)return heldMagnet->previousTarget;
 if(!active||index>=active->objects.size())throw std::runtime_error("Invalid H4 marker visibility datum");
 return active->objects[index].datum;
}

PhysicsTransitionCall& CurrentPhysicsTransition(){
 if(!physicsTransition)throw std::runtime_error("H4 physics world query outside transition");
 return *physicsTransition;
}

const PhysicsSelection& CurrentPhysicsSelection(){
 if(!physicsSelection)throw std::runtime_error("H4 physics query outside selector");
 return *physicsSelection;
}

void word(uint8_t* base,uint32_t a,uint32_t v){REX_STORE_U32(a,v);}
void real(uint8_t* base,uint32_t a,float v){word(base,a,std::bit_cast<uint32_t>(v));}
float get(uint8_t* base,uint32_t a){return std::bit_cast<float>(REX_LOAD_U32(a));}
void ProjectContactSet(uint8_t* base,uint32_t table,uint32_t triangles,const advanced_forge::ContactSet& contacts){
 if(contacts.samples.size()>256||contacts.primary< -1||
    (contacts.primary>=0&&uint32_t(contacts.primary)>=contacts.samples.size())||!std::isfinite(contacts.closestDistance))
  throw std::runtime_error("Invalid projected contact set");
 // Only fields read by the two original selection routines are projected.
 // Native BSP/triangle pointers must never be dereferenced in this arena.
 std::memset(base+table,0,24+256*32);
 word(base,table,static_cast<uint32_t>(contacts.primary));
 real(base,table+4,contacts.closestDistance);word(base,table+20,uint32_t(contacts.samples.size()));
 for(unsigned i=0;i<contacts.samples.size();++i){
  const auto& sample=contacts.samples[i];const uint32_t triangle=triangles+i*80;
  if(!std::isfinite(sample.planeDistance)||!std::isfinite(sample.closestDistance))
   throw std::runtime_error("Nonfinite contact distance");
  StoreVector(base,triangle,sample.normal);
  for(unsigned j=0;j<3;++j)StoreVector(base,triangle+32+j*12,sample.triangle[j]);
  word(base,table+32+i*32,triangle);
  real(base,table+36+i*32,sample.planeDistance);
  real(base,table+40+i*32,sample.closestDistance);
  StoreVector(base,table+44+i*32,sample.closestPoint);
 }
}
const advanced_forge::Object& object(uint32_t i){
 if(!active||i>=active->objects.size())throw std::runtime_error("Invalid H4 scene query");
 return active->objects[i];
}
void ValidateSceneQuery(const advanced_forge::Scene& scene){
 if(scene.objects.empty()||scene.objects.size()>65)
  throw std::runtime_error("Invalid scene storage capacity");
 const auto count=scene.nearbyOrder?scene.nearbyOrder->size():scene.objects.size();
 if(count>64)throw std::runtime_error("Invalid scene query capacity");
 std::set<uint32_t> seen;
 if(scene.nearbyOrder)for(auto index:*scene.nearbyOrder)
  if(index>=scene.objects.size()||!seen.insert(index).second)
   throw std::runtime_error("Invalid scene query index");
}
}
namespace h4_forge_original {
void sub_82CD55F0(PPCContext& ctx,uint8_t*){
 if(!controlledBody||ctx.r3.u32!=controlledBodyAddress)
  throw std::runtime_error("Invalid original controller activation");
 controlledBody->activate();
}
void sub_82CD40A8(PPCContext& ctx,uint8_t* base){
 if(!controlledBody||ctx.r3.u32!=controlledBodyAddress)
  throw std::runtime_error("Invalid original controller relocation");
 const auto position=ControllerVector(base,ctx.r4.u32),orientation=ControllerVector(base,ctx.r5.u32);
 controlledBody->relocate(position,orientation);
 for(unsigned i=0;i<4;++i){
  REX_STORE_U32(controlledBodyAddress+288+i*4,std::bit_cast<uint32_t>(position[i]));
  REX_STORE_U32(controlledBodyAddress+352+i*4,std::bit_cast<uint32_t>(orientation[i]));
 }
}
void controller_dispatch(PPCContext& ctx,uint8_t* base,uint32_t address){
 if(!controlledBody||ctx.r3.u32!=controlledBodyAddress+224||(address!=0x100&&address!=0x104))
  throw std::runtime_error("Unexpected original controller virtual call");
 const auto value=ControllerVector(base,ctx.r4.u32);
 const bool linear=address==0x100;
 if(linear)controlledBody->setLinearVelocity(value);else controlledBody->setAngularVelocity(value);
 for(unsigned i=0;i<4;++i)
  REX_STORE_U32(controlledBodyAddress+(linear?432:448)+i*4,std::bit_cast<uint32_t>(value[i]));
}
void sub_82486B78(PPCContext& ctx,uint8_t* base){
 if(!sceneryContact||ctx.r5.u32!=sceneryContact->objectType||ctx.r6.u32||ctx.r9.u32!=(monitorContact&&monitorContact->movementMode==1?1u:0u))
  throw std::runtime_error("Unexpected scenery contact collection context");
 std::array<float,3> center;
 for(unsigned i=0;i<3;++i)center[i]=get(base,ctx.r8.u32+i*4);
 const auto contacts=sceneryContact->collect(center,float(ctx.f1.f64),float(ctx.f2.f64));
 // Scenery/crate cannot admit the character-only special surface categories.
 // Reject an inconsistent native projection before any character side effects.
 if(contacts.flags&&!monitorContact)throw std::runtime_error("Non-scenery contact category in scenery response");
 word(base,ctx.r4.u32,contacts.flags);
 ProjectContactSet(base,ctx.r3.u32,0x140000,contacts.geometry);
}
void sub_822D1158(PPCContext& ctx,uint8_t* base){
 if(!sceneryContact||ctx.r3.u32!=65||ctx.r5.u32)
  throw std::runtime_error("Unexpected scenery contact velocity request");
 std::array<float,3> velocity;
 for(unsigned i=0;i<3;++i){
  velocity[i]=get(base,ctx.r4.u32+i*4);
  if(!std::isfinite(velocity[i]))throw std::runtime_error("Nonfinite original contact velocity");
 }
 sceneryContact->setLinearVelocity(velocity);
}
void sub_82943B08(PPCContext& ctx,uint8_t*){
 if(!monitorContact||!sceneryContact||ctx.r3.u32!=65||ctx.r4.u32||
    ctx.r5.u32!=1||ctx.r6.u32!=1||ctx.r7.u32)
  throw std::runtime_error("Unexpected original monitor surface notification");
 monitorContact->surfaceNotification();
}
void sub_82260CF0(PPCContext& ctx,uint8_t* base){
 if(sceneryContact){
  if(ctx.r3.u32!=65||ctx.r5.u32)throw std::runtime_error("Unexpected scenery response motion query");
  StoreVector(base,ctx.r4.u32,sceneryContact->velocity);return;
 }
 auto& call=CurrentHeldUpdate();
 const auto datum=HeldWorldDatum(ctx.r3.u32);
 if(ctx.r5.u32){
  if(!call.world.objectVelocities)throw std::runtime_error("Missing native angular prediction velocities");
  const auto velocities=call.world.objectVelocities(datum);
  if(ctx.r4.u32)StoreVector(base,ctx.r4.u32,velocities[0]);
  StoreVector(base,ctx.r5.u32,velocities[1]);
 }else if(ctx.r4.u32)StoreVector(base,ctx.r4.u32,call.world.objectMotion(datum));
 // Original82260CF0 and its entire helper closure leave f1 unchanged.
 //824BEB50 consumes its original incoming time, not a velocity-query return.

}
void sub_82243068(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 if(!call.world.objectOrientation)throw std::runtime_error("Missing native prediction orientation");
 const auto axes=call.world.objectOrientation(HeldWorldDatum(ctx.r3.u32));
 if(ctx.r4.u32)StoreVector(base,ctx.r4.u32,axes[0]);
 if(ctx.r5.u32)StoreVector(base,ctx.r5.u32,axes[1]);
}
void sub_8249B1F8(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 if(ctx.r3.u32!=0xc5000||!call.world.hasInstance||!call.world.bodyCount||!call.world.objectPredictionLocalPoint)
  throw std::runtime_error("Missing native prediction local center");
 StoreVector(base,ctx.r4.u32,call.world.objectPredictionLocalPoint(HeldWorldDatum(0)));
}
void sub_822410D0(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 const auto point=call.world.objectReferencePoint(HeldWorldDatum(ctx.r3.u32));
 if(!call.monitorFollow&&ctx.lr==0x8244AB68){
  call.result.referencePoint=point;
  call.result.movementDelta={float(ctx.f29.f64),float(ctx.f30.f64),float(ctx.f31.f64)};
  for(unsigned i=0;i<3;++i)call.result.priorTarget[i]=get(base,0x21aec+124+i*4);
 }
 StoreVector(base,ctx.r4.u32,point);
}
void sub_82415970(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 if(!call.monitorFollow||!call.world.pointOutsideWorld||ctx.r3.u64!=0x0000100900000000ULL||
    ctx.r5.u32!=0xffffffff||ctx.r6.u32!=0xffffffff)
  throw std::runtime_error("Unsupported original point-containment contract");
 std::array<float,3> point;
 for(unsigned axis=0;axis<3;++axis){
  point[axis]=get(base,ctx.r4.u32+axis*4);
  if(!std::isfinite(point[axis]))throw std::runtime_error("Nonfinite follow containment point");
 }
 //8244AF48 never reads the16-byte result record: it reuses that stack
 // storage immediately. Only the boolean is mapped. Do not expose this
 // boundary to callers that require H4 BSP/instance identifiers.
 ctx.r3.u32=call.world.pointOutsideWorld(point)?1:0;
}
void sub_82451BA8(PPCContext& ctx,uint8_t*){
 auto& call=CurrentHeldUpdate();
 ctx.r3.u32=call.world.geometryContainsObject(HeldWorldDatum(ctx.r3.u32));
}
void sub_822AD348(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 if(ctx.r3.u32!=0xc5000||ctx.r4.u32>=call.world.bodyCount)
  throw std::runtime_error("Invalid original held body transform query");
 const auto pose=call.world.bodyTransform(ctx.r4.u32);
 for(unsigned i=0;i<13;++i){
  if(!std::isfinite(pose[i]))throw std::runtime_error("Nonfinite held body transform");
  real(base,ctx.r5.u32+i*4,pose[i]);
 }
}
void sub_82235650(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 std::array<float,3> point;
 for(unsigned i=0;i<3;++i)point[i]=get(base,ctx.r4.u32+i*4);
 const auto contact=call.world.resolveContact(HeldWorldDatum(ctx.r3.u32),point);
 //82235874..82235890 refreshes the cached point independently of whether
 // response ultimately returns true. Preserve this in/out parameter always.
 StoreVector(base,ctx.r4.u32,point);
 if(contact)StoreVector(base,ctx.r5.u32,*contact);
 ctx.r3.u32=contact?1:0;
}
void sub_82400D48(PPCContext& ctx,uint8_t* base){
 if(!monitorView||ctx.r3.u32!=0||ctx.lr!=0x823FC440||monitorView->notified)
  throw std::runtime_error("Unexpected original monitor view notification");
 const auto tls=REX_LOAD_U32(ctx.r13.u32);
 const auto view=REX_LOAD_U32(tls+100)+288;
 for(unsigned axis=0;axis<3;++axis){
  const float value=get(base,view+20+axis*4);
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite original monitor view angle");
  monitorView->angles[axis]=value;
  // Original823FC348 saves its facing argument at stack112 before building
  // quaternion/angles. Capture it at the exact notification call, avoiding
  // an inverse angle conversion or a guessed monitor-target direction.
  const float facing=get(base,ctx.r1.u32+112+axis*4);
  if(!std::isfinite(facing))throw std::runtime_error("Nonfinite original monitor facing");
  monitorView->direction[axis]=facing;
 }
 monitorView->notified=true;
}
void sub_82452930(PPCContext& ctx,uint8_t* base){
 auto& call=CurrentHeldUpdate();
 if(ctx.r3.u32!=(call.monitorFollow?monitorIndex:0u)||call.result.submitted)
  throw std::runtime_error("Unexpected original target submission");
 call.result.submittedDatum=HeldWorldDatum(ctx.r3.u32);
 for(unsigned i=0;i<13;++i){
  const float value=get(base,ctx.r4.u32+i*4);
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite original held target");
  call.result.pose[i]=value;
 }
 call.result.controllerParameter=static_cast<float>(ctx.f1.f64);
 call.result.submitted=true;
}
void sub_82232AC8(PPCContext& ctx,uint8_t* base){
 if(!manipulationInput||ctx.r3.u32!=0)
  throw std::runtime_error("H4 input eligibility outside manipulation processing");
 if(manipulationInput->eligible&&ctx.r4.u32)
  word(base,ctx.r4.u32,manipulationInput->hasHeldObject?65:0xffffffff);
 ctx.r3.u32=manipulationInput->eligible?1:0;
}
void sub_8312D878(PPCContext& ctx,uint8_t* base){
 if(!editorEventSink||ctx.r4.u32!=9||ctx.r5.u64||ctx.r6.u64||ctx.r7.u64||ctx.r8.u64||ctx.r9.u64||ctx.r10.u64)
  throw std::runtime_error("Unexpected original Forge lifecycle event");
 // Only the three original constructor/selection event strings are accepted.
 if(ctx.r3.u32!=0x82131288&&ctx.r3.u32!=0x82131298&&ctx.r3.u32!=0x821312b0)
  throw std::runtime_error("Unexpected original Forge lifecycle event name");
 (*editorEventSink)(std::string(reinterpret_cast<const char*>(base+ctx.r3.u32)));
 // The constructor and selection caller do not consume the event handle.
 ctx.r3.u32=0;
}
void sub_82449B18(PPCContext& ctx,uint8_t*){
 ctx.r3.u32=(physicsTransition?physicsTransition->input.held:CurrentPhysicsSelection().held)?0:0xffffffff;
}
void sub_82260B58(PPCContext& ctx,uint8_t* base){
 if(sceneryContact){
  if(ctx.r3.u32!=65)throw std::runtime_error("Unexpected scenery response point query");
  StoreVector(base,ctx.r4.u32,sceneryContact->physicsPoint);return;
 }
 if(heldSelection){
  const auto point=heldSelection->world.objectPoint(ctx.r3.u32);
  for(unsigned i=0;i<3;++i){
   if(!std::isfinite(point[i]))throw std::runtime_error("Nonfinite held-selection point");
   real(base,ctx.r4.u32+i*4,point[i]);
  }
  return;
 }

 auto& transition=CurrentPhysicsTransition();
 if(ctx.r3.u32!=65)throw std::runtime_error("Unexpected H4 physics point datum");
 for(unsigned i=0;i<3;++i)real(base,ctx.r4.u32+i*4,transition.point[i]);
}
void sub_822ED938(PPCContext& ctx,uint8_t*){
 if(heldMagnet){
  if(ctx.r3.u32!=0)throw std::runtime_error("Unexpected magnet player");
  ctx.r3.u32=heldMagnet->localHolder;return;
 }
 if(heldSelection){
  if(ctx.r3.u32!=heldSelection->player)throw std::runtime_error("Unexpected selection player");
  ctx.r3.u32=heldSelection->world.localHolder;return;
 }

 auto& transition=CurrentPhysicsTransition();
 if(ctx.r3.u32!=0)throw std::runtime_error("Unexpected H4 physics holder");
 ctx.r3.u32=transition.input.localHolder;
}
void sub_8225EA20(PPCContext& ctx,uint8_t* base){
 if(heldUpdate){
  StoreVector(base,ctx.r4.u32,heldUpdate->world.objectReferencePoint(HeldWorldDatum(ctx.r3.u32)));
  return;
 }
 if(!heldSelection)throw std::runtime_error("Reference-vector query outside selection");
 const auto vector=heldSelection->world.objectReferenceVector(ctx.r3.u32);
 for(unsigned i=0;i<3;++i){
  if(!std::isfinite(vector[i]))throw std::runtime_error("Nonfinite held reference vector");
  real(base,ctx.r4.u32+i*4,vector[i]);
 }
}
void sub_82505DE8(PPCContext& ctx,uint8_t*){
 if(!heldSelection||ctx.r3.u32!=heldSelection->player||ctx.r4.u32!=0)
  throw std::runtime_error("Unexpected original selection focus query");
 ctx.r3.u32=heldSelection->world.focusObject(ctx.r3.u32);
}
void UpdatePhysicsBody(PPCContext& ctx,uint8_t* base,bool create){
 auto& transition=CurrentPhysicsTransition();
 if(ctx.r3.u32!=65||(create?(ctx.r4.u32!=1||ctx.r5.u32!=1):ctx.r4.u32!=0))
  throw std::runtime_error("Unexpected H4 body update arguments");
 auto updated=transition.update(REX_LOAD_U64(0xb5000+256),create);
 for(float v:updated.point)if(!std::isfinite(v))throw std::runtime_error("Nonfinite native physics point");
 REX_STORE_U64(0xb5000+256,updated.flags);
 word(base,0xb5000+240,updated.hasInstance?0:0xffffffff);
 transition.point=updated.point;
}
void sub_82388C68(PPCContext& ctx,uint8_t* base){UpdatePhysicsBody(ctx,base,true);}
void sub_82388A08(PPCContext& ctx,uint8_t* base){UpdatePhysicsBody(ctx,base,false);}

void sub_82469630(PPCContext& ctx,uint8_t*){ctx.r3.u32=CurrentPhysicsSelection().keyframed;}
void sub_8244A5F0(PPCContext& ctx,uint8_t*){ctx.r3.u32=CurrentPhysicsSelection().normalStateOverride;}
void sub_823C2020(PPCContext& ctx,uint8_t*){
 if(!heldUpdate&&!selectionRay)CurrentPhysicsSelection();
 ctx.r3.u32=0xc0000;
}
void sub_822B79A0(PPCContext& ctx,uint8_t* base){
 if(!selectionRay||ctx.r3.u32!=monitorIndex)throw std::runtime_error("Selection origin outside ray call");
 StoreVector(base,ctx.r4.u32,selectionRay->world.origin);
}
void sub_82268800(PPCContext& ctx,uint8_t* base){
 if(!selectionRay)throw std::runtime_error("Selection iterator outside ray call");
 const auto index=selectionRay->next;
 if(index==selectionRay->world.exclusions.size()){ctx.r3.u32=0;return;}
 // Caller consumes iterator0->node[-12] as a private object handle. The
 // projected unit's Seats count is0 because the native producer filtered it.
 const uint32_t node=0x1e0000+uint32_t(index)*16;
 word(base,node,uint32_t(index));word(base,ctx.r3.u32,node+12);
 ++selectionRay->next;ctx.r3.u32=1;
}
void sub_823C5C28(PPCContext& ctx,uint8_t*){
 if(!selectionRay)throw std::runtime_error("Discarded variant read outside selection ray");
 //8244C740 initializes this76-byte temporary with original823C1E28, reads
 // a variant record into it, then overwrites it with the ray result without
 // consuming any field or the return value.823C5C28 only writes that output.
 // Keep the initialized temporary: no live variant mutation is suppressed.
 ctx.r3.u32=0;
}
void sub_82417550(PPCContext& ctx,uint8_t* base){
 if(!selectionRay&&!obstructionRay)throw std::runtime_error("Collision query outside mapped ray call");
 const auto input=ctx.r3.u32,output=ctx.r4.u32;
 advanced_forge::SelectionRayRequest request;
 request.layer=REX_LOAD_U32(input);
 request.flags=(uint64_t(REX_LOAD_U32(input+4))<<32)|REX_LOAD_U32(input+8);
 for(unsigned i=0;i<3;++i){request.origin[i]=get(base,input+12+i*4);request.endpoint[i]=get(base,input+24+i*4);}
 const auto count=base[input+292];
 if(count>64||base[input+296]||base[input+297])throw std::runtime_error("Unexpected original ray metadata");
 for(unsigned i=0;i<count;++i){
  const auto index=REX_LOAD_U32(input+36+i*4);
  if(selectionRay){
   if(index>=selectionRay->world.exclusions.size())throw std::runtime_error("Invalid private ray exclusion");
   request.exclusions.push_back(selectionRay->world.exclusions[index]);
  }else request.exclusions.push_back(index);
 }
 const auto hit=selectionRay?selectionRay->world.query(request):(*obstructionRay)(request);
 if(!hit){ctx.r3.u32=0;return;}
 if(hit->category==4&&hit->datum==0xffffffff)throw std::runtime_error("Missing selection hit identity");
 if(!std::isfinite(hit->fraction)||hit->fraction<0||hit->fraction>1)
  throw std::runtime_error("Invalid mapped collision fraction");
 word(base,output,hit->category);real(base,output+4,hit->fraction);StoreVector(base,output+8,hit->point);
 word(base,output+40,hit->datum);ctx.r3.u32=1;
}

void sub_82271460(PPCContext& ctx,uint8_t*){
 if(!coordinateEdit)throw std::runtime_error("H4 object lookup outside coordinate edit");
 ctx.r3.u32=ctx.r3.u32==coordinateEdit->datum?1:0;
}
void sub_822714E0(PPCContext& ctx,uint8_t*){
 if(!coordinateEdit)throw std::runtime_error("H4 player lookup outside coordinate edit");
 ctx.r3.u32=ctx.r4.u32==0?1:0;
}
void sub_825812D0(PPCContext& ctx,uint8_t* base){
 if(!coordinateEdit||REX_LOAD_U16(ctx.r3.u32+0x108)!=0xd||REX_LOAD_U32(ctx.r3.u32)!=coordinateEdit->datum)
  throw std::runtime_error("Unexpected H4 coordinate event");
 for(unsigned i=0;i<9;++i)coordinateEdit->result.basis[i]=get(base,ctx.r3.u32+8+i*4);
 for(unsigned i=0;i<3;++i)coordinateEdit->result.position[i]=get(base,ctx.r3.u32+0x2c+i*4);
}
void sub_825827B0(PPCContext& ctx,uint8_t*){
 if(!visibleObjects)throw std::runtime_error("H4 marker renderer outside visibility update");
 visibleObjects->insert(VisibleDatum(ctx.r4.u32));
}
void sub_82582950(PPCContext& ctx,uint8_t*){
 if(!visibleObjects)throw std::runtime_error("H4 marker renderer outside visibility update");
 visibleObjects->erase(VisibleDatum(ctx.r4.u32));
}
void sub_821F2050(PPCContext& ctx,uint8_t* base){
 // Caller supplies the H3 nearby-object set. Never rank or snap in the adapter.
 if(!active)throw std::runtime_error("Nearby query outside scene");
 const size_t count=active->nearbyOrder?active->nearbyOrder->size():active->objects.size();
 if(count>ctx.r9.u32||count>64)throw std::runtime_error("Nearby scene exceeds original query capacity");
 std::set<uint32_t> seen;
 for(uint32_t i=0;i<count;++i){
  const auto index=active->nearbyOrder?(*active->nearbyOrder)[i]:i;
  if(index>=active->objects.size()||!seen.insert(index).second)
   throw std::runtime_error("Invalid native nearby-query index");
 }
 for(uint32_t i=0;i<count;++i)
  word(base,ctx.r8.u32+i*4,active->nearbyOrder?(*active->nearbyOrder)[i]:i);
 ctx.r3.u32=static_cast<uint32_t>(count);
}
void sub_82582610(PPCContext& ctx,uint8_t* base){
 const auto& markers=object(ctx.r3.u32).markers;
 if(markers.size()>32)throw std::runtime_error("H4 marker capacity exceeded");
 for(size_t i=0;i<markers.size();++i)std::memcpy(base+ctx.r4.u32+i*112,markers[i].data(),112);
 ctx.r3.u32=static_cast<uint32_t>(markers.size());
}
void sub_82582A68(PPCContext& ctx,uint8_t*){ctx.r3.u32=0x193;}
void sub_82937F50(PPCContext& ctx,uint8_t*){
 if(ctx.r4.u32!=0x193)throw std::runtime_error("Unexpected H4 candidate marker group");
 if(ctx.r3.u32==0xffffffff){ctx.r3.u32=0;return;}
 const auto& candidate=object(ctx.r3.u32);
 ctx.r3.u32=candidate.hasMagnetGroup.value_or(!candidate.markers.empty())?1:0;
}
void sub_8293A3B0(PPCContext& ctx,uint8_t* base){
 auto p=heldUpdate?heldUpdate->world.objectPhysicsPoint(HeldWorldDatum(ctx.r3.u32)):
                    object(ctx.r3.u32).position;
 for(unsigned i=0;i<3;++i)real(base,ctx.r4.u32+i*4,p[i]);
}
}
namespace advanced_forge {
struct Bridge::Impl {
 uint8_t* base=nullptr;
 uint32_t visibleHeld=0xffffffff,visibleTarget=0xffffffff;
 std::set<uint32_t> visible;
 ~Impl(){if(base)VirtualFree(base,0,MEM_RELEASE);}
 void commit(uint32_t a,size_t n){if(!VirtualAlloc(base+a,n,MEM_COMMIT,PAGE_READWRITE))throw std::runtime_error("H4 private guest commit failed");}
};
Bridge::Bridge(const std::string& imagePath,const std::string& configPath):impl_(std::make_unique<Impl>()){
 auto& m=*impl_;
 m.base=static_cast<uint8_t*>(VirtualAlloc(nullptr,0x100000000ull,MEM_RESERVE,PAGE_NOACCESS));
 if(!m.base)throw std::runtime_error("H4 private guest reservation failed");
 m.commit(0,0x200000);m.commit(0x82000000,0x2f40000);
 for(uint32_t a:{0x835b0000u,0x84050000u,0x84070000u,0x84200000u})m.commit(a,0x10000);
 auto base=m.base;
 std::ifstream image(imagePath,std::ios::binary),config(configPath,std::ios::binary);
 if(!image.read(reinterpret_cast<char*>(base+0x82000000),0x2f38000)||
    !config.read(reinterpret_cast<char*>(base+0x52000),0x58))throw std::runtime_error("Original Halo 4 inputs missing or short");
 // Original camera pitch function, extracted from the same H4 globals tag.
 // Relocate its TagDataReference into the private arena; never use a guessed curve.
 std::ifstream cameraSettings(std::filesystem::path(configPath).parent_path()/"camera-settings.bin",std::ios::binary);
 if(!cameraSettings.read(reinterpret_cast<char*>(base+0x190000),216)||cameraSettings.peek()!=std::char_traits<char>::eof())
  throw std::runtime_error("Original H4 camera settings missing or wrong size");
 std::ifstream cameraCurve(std::filesystem::path(configPath).parent_path()/"camera-pitch-function.bin",std::ios::binary);
 if(!cameraCurve.read(reinterpret_cast<char*>(base+0x190100),84)||cameraCurve.peek()!=std::char_traits<char>::eof())
  throw std::runtime_error("Original H4 camera pitch function missing or wrong size");
 word(base,0x50100,0x190000);word(base,0x190010,84);word(base,0x19001c,0x190100);
 if(REX_LOAD_U32(0x5201c)!=0x193)throw std::runtime_error("Incorrect H4 marker settings");
 word(base,0x10000,0x11000);word(base,0x1101c,0x20000);
 word(base,0x12150,0x40000);word(base,0x40044,0x41000);
 word(base,0x8405d340,0x50000);word(base,0x501ec,0x666f7267);word(base,0x501f8,0);
 word(base,0x8420ff20,0x60000);word(base,0x835b6a50,0x51000);
 word(base,0x9fff8,1);word(base,0x9fffc,0x666f7267);word(base,0x51004,0x52000);
 // Original map-settings initialization preserves authored camera obstruction
 // parameters and the source's per-field override semantics. The executable's
 // zero-filled runtime block is not the map's camera configuration.
 PPCContext cameraContext{};cameraContext.fpscr.loadFromHost();cameraContext.r1.u32=0x180000;
 h4_forge_original::sub_824BFE90(cameraContext,base);
 // These original startup constructors populate the obstruction query mask;
 // both source and destination words are zero in the unloaded image.
 h4_forge_original::sub_83292E30(cameraContext,base);
 h4_forge_original::sub_83292E50(cameraContext,base);
}
Bridge::~Bridge()=default;
float Bridge::MagnetQueryRadius(const HeldEditorState& state,
                               const std::array<float,3>& physicsPoint,float runtimeRadius){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||
    physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||
    heldMagnet||heldUpdate||sceneryContact||monitorContact)
  throw std::runtime_error("Reentrant original magnet query reference");
 if(!std::isfinite(runtimeRadius)||runtimeRadius<0)
  throw std::runtime_error("Invalid magnet query runtime radius");
 for(float value:physicsPoint)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite magnet query point");
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,reference=0x31000;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 if(REX_LOAD_U32(editor)==0xffffffff)
  throw std::runtime_error("Magnet query requires selected object");
 for(unsigned offset:{36u,56u,60u,64u})if(!std::isfinite(get(base,editor+offset)))
  throw std::runtime_error("Nonfinite original magnet reference state");
 Scene scene;Object held;held.position=physicsPoint;scene.objects.push_back(held);
 struct Scope{Scope(const Scene& s){active=&s;}~Scope(){active=nullptr;}} scope(scene);
 word(base,editor,0);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=reference;
 h4_forge_original::sub_824499A8(ctx,base);
 //82582250: fsubs Y/Z/X; fmuls Y; fmadds Z then X; fsqrts; fadds radius.
 const float y=float(double(physicsPoint[1])-get(base,reference+4));
 const float z=float(double(physicsPoint[2])-get(base,reference+8));
 const float x=float(double(physicsPoint[0])-get(base,reference));
 const float yy=float(double(y)*y);
 const float zy=float(std::fma(double(z),double(z),double(yy)));
 const float square=float(std::fma(double(x),double(x),double(zy)));
 const float distance=float(std::sqrt(double(square)));
 const float radius=float(double(runtimeRadius)+distance);
 if(!std::isfinite(radius))throw std::runtime_error("Nonfinite original magnet query radius");
 return radius;
}
std::vector<Marker> Bridge::BuildMarkers(const std::vector<MarkerDefinition>& definitions,
    const std::vector<std::array<float,13>>& nodes,
    const std::optional<std::vector<uint8_t>>& permutations,bool mirrored){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||
    physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||
    heldMagnet||heldUpdate||sceneryContact||monitorContact)
  throw std::runtime_error("Reentrant original marker construction");
 if(nodes.empty()||nodes.size()>256)
  throw std::runtime_error("Invalid original marker node/region data");
 for(const auto& node:nodes)for(float value:node)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite marker node matrix");
 for(const auto& marker:definitions){
  const int region=static_cast<int8_t>(marker[0]);
  if(marker[2]>=nodes.size()||region< -1||
     (permutations&&region>=0&&size_t(region)>=permutations->size()))
   throw std::runtime_error("Invalid original marker node/region reference");
 }
 // This temporary private arena is outside the persistent adapters below2MB.
 // Its size follows the source group, not the32-marker output cap: permutation
 // filtering can discard early records before the original output fills.
 constexpr uint32_t model=0x200000,group=model+0x100,records=model+0x200;
 const uint64_t nodeStart=uint64_t(records)+definitions.size()*48ULL;
 const uint64_t permutationStart=nodeStart+nodes.size()*52ULL;
 const uint64_t outputStart=(permutationStart+(permutations?permutations->size():0)+15)&~15ULL;
 const uint64_t arenaEnd=(outputStart+32*112+4095)&~4095ULL;
 if(definitions.size()>0x7fffffffULL||arenaEnd>=0x82000000ULL)
  throw std::runtime_error("Original marker group exceeds private address space");
 auto base=impl_->base;
 impl_->commit(model,size_t(arenaEnd-model));
 const auto oldTag=REX_LOAD_U32(0x51000+3*8+4);
 struct ArenaScope {
  uint8_t* base;size_t size;uint32_t oldTag;
  ~ArenaScope(){REX_STORE_U32(0x51000+3*8+4,oldTag);VirtualFree(base+0x200000,size,MEM_DECOMMIT);}
 } scope{base,size_t(arenaEnd-model),oldTag};
 word(base,0x51000+3*8+4,model);word(base,model+64,group);
 word(base,group+4,uint32_t(definitions.size()));word(base,group+8,records);
 for(size_t i=0;i<definitions.size();++i)
  std::memcpy(base+records+i*48,definitions[i].data(),48);
 for(size_t i=0;i<nodes.size();++i)for(unsigned j=0;j<13;++j)
  real(base,uint32_t(nodeStart+i*52+j*4),nodes[i][j]);
 if(permutations&&!permutations->empty())
  std::memcpy(base+permutationStart,permutations->data(),permutations->size());
 std::memset(base+outputStart,0,32*112);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=3;ctx.r4.u32=0;
 ctx.r5.u32=permutations?uint32_t(permutationStart):0;
 ctx.r6.u32=uint32_t(nodeStart);ctx.r7.u32=mirrored?1:0;
 ctx.r8.u32=uint32_t(outputStart);ctx.r9.u32=32;
 h4_forge_original::sub_8259E9A8(ctx,base);
 if(ctx.r3.s32<0||ctx.r3.u32>32)throw std::runtime_error("Invalid original marker output count");
 std::vector<Marker> result(ctx.r3.u32);
 for(size_t i=0;i<result.size();++i)
  std::memcpy(result[i].data(),base+outputStart+i*112,112);
 return result;
}
bool Bridge::CollisionGroupAllows(uint32_t queryInfo,uint32_t shapeInfo,
                                   const std::array<uint32_t,32>& lookup){
 // This leaf has no callbacks, TLS access or global writes. Use a private
 // frame so a native query callback can invoke it without disturbing its
 // enclosing original held-update call or guest stack.
 auto base=impl_->base;
 constexpr uint32_t filter=0x191000,result=0x191100;
 for(unsigned i=0;i<lookup.size();++i)word(base,filter+52+i*4,lookup[i]);
 base[result]=0;
 PPCContext ctx{};ctx.fpscr.loadFromHost();
 ctx.r3.u32=result;ctx.r4.u32=filter;
 ctx.r5.u32=queryInfo;ctx.r6.u32=shapeInfo;
 h4_forge_original::sub_82D813F8(ctx,base);
 return base[result]!=0;
}
SelectionRayResult Bridge::UpdateSelectionRay(HeldEditorState& state,const SelectionRayWorld& world){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||
    editorEventSink||heldSelection||manipulationInput||heldMagnet||heldUpdate||sceneryContact||!world.query||world.exclusions.size()>64)
  throw std::runtime_error("Invalid or reentrant H4 selection ray");
 for(const auto& vector:{world.origin,world.direction})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite H4 selection view");
 std::set<uint32_t> unique;
 for(auto datum:world.exclusions)
  if(datum==0xffffffff||!unique.insert(datum).second)throw std::runtime_error("Invalid H4 selection exclusion list");
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,result=0x31000;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 const auto held=REX_LOAD_U32(editor);
 if(!std::isfinite(get(base,editor+28)))throw std::runtime_error("Nonfinite held ray distance");
 word(base,editor,held==0xffffffff?0xffffffff:65);
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,0xb3000);
 word(base,0xb3000+36,monitorIndex);word(base,0x41000+monitorIndex*16+12,0xb4000);
 StoreVector(base,0xb4000+1260,world.direction);
 word(base,0x41000+65*16+12,0xb5000);
 REX_STORE_U16(0xb5000+62,static_cast<uint16_t>(world.heldVariantSlot));
 // Private compact handles are translated back at the collision boundary.
 // Only the source-read tag/Seats fields are projected; no H3 layout escapes.
 word(base,0x51000+3*8+4,0x1a9000);word(base,0x1a9000+1364,0);
 for(uint32_t i=0;i<world.exclusions.size();++i){
  const auto object=0x1b0000+i*0x800;
  word(base,0x41000+i*16+12,object);word(base,object+8,3);
 }
 word(base,result,0xffffffff);
 SelectionRayCall call{world};
 struct Scope {
  explicit Scope(SelectionRayCall& call){selectionRay=&call;}
  ~Scope(){selectionRay=nullptr;}
 } scope(call);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=result;
 h4_forge_original::sub_8244C740(ctx,base);
 word(base,editor,held);
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
 return {bool(ctx.r3.u32&255),REX_LOAD_U32(result)};
}

std::array<float,13> Bridge::PrepareActiveBipedTarget(const std::array<float,13>& pose,
                                                       std::array<float,3>& facing){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||
    physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||heldMagnet||heldUpdate||sceneryContact)
  throw std::runtime_error("Reentrant active biped target preparation");
 auto base=impl_->base;
 constexpr uint32_t target=0x31000;
 for(unsigned i=0;i<13;++i){
  if(!std::isfinite(pose[i]))throw std::runtime_error("Nonfinite biped controller pose");
  real(base,target+i*4,pose[i]);
 }
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=target+4;
 h4_forge_original::sub_8257FB98(ctx,base);
 std::array<float,3> nextFacing;
 for(unsigned i=0;i<3;++i){
  nextFacing[i]=get(base,target+4+i*4);
  if(!std::isfinite(nextFacing[i]))throw std::runtime_error("Nonfinite original biped facing");
 }
 auto result=pose;
 //82452A6C..82452A8C copies the original nine-float identity basis,
 // preserving the requested scale and translation for the controller.
 for(unsigned i=0;i<9;++i)result[1+i]=get(base,0x82125148+i*4);
 facing=nextFacing;
 return result;
}

std::array<float,3> Bridge::ConvertMonitorView(const std::array<float,3>& forward,
                                               const std::array<float,3>& up){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||
    physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||heldMagnet||heldUpdate||sceneryContact)
  throw std::runtime_error("Reentrant monitor view conversion");
 for(const auto& vector:{forward,up})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite monitor view basis");
 auto base=impl_->base;
 constexpr uint32_t forwardAddress=0x31000,upAddress=0x31010,viewStorage=0x32000;
 const auto tls=REX_LOAD_U32(0x10000);
 const auto priorView=REX_LOAD_U32(tls+100);
 MonitorViewCall call;
 struct Scope {
  uint8_t* base;uint32_t slot,previous;
  Scope(uint8_t* b,uint32_t s,uint32_t p,MonitorViewCall& c):base(b),slot(s),previous(p){monitorView=&c;}
  ~Scope(){word(base,slot,previous);monitorView=nullptr;}
 } scope(base,tls+100,priorView,call);
 word(base,tls+100,viewStorage);
 StoreVector(base,forwardAddress,forward);StoreVector(base,upAddress,up);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=forwardAddress;ctx.r5.u32=upAddress;
 h4_forge_original::sub_823FC348(ctx,base);
 if(!call.notified)throw std::runtime_error("Missing original monitor view notification");
 return call.angles;
}

void Bridge::UpdateMonitorObstruction(HeldEditorState& state,uint32_t monitor,float tickInterval,
             const std::array<float,3>& target,const std::array<float,3>& origin,
             const std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)>& query){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||
    editorEventSink||heldSelection||manipulationInput||heldMagnet||heldUpdate||sceneryContact||!query||monitor==0xffffffff)
  throw std::runtime_error("Invalid or reentrant monitor obstruction stage");
 if(!std::isfinite(tickInterval)||tickInterval<0)
  throw std::runtime_error("Invalid monitor obstruction timestep");
 for(const auto& vector:{target,origin})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite monitor obstruction point");
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,targetAddress=0x31000,originAddress=0x31010;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 const auto held=REX_LOAD_U32(editor);
 if(held==0xffffffff)throw std::runtime_error("Monitor obstruction without a held object");
 for(unsigned i=0;i<6;++i)
  if(!std::isfinite(get(base,editor+228+i*4)))throw std::runtime_error("Nonfinite monitor obstruction state");
 //8244AF48 writes the two exclusions immediately before824F5CF0. Their
 // identities remain native because this substage never dereferences them.
 word(base,editor+256,held);word(base,editor+260,monitor);
 StoreVector(base,targetAddress,target);StoreVector(base,originAddress,origin);
 struct Scope {
  explicit Scope(const std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)>& query){obstructionRay=&query;}
  ~Scope(){obstructionRay=nullptr;}
 } scope(query);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r4.u32=0x8407f34c;ctx.r5.u32=editor+228;
 ctx.r6.u32=targetAddress;ctx.r7.u32=originAddress;ctx.f1.f64=tickInterval;
 h4_forge_original::sub_824F5CF0(ctx,base);
 std::memcpy(state.bytes.data()+228,base+editor+228,36);
}

uint64_t Bridge::ControlBody(const std::array<float,13>& pose,float parameter,
                             const ControlledBody& body){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||
    heldSelection||manipulationInput||heldMagnet||heldUpdate||sceneryContact||controlledBody)
  throw std::runtime_error("Reentrant original body controller");
 if(!std::isfinite(parameter)||parameter<=0||!std::isfinite(body.angularResponseLimit)||body.angularResponseLimit<0||!body.activate||!body.relocate||
    !body.setLinearVelocity||!body.setAngularVelocity)
  throw std::runtime_error("Incomplete native body controller mapping");
 for(float value:pose)if(!std::isfinite(value))throw std::runtime_error("Nonfinite controller target");
 for(const auto& vector:{body.position,body.orientation,body.linearVelocity,body.angularVelocity})
  for(float value:vector)if(!std::isfinite(value))throw std::runtime_error("Nonfinite controller snapshot");
 auto base=impl_->base;
 constexpr uint32_t instance=0x151000,entries=0x151100,owner=0x151200,target=0x151500,table=0x151600;
 constexpr uint32_t header=0x41000+65*16;
 const auto previous=REX_LOAD_U32(header+12);
 struct Scope{uint8_t* base;uint32_t header,previous;
  ~Scope(){word(base,header+12,previous);controlledBody=nullptr;}
 } scope{base,header,previous};
 std::memset(base+controlledBodyAddress,0,0x400);
 std::memset(base+instance,0,0x700);
 word(base,header+12,owner);word(base,instance+20,65);word(base,instance+48,entries);
 word(base,entries+52,controlledBodyAddress);word(base,controlledBodyAddress+224,table);
 word(base,table+64,0x100);word(base,table+68,0x104);
 real(base,table+80,body.angularResponseLimit);
 for(unsigned i=0;i<4;++i){
  real(base,controlledBodyAddress+288+i*4,body.position[i]);
  real(base,controlledBodyAddress+352+i*4,body.orientation[i]);
  real(base,controlledBodyAddress+432+i*4,body.linearVelocity[i]);
  real(base,controlledBodyAddress+448+i*4,body.angularVelocity[i]);
 }
 for(unsigned i=0;i<13;++i)real(base,target+i*4,pose[i]);
 controlledBody=&body;
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 // Original H4 motion constructor82CD3140 encodes incoming f3 here.
 // H3 constructor8265F4F0 retains the corresponding value as a float.
 ctx.r3.u32=controlledBodyAddress+411;ctx.r4.u32=table+80;
 h4_forge_original::sub_82C969B0(ctx,base);
 ctx.r3.u32=instance;ctx.r4.u32=0;ctx.r5.u32=target;ctx.f1.f64=parameter;
 h4_forge_original::sub_8249B418(ctx,base);
 return REX_LOAD_U64(owner+256);
}
std::array<float,13> Bridge::CompensateAttachmentPose(const std::array<float,13>& root,
                const std::array<float,13>& node,const std::array<float,3>& linear,
                const std::array<float,3>& angular,float tickInterval){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||
    coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||
    manipulationInput||sceneryContact||heldUpdate)
  throw std::runtime_error("Reentrant H4 attachment compensation");
 if(!std::isfinite(tickInterval)||tickInterval<0)
  throw std::runtime_error("Invalid attachment tick interval");
 for(const auto& pose:{root,node})for(float value:pose)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite attachment pose");
 for(const auto& vector:{linear,angular})for(float value:vector)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite attachment velocity");
 auto base=impl_->base;
 constexpr uint32_t rootAddress=0x1f0000,nodeAddress=0x1f0040,axis=0x1f0080;
 constexpr uint32_t rotation=0x1f0100,previousRoot=0x1f0140,inverse=0x1f0180;
 constexpr uint32_t relative=0x1f01c0,output=0x1f0200;
 for(unsigned i=0;i<13;++i){real(base,rootAddress+i*4,root[i]);real(base,nodeAddress+i*4,node[i]);}
 StoreVector(base,axis,angular);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 // Exact helper order from82939248,829393EC..82939500 branch. Normalize
 // angular velocity, form its reverse-tick rotation, and retain root scale.
 ctx.r3.u32=axis;h4_forge_original::sub_8228ACE8(ctx,base);
 const float reverseTick=-tickInterval,angle=float(ctx.f1.f64)*reverseTick;
 ctx.f1.f64=angle;h4_forge_original::sub_82265C30(ctx,base);
 const float sine=float(ctx.f1.f64);
 ctx.f1.f64=angle;h4_forge_original::sub_82265E28(ctx,base);
 const float cosine=float(ctx.f1.f64);
 ctx.r3.u32=rotation;ctx.r4.u32=axis;ctx.f1.f64=sine;ctx.f2.f64=cosine;
 h4_forge_original::sub_82300D40(ctx,base);
 real(base,previousRoot,root[0]);
 ctx.r3.u32=rotation;ctx.r4.u32=rootAddress+4;ctx.r5.u32=previousRoot+4;
 h4_forge_original::sub_821E0550(ctx,base);
 for(unsigned i=0;i<3;++i)real(base,previousRoot+40+i*4,std::fma(linear[i],reverseTick,root[10+i]));
 ctx.r3.u32=rootAddress;ctx.r4.u32=inverse;
 h4_forge_original::sub_822864E0(ctx,base);
 ctx.r3.u32=inverse;ctx.r4.u32=nodeAddress;ctx.r5.u32=relative;
 h4_forge_original::sub_8226BFC0(ctx,base);
 ctx.r3.u32=previousRoot;ctx.r4.u32=relative;ctx.r5.u32=output;
 h4_forge_original::sub_8226BFC0(ctx,base);
 std::array<float,13> result;
 for(unsigned i=0;i<13;++i)result[i]=get(base,output+i*4);
 return result;
}
HeldEditorState Bridge::InitializeHeldEditorState(const std::array<uint8_t,336>& storage,
                                                   const std::function<void(const std::string&)>& eventSink){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||!eventSink)
  throw std::runtime_error("Invalid or reentrant H4 editor initialization");
 auto base=impl_->base;constexpr uint32_t editor=0x21aec;
 std::memcpy(base+editor,storage.data(),storage.size());
 struct Scope {
  explicit Scope(const std::function<void(const std::string&)>& sink){editorEventSink=&sink;}
  ~Scope(){editorEventSink=nullptr;}
 } scope(eventSink);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=editor;
 h4_forge_original::sub_82449DD8(ctx,base);
 std::array<uint8_t,336> initialized;
 std::memcpy(initialized.data(),base+editor,initialized.size());
 return HeldEditorState(initialized);
}
std::vector<uint32_t> Bridge::SelectHeldObject(HeldEditorState& state,uint32_t player,
                                              uint32_t datum,const HeldSelectionWorld& world){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||
    player==0xffffffff||(player&65535)>=16||!world.objectPoint||!world.objectReferenceVector||!world.focusObject||!world.eventSink)
  throw std::runtime_error("Invalid or reentrant H4 held selection");
 auto base=impl_->base;
 const auto editor=0x21aec+(player&65535)*336;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 HeldSelectionCall selection{player,world};
 std::set<uint32_t> visible(state.visibleObjects.begin(),state.visibleObjects.end());
 struct Scope {
  Scope(const HeldSelectionCall& selection,std::set<uint32_t>& visible){
   heldSelection=&selection;visibleObjects=&visible;editorEventSink=&selection.world.eventSink;
  }
  ~Scope(){heldSelection=nullptr;visibleObjects=nullptr;editorEventSink=nullptr;}
 } scope(selection,visible);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=editor;ctx.r4.u32=player;ctx.r5.u32=datum;
 h4_forge_original::sub_82449ED8(ctx,base);
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
 state.visibleObjects.assign(visible.begin(),visible.end());
 return state.visibleObjects;
}
bool Bridge::NotifyObjectDeleted(HeldEditorState& state,uint32_t player,
                                  uint32_t datum,const HeldSelectionWorld& world){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||
    player==0xffffffff||(player&65535)>=16||datum==0xffffffff||
    !world.objectPoint||!world.objectReferenceVector||!world.focusObject||!world.eventSink)
  throw std::runtime_error("Invalid or reentrant H4 object deletion");
 auto base=impl_->base;
 const auto editor=0x21aec+(player&65535)*336;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 HeldSelectionCall selection{player,world};
 std::set<uint32_t> visible(state.visibleObjects.begin(),state.visibleObjects.end());
 struct Scope {
  Scope(const HeldSelectionCall& selection,std::set<uint32_t>& visible){
   heldSelection=&selection;visibleObjects=&visible;editorEventSink=&selection.world.eventSink;
  }
  ~Scope(){heldSelection=nullptr;visibleObjects=nullptr;editorEventSink=nullptr;}
 } scope(selection,visible);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 // Exact per-editor branch order in8244C000. Native H3 retains engine-wide
 // notifications and deferred removal; H4 notification822FF770 is not emitted here.
 if(REX_LOAD_U32(editor+24)==datum)word(base,editor+24,0xffffffff);
 const bool selected=REX_LOAD_U32(editor)==datum;
 if(selected){
  ctx.r3.u32=editor;ctx.r4.u32=player;ctx.r5.u32=0xffffffff;
  h4_forge_original::sub_82449ED8(ctx,base);
 }
 if(REX_LOAD_U32(editor+4)==datum){
  ctx.r3.u32=editor;ctx.r4.u32=player;ctx.r5.u32=0xffffffff;
  h4_forge_original::sub_8244A118(ctx,base);
 }
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
 state.visibleObjects.assign(visible.begin(),visible.end());
 return selected;
}

bool Bridge::InitializeGrabPlacement(HeldEditorState& editor,const GrabPlacement& input){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection)
  throw std::runtime_error("Reentrant H4 grab initialization");
 auto read=[&](size_t offset){uint32_t value;std::memcpy(&value,editor.bytes.data()+offset,4);return std::byteswap(value);};
 if(input.datum==0xffffffff||read(0)!=input.datum)
  throw std::runtime_error("Grab placement disagrees with original held selection");
 // Original82451048 branches directly to8245119C for a bodyless instance.
 if(!input.hasBodies)return false;
 for(const auto& vector:{input.heldPoint,input.monitorPoint,input.monitorForward})
  for(float value:vector)if(!std::isfinite(value))throw std::runtime_error("Nonfinite grab world input");
 const auto pose=ConstrainGrabPose(input.pose,input.variantBounds);
 std::array<float,3> delta;
 for(unsigned i=0;i<3;++i){
  const auto cached=std::bit_cast<float>(read(44+i*4));
  if(!std::isfinite(cached))throw std::runtime_error("Nonfinite original grab reference point");
  // Original fsubs rounds each component before the projection.
  delta[i]=float(double(cached)-double(input.monitorPoint[i]));
 }
 // Original824510B8..824510F8: Y product, Z fused add, then X fused add.
 // Keep the generated original's double intermediates and single rounding.
 const float y=float(double(input.monitorForward[1])*double(delta[1]));
 const float yz=float(std::fma(double(input.monitorForward[2]),double(delta[2]),double(y)));
 const float projected=float(std::fma(double(input.monitorForward[0]),double(delta[0]),double(yz)));
 const float distance=ConstrainHeldDistance(projected,input.radius,input.inputActive,input.distanceInput,true);
 // Commit only the fields written by this stage. Keep compensated offset,
 // preferences, prior selection and all other336-byte editor state intact.
 auto next=editor.bytes;
 auto write=[&](size_t offset,float value){const auto word=std::byteswap(std::bit_cast<uint32_t>(value));std::memcpy(next.data()+offset,&word,4);};
 for(unsigned i=0;i<pose.size();++i)write(84+i*4,pose[i]);
 write(28,distance);
 for(unsigned i=0;i<3;++i)write(68+i*4,input.heldPoint[i]);
 editor.bytes=next;
 return true;
}

SpawnPlacement Bridge::PrepareSpawnPlacement(const std::array<float,3>& point,
                const std::optional<std::array<float,3>>& monitorPoint,float definitionRadius){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||
    coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||
    manipulationInput||sceneryContact||heldUpdate||heldMagnet)
  throw std::runtime_error("Reentrant H4 spawn placement");
 for(float value:point)if(!std::isfinite(value))throw std::runtime_error("Nonfinite spawn point");
 if(!std::isfinite(definitionRadius))throw std::runtime_error("Nonfinite spawn radius");
 auto base=impl_->base;
 SpawnPlacement result{point,definitionRadius};
 // Original8244EFEC..8244F000 uses definition radius, not native model radius.
 if(result.radius<get(base,0x82128a54))result.radius=get(base,0x821289e4);
 if(!monitorPoint)return result; // Original focus lookup returned invalid.
 constexpr uint32_t direction=0x1f0240;
 for(unsigned i=0;i<3;++i){
  if(!std::isfinite((*monitorPoint)[i]))throw std::runtime_error("Nonfinite spawn monitor point");
  real(base,direction+i*4,float(double((*monitorPoint)[i])-double(point[i])));
 }
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=direction;h4_forge_original::sub_8228ACE8(ctx,base);
 const float separation=float(ctx.f1.f64);
 // Preserve the original comparison and single rounding per multiply/add.
 const float offset=result.radius<separation?result.radius:
                    float(double(separation)*double(get(base,0x82128a08)));
 for(unsigned i=0;i<3;++i){
  const float delta=float(double(get(base,direction+i*4))*double(offset));
  result.point[i]=float(double(point[i])+double(delta));
  if(!std::isfinite(result.point[i]))throw std::runtime_error("Nonfinite adjusted spawn point");
 }
 return result;
}

std::array<float,13> Bridge::ConstrainGrabPose(const std::array<float,13>& pose,
                                                const std::array<float,6>& bounds){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection)
  throw std::runtime_error("Reentrant H4 grab-pose constraint");
 for(float value:pose)if(!std::isfinite(value))throw std::runtime_error("Nonfinite H4 grab pose");
 for(float value:bounds)if(!std::isfinite(value))throw std::runtime_error("Nonfinite H4 variant bounds");
 for(unsigned i=0;i<3;++i)if(bounds[i*2]>bounds[i*2+1])
  throw std::runtime_error("Inverted H4 variant bounds");
 auto base=impl_->base;
 constexpr uint32_t nativeBounds=0xb7000,point=0xb7040;
 for(unsigned i=0;i<6;++i)real(base,nativeBounds+i*4,bounds[i]);
 for(unsigned i=0;i<3;++i)real(base,point+i*4,pose[10+i]);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=nativeBounds;ctx.r4.u32=point;ctx.r5.u32=point;
 h4_forge_original::sub_82282580(ctx,base);
 auto result=pose;
 for(unsigned i=0;i<3;++i)result[10+i]=get(base,point+i*4);
 return result;
}

std::array<float,13> Bridge::ApplyHeldCoordinatePose(HeldEditorState& editor,uint32_t datum,
                                                       const std::array<float,13>& pose,
                                                       const std::array<float,6>& bounds){
 uint32_t selected;
 std::memcpy(&selected,editor.bytes.data(),sizeof(selected));
 if(datum==0xffffffff||std::byteswap(selected)!=datum)
  throw std::runtime_error("H4 coordinate event does not own selected object");
 // 824503C4..82450428 copies packet+4 to editor+84 (52 bytes), then
 // constrains editor+124. No distance, grab offset, input, or snap reset.
 // Constrain first so a rejected host request leaves the editor untouched.
 const auto constrained=ConstrainGrabPose(pose,bounds);
 for(unsigned i=0;i<constrained.size();++i){
  const auto word=std::byteswap(std::bit_cast<uint32_t>(constrained[i]));
  std::memcpy(editor.bytes.data()+84+i*4,&word,sizeof(word));
 }
 return constrained;
}

ManipulationInputResult Bridge::ConsumeManipulationInput(const ManipulationInputState& prior,
                                                             const ManipulationInput& input){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput)
  throw std::runtime_error("Reentrant H4 manipulation input");
 for(float value:{prior.distance,prior.roll,prior.yaw,prior.pitch,input.trigger,
                  input.movement[0],input.movement[1],input.look[0],input.look[1]})
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite manipulation input");
 auto base=impl_->base;
 constexpr uint32_t player=0xb3000,packet=0xb8000;
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,player);
 base[player+1888]=prior.active?1:0;
 real(base,player+1892,prior.distance);real(base,player+1896,prior.roll);
 real(base,player+1900,prior.yaw);real(base,player+1904,prior.pitch);
 // Only these packet fields are read/written by original82368CE0.
 real(base,packet+28,input.movement[0]);real(base,packet+32,input.movement[1]);
 base[packet+40]=input.rotationAvailable?1:0;
 real(base,packet+44,input.look[0]);real(base,packet+48,input.look[1]);
 real(base,packet+56,input.trigger);
 struct Scope {
  explicit Scope(const ManipulationInput& input){manipulationInput=&input;}
  ~Scope(){manipulationInput=nullptr;}
 } scope(input);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=packet;
 h4_forge_original::sub_82368CE0(ctx,base);
 ManipulationInputResult result;
 result.state={base[player+1888]!=0,get(base,player+1892),get(base,player+1896),
               get(base,player+1900),get(base,player+1904)};
 result.remainingMovement={get(base,packet+28),get(base,packet+32)};
 return result;
}

void Bridge::RotateHeld(HeldEditorState& state,const ManipulationInputState& input,
                         const std::array<float,3>& viewDirection,float tickInterval,
                         const RotationPhysics& physics){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput)
  throw std::runtime_error("Reentrant H4 held rotation");
 if(physics.objectType>=32||physics.bodyMotion.size()>64||(!physics.hasInstance&&!physics.bodyMotion.empty())||
    !std::isfinite(tickInterval)||tickInterval<0)
  throw std::runtime_error("Invalid H4 rotation world");
 for(float value:{input.roll,input.yaw,input.pitch,viewDirection[0],viewDirection[1],viewDirection[2]})
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite H4 rotation input");
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,object=0xb5000,player=0xb3000,monitor=0xb4000;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 const auto nativeHeld=REX_LOAD_U32(editor);
 // Only the private query datum is remapped. Restore the native datum before
 // returning persistent editor storage to its owner.
 word(base,editor,nativeHeld==0xffffffff?0xffffffff:65);
 word(base,0x41000+65*16+12,object);
 base[object+178]=physics.objectType;
 REX_STORE_U64(object+256,physics.objectFlags);
 word(base,object+240,physics.hasInstance?0:0xffffffff);
 word(base,0x83625160,0xc4000);word(base,0xc4000+68,0xc5000);
 word(base,0xc5000+16,physics.instanceFlags);
 word(base,0xc5000+48,0xd0000);word(base,0xc5000+52,uint32_t(physics.bodyMotion.size()));
 for(unsigned i=0;i<physics.bodyMotion.size();++i){
  const uint32_t body=0xe0000+i*256;
  word(base,0xd0000+i*60+52,body);base[body+232]=physics.bodyMotion[i];
 }
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,player);
 word(base,player+36,monitorIndex);word(base,0x41000+monitorIndex*16+12,monitor);
 base[player+1888]=input.active?1:0;
 real(base,player+1896,input.roll);real(base,player+1900,input.yaw);real(base,player+1904,input.pitch);
 for(unsigned i=0;i<3;++i)real(base,monitor+1260+i*4,viewDirection[i]);
 word(base,0x11000+88,0xc6100);real(base,0xc6100+8,tickInterval);
 word(base,0xc6000,0);word(base,0xc6004,editor);
 // Original force-decay global8407EFFB retains its zero-initialized state;
 // no fabricated host override or debug control is introduced here.
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=0xc6000;
 h4_forge_original::sub_8244A7D0(ctx,base);
 word(base,editor,nativeHeld);
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
}

void Bridge::AdvanceHeldPlacement(HeldEditorState& editor,
                                   const ManipulationInputState& input,float radius){
 auto read=[&](size_t offset){uint32_t word;std::memcpy(&word,editor.bytes.data()+offset,4);return std::byteswap(word);};
 if(read(0)==0xffffffff)throw std::runtime_error("Held placement has no original selection");
 const float scale=std::bit_cast<float>(read(36)),decay=std::bit_cast<float>(read(40));
 const float distance=std::bit_cast<float>(read(28));
 if(!std::isfinite(scale)||!std::isfinite(decay)||!std::isfinite(distance))
  throw std::runtime_error("Nonfinite original held placement state");
 // Original fsubs rounds before fsel. Preserve negative zero's selected
 // branch; source image821289E0 supplies the fallback positive zero.
 const float remaining=float(double(scale)-double(decay));
 const float nextScale=remaining>=0.f?remaining:get(impl_->base,0x821289e0);
 const auto nextDistance=ConstrainHeldDistance(distance,radius,input.active,input.distance,true);
 auto write=[&](size_t offset,float value){const auto word=std::byteswap(std::bit_cast<uint32_t>(value));std::memcpy(editor.bytes.data()+offset,&word,4);};
 write(36,nextScale);write(28,nextDistance);
}

float Bridge::ConstrainHeldDistance(float distance,float radius,bool inputActive,
                                    float distanceInput,bool hasHeldObject){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsTransition||editorEventSink)throw std::runtime_error("Reentrant H4 distance update");
 if(!std::isfinite(distance)||!std::isfinite(radius)||radius<0||!std::isfinite(distanceInput))
  throw std::runtime_error("Invalid H4 distance inputs");
 auto base=impl_->base;
 // Standalone radius query uses object65; the monitor has its own index.
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,0xb3000);
 base[0xb3000+1888]=inputActive?1:0;real(base,0xb3000+1892,distanceInput);
 word(base,0x41000+65*16+12,0xb5000);real(base,0xb5000+76,radius);
 real(base,0xb6000,distance);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=hasHeldObject?65:0xffffffff;ctx.r5.u32=0xb6000;
 h4_forge_original::sub_82452738(ctx,base);
 return get(base,0xb6000);
}

uint32_t Bridge::SelectPhysicsState(PhysicsMode mode,bool held,bool keyframed,
                                    bool normalStateOverride,bool variantObject){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink)
  throw std::runtime_error("Reentrant H4 physics selection");
 if(mode!=PhysicsMode::Normal&&mode!=PhysicsMode::Fixed&&mode!=PhysicsMode::Phased)
  throw std::runtime_error("Invalid H4 physics selection mode");
 auto base=impl_->base;
 word(base,0x41000+65*16+12,0xb5000);
 REX_STORE_U16(0xb5000+62,variantObject?0:0xffff);
 REX_STORE_U16(0xc0000+5356+62,static_cast<uint16_t>(mode));
 PhysicsSelection selection{held,keyframed,normalStateOverride};
 struct Scope{explicit Scope(const PhysicsSelection& s){physicsSelection=&s;}~Scope(){physicsSelection=nullptr;}} scope(selection);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=65;
 h4_forge_original::sub_8244A180(ctx,base);
 return ctx.r3.u32;
}
PhysicsTransition Bridge::TransitionPhysics(const PhysicsTransition& current,
                                            const PhysicsBodyAdapter& updateBody){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink)
  throw std::runtime_error("Reentrant H4 physics transition");
 if(current.state>3||!updateBody||!std::isfinite(current.offsetScale)||!std::isfinite(current.offsetDecay))
  throw std::runtime_error("Invalid H4 physics transition");
 for(float v:current.point)if(!std::isfinite(v))throw std::runtime_error("Nonfinite physics point");
 for(float v:current.grabOffset)if(!std::isfinite(v))throw std::runtime_error("Nonfinite grab offset");
 auto base=impl_->base;
 constexpr uint32_t objectAddress=0xb5000,editor=0x21aec;
 word(base,0x41000+65*16+12,objectAddress);
 // Keep tag0 (Forge globals) intact. Private object/model references use1/2/3.
 word(base,objectAddress+8,1);word(base,0x51000+1*8+4,0xc2000);
 word(base,0xc2000+148,current.hasPhysicsModel?2:0xffffffff);
 word(base,0x51000+2*8+4,0xc2200);word(base,0xc2200+60,3);
 word(base,objectAddress+240,current.hasInstance?0:0xffffffff);
 REX_STORE_U64(objectAddress+256,current.flags);
 real(base,editor+36,current.offsetScale);real(base,editor+40,current.offsetDecay);
 for(unsigned i=0;i<3;++i)real(base,editor+56+i*4,current.grabOffset[i]);
 PhysicsTransitionCall transition{current,updateBody,current.point};
 struct Scope {
  explicit Scope(PhysicsTransitionCall& t){physicsTransition=&t;}
  ~Scope(){physicsTransition=nullptr;}
 } scope(transition);
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=65;ctx.r4.u32=current.state;
 h4_forge_original::sub_8244A2A0(ctx,base);
 auto result=current;result.flags=REX_LOAD_U64(objectAddress+256);result.point=transition.point;
 result.hasInstance=REX_LOAD_U32(objectAddress+240)!=0xffffffff;
 result.offsetScale=get(base,editor+36);result.offsetDecay=get(base,editor+40);
 for(unsigned i=0;i<3;++i)result.grabOffset[i]=get(base,editor+56+i*4);
 return result;
}
PhysicsTransition Bridge::TransitionHeldPhysics(HeldEditorState& editor,
                                                PhysicsTransition current,
                                                const PhysicsBodyAdapter& updateBody){
 auto read=[&](size_t offset){uint32_t v;std::memcpy(&v,editor.bytes.data()+offset,4);return std::byteswap(v);};
 if((read(0)!=0xffffffff)!=current.held)
  throw std::runtime_error("Original held state disagrees with native physics holder");
 current.offsetScale=std::bit_cast<float>(read(36));
 current.offsetDecay=std::bit_cast<float>(read(40));
 for(unsigned i=0;i<3;++i)current.grabOffset[i]=std::bit_cast<float>(read(56+i*4));
 auto result=TransitionPhysics(current,updateBody);
 auto write=[&](size_t offset,float value){const auto v=std::byteswap(std::bit_cast<uint32_t>(value));std::memcpy(editor.bytes.data()+offset,&v,4);};
 // Original8244A2A0 changes only these editor fields. In particular, do not
 // overwrite editor84's persistent unsnapped transform with a snapped pose.
 write(36,result.offsetScale);write(40,result.offsetDecay);
 for(unsigned i=0;i<3;++i)write(56+i*4,result.grabOffset[i]);
 return result;
}
uint16_t Bridge::EditPhysics(uint16_t editorProperties,PhysicsMode mode){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsTransition||editorEventSink)throw std::runtime_error("Reentrant physics edit");
 if(mode!=PhysicsMode::Normal&&mode!=PhysicsMode::Fixed&&mode!=PhysicsMode::Phased)
  throw std::runtime_error("Invalid Halo 4 physics mode");
 auto base=impl_->base;constexpr uint32_t editor=0xb1200,properties=0xb1240;
 // The menu supplies a property pointer and mask at +0x10/+0x14. This
 // address space is private H4 memory, with no access to live H3 objects.
 word(base,editor+0x10,properties);
 REX_STORE_U16(editor+0x14,0xc0);
 REX_STORE_U16(properties,editorProperties);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=editor;ctx.r4.u32=static_cast<uint16_t>(mode);
 h4_forge_original::sub_8268C340(ctx,base);
 return REX_LOAD_U16(properties);
}
std::array<float,3> Bridge::CoordinateAngles(const CoordinatePose& pose){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsTransition||editorEventSink)throw std::runtime_error("Reentrant coordinate read");
 auto base=impl_->base;
 for(unsigned i=0;i<9;++i)real(base,0xb1000+i*4,pose.basis[i]);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0xb1100;ctx.r4.u32=0xb1000;ctx.r5.u32=0xb1018;
 h4_forge_original::sub_8232F960(ctx,base);
 std::array<float,3> angles;
 for(unsigned i=0;i<3;++i)angles[i]=get(base,0xb1100+i*4)*get(base,0x82128b50);
 return angles;
}
std::array<CoordinateRange,2> Bridge::CoordinateRanges(){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsTransition||editorEventSink)throw std::runtime_error("Reentrant coordinate range read");
 auto base=impl_->base;constexpr uint32_t editor=0xb0000;
 std::memset(base+editor,0,0x200);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=editor;
 h4_forge_original::sub_8268AE80(ctx,base);
 return {{{get(base,editor+0xb4),get(base,editor+0xb8),get(base,editor+0xc0)},
          {get(base,editor+0xc8),get(base,editor+0xcc),get(base,editor+0xd4)}}};
}
CoordinatePose Bridge::EditCoordinates(uint32_t datum,const CoordinatePose& current,
                                      std::array<float,3> position,std::array<float,3> angles){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsTransition||editorEventSink||datum==0xffffffff)throw std::runtime_error("Invalid or reentrant coordinate edit");
 for(float v:position)if(!std::isfinite(v))throw std::runtime_error("Nonfinite coordinate input");
 for(float v:angles)if(!std::isfinite(v))throw std::runtime_error("Nonfinite angle input");
 auto base=impl_->base;constexpr uint32_t editor=0xb0000;
 std::memset(base+editor,0,0x200);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=editor;
 h4_forge_original::sub_8268AE80(ctx,base);
 // The original menu's shared range/step definitions, not invented limits.
 // Authored poses need not lie on an editable integer-angle endpoint. Keep
 // untouched components (for example yaw 179.5 during an X edit); only new
 // requested values must satisfy the original editor's bounds.
 for(unsigned i=0;i<3;++i)if((position[i]<get(base,editor+0xb4)||position[i]>get(base,editor+0xb8))&&position[i]!=current.position[i])
  throw std::runtime_error("Coordinate outside Halo 4 editor range");
 const auto currentAngles=CoordinateAngles(current);
 for(unsigned i=0;i<3;++i)if((angles[i]<get(base,editor+0xc8)||angles[i]>get(base,editor+0xcc))&&std::abs(angles[i]-currentAngles[i])>.0001f)
  throw std::runtime_error("Angle outside Halo 4 editor range");
 word(base,editor+0x28,0);word(base,editor+0x2c,datum);
 real(base,editor+0x30,1);real(base,editor+0x70,1);
 for(unsigned i=0;i<9;++i){real(base,editor+0x34+i*4,current.basis[i]);real(base,editor+0x74+i*4,i%4==0?1.f:0.f);}
 for(unsigned i=0;i<3;++i){
  real(base,editor+0x58+i*4,current.position[i]);real(base,editor+0x98+i*4,position[i]);
  real(base,editor+0xa4+i*4,angles[i]);
 }
 // H3 exposes world coordinates directly: supply a zero coordinate origin.
 word(base,0x8405d33c,0x53000);
 for(unsigned i=0;i<3;++i)real(base,0x5307c+i*4,0);
 CoordinateEdit edit{datum,current};
 struct Scope {explicit Scope(CoordinateEdit& e){coordinateEdit=&e;}~Scope(){coordinateEdit=nullptr;}} scope(edit);
 ctx.r3.u32=editor;h4_forge_original::sub_8268B410(ctx,base);
 return edit.result;
}
std::vector<uint32_t> Bridge::UpdateVisibility(uint32_t held,uint32_t target,bool enabled){
 if(visibleObjects||active||physicsTransition||editorEventSink)throw std::runtime_error("Reentrant H4 visibility update");
 auto& m=*impl_;auto base=m.base;
 // 825826B0 compares current state with the prior held/target arguments.
 word(base,0x21aec,held);word(base,0x21af0,target);base[0x21b3e]=enabled?1:0;
 struct Scope{explicit Scope(std::set<uint32_t>& s){visibleObjects=&s;}~Scope(){visibleObjects=nullptr;}} scope(m.visible);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=m.visibleHeld;ctx.r5.u32=m.visibleTarget;
 h4_forge_original::sub_825826B0(ctx,base);
 // H4's enabled transition assumes selection changed; force it on re-enable
 // by retaining no prior visual selection when the routine removes markers.
 m.visibleHeld=enabled?held:0xffffffff;m.visibleTarget=enabled?target:0xffffffff;
 return {m.visible.begin(),m.visible.end()};
}
SceneryContactResult Bridge::ResolveSceneryContact(const SceneryContactWorld& world,
                                                   const std::array<float,3>& cachedPoint){
 return RunContactResponse(world,cachedPoint,nullptr).response;
}
MonitorContactResult Bridge::ResolveMonitorContact(const MonitorContactWorld& world,
                                                   const std::array<float,3>& cachedPoint){
 return RunContactResponse(world.contact,cachedPoint,&world);
}
MonitorContactResult Bridge::RunContactResponse(const SceneryContactWorld& world,
                     const std::array<float,3>& cachedPoint,const MonitorContactWorld* monitor){
 if(monitorView||obstructionRay||selectionRay||controlledBody||sceneryContact||((active||visibleObjects||heldMagnet)&&!heldUpdate)||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput)
  throw std::runtime_error("Reentrant H4 scenery contact response");
 if((monitor?world.objectType!=0:(world.objectType!=6&&world.objectType!=11))||!world.collect||!world.setLinearVelocity||
    !std::isfinite(world.definitionRadius)||world.definitionRadius<0||!std::isfinite(world.tickInterval)||world.tickInterval<0)
  throw std::runtime_error("Incomplete scenery contact mapping");
 for(float value:world.responseSettings)if(!std::isfinite(value))throw std::runtime_error("Nonfinite contact response setting");
 if(monitor){
  if(!monitor->surfaceNotification||!monitor->tickRate||monitor->tickRate>32767)
   throw std::runtime_error("Incomplete monitor contact mapping");
  for(float value:monitor->responseSettings)if(!std::isfinite(value))
   throw std::runtime_error("Nonfinite monitor contact response setting");
  for(float value:monitor->previousNormal)if(!std::isfinite(value))
   throw std::runtime_error("Nonfinite cached monitor contact normal");
 }
 for(float value:cachedPoint)if(!std::isfinite(value))
  throw std::runtime_error("Nonfinite cached contact point");
 auto base=impl_->base;
 constexpr uint32_t object=0x130000,tag=0x132000,time=0x133000,settings=0x134000,point=0x135000,normal=point+16;
 const uint32_t header=0x41000+65*16,globals=REX_LOAD_U32(0x8405d340);
 const uint32_t previousHeader=REX_LOAD_U32(header+12),previousTag=REX_LOAD_U32(0x51014);
 const uint8_t previousType=base[header+4];
 const uint32_t previousSettings=REX_LOAD_U32(globals+328),previousTime=REX_LOAD_U32(0x11000+88);
 // These projections are private. Preserve outer held-update records and
 // restore shared pointer slots even if a native callback rejects its inputs.
 struct Scope{
  uint8_t* base;uint32_t header,globals,oldHeader,oldTag,oldSettings,oldTime;uint8_t oldType;
  ~Scope(){
   word(base,header+12,oldHeader);base[header+4]=oldType;word(base,0x51014,oldTag);
   word(base,globals+328,oldSettings);word(base,0x11000+88,oldTime);sceneryContact=nullptr;monitorContact=nullptr;
  }
 } scope{base,header,globals,previousHeader,previousTag,previousSettings,previousTime,previousType};
 std::memset(base+object,0,4096);word(base,header+12,object);base[header+4]=world.objectType;
 word(base,object+8,2);word(base,object+36,0xffffffff);word(base,object+364,world.collisionFlags);
 REX_STORE_U64(object+256,world.objectFlags);
 word(base,0x51014,tag);real(base,tag+32,world.definitionRadius);
 word(base,0x11000+88,time);real(base,time+8,world.tickInterval);
 word(base,globals+328,settings);
 for(unsigned i=0;i<3;++i)real(base,settings+16+i*4,world.responseSettings[i]);
 if(monitor){
  for(unsigned i=0;i<4;++i)real(base,settings+i*4,monitor->responseSettings[i]);
  REX_STORE_U16(time+4,monitor->tickRate);word(base,time+12,monitor->tick);
  word(base,object+2188,monitor->surfaceTimestamp);
  base[object+3910]=monitor->movementMode;base[object+4015]=monitor->surfaceFlags;
 }
 StoreVector(base,point,cachedPoint);
 if(monitor)StoreVector(base,normal,monitor->previousNormal);
 else std::memset(base+normal,0,12);
 // Check callback input snapshots before executing the original response.
 for(const auto& vector:{world.velocity,world.physicsPoint})for(float value:vector)
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite native contact state");
 sceneryContact=&world;monitorContact=monitor;
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x160000;ctx.r13.u32=0x10000;
 ctx.r3.u32=65;ctx.r4.u32=point;ctx.r5.u32=normal;
 h4_forge_original::contact_response::sub_82235650(ctx,base);
 MonitorContactResult output;auto& result=output.response;result.contact=(ctx.r3.u32&255)!=0;
 for(unsigned i=0;i<3;++i){result.cachedPoint[i]=get(base,point+i*4);result.normal[i]=get(base,normal+i*4);}
 result.objectFlags=REX_LOAD_U64(object+256);
 if(monitor){
  output.surfaceTimestamp=REX_LOAD_U32(object+2188);
  output.surfaceFlags=base[object+4015];
 }
 return output;
}
std::optional<ContactResolution> Bridge::SelectContactResponse(const ContactSet& contacts,
                                      const std::array<float,3>& point,bool reverse){
 if(monitorView||obstructionRay||selectionRay||controlledBody||sceneryContact||((active||visibleObjects||heldMagnet)&&!heldUpdate)||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput)
  throw std::runtime_error("Reentrant H4 contact selection");
 if(contacts.samples.size()>256||contacts.primary< -1||
    (contacts.primary>=0&&uint32_t(contacts.primary)>=contacts.samples.size())||!std::isfinite(contacts.closestDistance))
  throw std::runtime_error("Invalid H4 contact set");
 auto base=impl_->base;
 constexpr uint32_t table=0xf0000,triangles=0x100000,outputs=0x110000;
 ProjectContactSet(base,table,triangles,contacts);
 std::memset(base+outputs,0,128);StoreVector(base,outputs,point);
 // This pure selector may run inside resolveContact while8244A8D8 is
 // suspended. Use a disjoint stack and scratch region; preserve outer state.
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x170000;ctx.r13.u32=0x10000;
 ctx.r3.u32=table;ctx.r4.u32=outputs;ctx.r5.u32=outputs+16;
 ctx.r6.u32=outputs+32;ctx.r7.u32=outputs+48;ctx.r8.u32=outputs+52;ctx.r9.u32=reverse?1:0;
 h4_forge_original::sub_824863F8(ctx,base);
 if(!(ctx.r3.u32&255))return {};
 ContactResolution result;
 for(unsigned i=0;i<3;++i)result.normal[i]=get(base,outputs+32+i*4);
 result.distance=get(base,outputs+48);result.residualSquared=get(base,outputs+52);
 const auto count=REX_LOAD_U32(outputs+16);
 if(count>3)throw std::runtime_error("Original contact response count out of range");
 for(unsigned i=0;i<count;++i){
  const auto index=REX_LOAD_U32(outputs+20+i*4);
  if(index>=contacts.samples.size())throw std::runtime_error("Original contact response index out of range");
  result.contributingSamples.push_back(index);
 }
 return result;
}
HeldUpdateResult Bridge::UpdateHeld(HeldEditorState& state,const Scene& scene,const HeldUpdateWorld& world){
 return RunHeldStage(state,scene,world,nullptr);
}
HeldUpdateResult Bridge::UpdateMonitorFollow(HeldEditorState& state,const Scene& scene,
                    const HeldUpdateWorld& world,const MonitorFollowWorld& follow){
 return RunHeldStage(state,scene,world,&follow);
}
HeldUpdateResult Bridge::RunHeldStage(HeldEditorState& state,const Scene& scene,
                    const HeldUpdateWorld& world,const MonitorFollowWorld* follow){
 ValidateSceneQuery(scene);
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||heldMagnet||heldUpdate)
  throw std::runtime_error("Reentrant H4 held update");
 if(scene.objects.empty()||scene.objects.size()>65||world.bodyCount>64||world.monitorDatum==0xffffffff||
    !std::isfinite(world.tickInterval)||world.tickInterval<0||world.tick>0x7fffffff||
    !world.objectMotion||!world.objectReferencePoint||!world.objectPhysicsPoint||
    !std::isfinite(world.heldDefinitionRadius)||world.heldDefinitionRadius<0||
    !world.geometryContainsObject||!world.bodyTransform||!world.resolveContact)
  throw std::runtime_error("Incomplete H4 held world mapping");
 for(float value:world.desiredView)if(!std::isfinite(value))throw std::runtime_error("Nonfinite desired monitor view");
 for(float value:{world.definitionMovementMultiplier,world.movementMultiplierFraction})
  if(!std::isfinite(value))throw std::runtime_error("Nonfinite monitor movement multiplier");
 for(unsigned i=0;i<3;++i)if(!std::isfinite(world.variantBounds[i*2])||!std::isfinite(world.variantBounds[i*2+1])||
    world.variantBounds[i*2]>world.variantBounds[i*2+1])throw std::runtime_error("Invalid native variant bounds");
 if(follow){
  if(!follow->query||!world.pointOutsideWorld||!world.objectVelocities||!world.objectOrientation)
   throw std::runtime_error("Incomplete monitor follow world");
  for(float value:follow->contactNormal)if(!std::isfinite(value))
   throw std::runtime_error("Nonfinite monitor contact normal");
 }
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,player=0xb3000,monitor=0xb4000;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 const uint32_t held=REX_LOAD_U32(editor),previous=REX_LOAD_U32(editor+4);
 if(held==0xffffffff||held!=scene.objects[0].datum||REX_LOAD_U32(editor+268)>4||REX_LOAD_U32(editor+224)>5)
  throw std::runtime_error("Held update scene/editor mismatch");
 std::set<uint32_t> datums;
 uint32_t previousIndex=previous==0xffffffff?0xffffffff:66;
 for(uint32_t i=0;i<scene.objects.size();++i){
  const auto& object=scene.objects[i];
  if(object.datum==0xffffffff||!datums.insert(object.datum).second||
     object.markers.size()>32||!std::isfinite(object.radius)||object.radius<0)
   throw std::runtime_error("Invalid held scene object");
  const uint32_t data=0xa0000+i*0x100;
  word(base,0x41000+i*16+12,data);
  StoreVector(base,data+64,object.position);real(base,data+76,object.radius);
  if(object.datum==previous)previousIndex=i;
 }
 for(unsigned i=0;i<13;++i)if(!std::isfinite(get(base,editor+84+i*4)))
  throw std::runtime_error("Nonfinite persistent held target");
 word(base,editor,0);word(base,editor+4,previousIndex);
 word(base,0xa0000+240,world.hasInstance?0:0xffffffff);
 word(base,0x83625160,0xc4000);word(base,0xc4000+68,0xc5000);
 word(base,0xc5000+52,world.bodyCount);
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,player);
 word(base,player+36,monitorIndex);word(base,0x41000+monitorIndex*16+12,monitor);
 StoreVector(base,monitor+1212,world.desiredView);
 StoreVector(base,monitor+1348,scene.processedMovement);
 REX_STORE_U64(monitor+1200,world.movementFlag?1:0);
 real(base,monitor+2168,world.movementMultiplierFraction);
 // Tag0 remains the original Forge configuration. Private tag1 supplies only
 // the monitor definition field actually read by8244A8D8.
 word(base,monitor+8,1);word(base,0x51000+12,0xc8000);
 // Original8244B758 reads the held definition radius, not runtime sphere76.
 word(base,0xa0000+8,2);word(base,0x51000+20,0xc9000);
 real(base,0xc9000+32,world.heldDefinitionRadius);
 real(base,0xc8000+1428,world.definitionMovementMultiplier);
 word(base,0x11000+88,0xc6100);real(base,0xc6100+8,world.tickInterval);
 word(base,0xc6100+12,world.tick);
 for(unsigned i=0;i<6;++i)real(base,0xc0000+696+i*4,world.variantBounds[i]);
 word(base,0xc6000,0);word(base,0xc6004,editor);
 HeldUpdateCall call{world,{},follow!=nullptr};
 MonitorViewCall viewCall;
 const auto priorView=REX_LOAD_U32(0x11000+100),priorLocalMap=REX_LOAD_U32(0x11000+160);
 std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)> followQuery;
 if(follow){
  word(base,monitor-12,monitorIndex);
  REX_STORE_U64(monitor+256,follow->contactActive?(uint64_t(1)<<20):0);
  StoreVector(base,player+152,follow->contactNormal);
  // Private player0 maps to local slot0 only when its native holder is local.
  word(base,0xc7300+29*4,world.localHolder?0:0xffffffff);
  followQuery=[&](const SelectionRayRequest& request){
   auto native=request;
   for(auto& datum:native.exclusions)datum=HeldWorldDatum(datum);
   return follow->query(native);
  };
 }

 HeldMagnetCall magnets{world.localHolder,previous};
 std::set<uint32_t> visible(state.visibleObjects.begin(),state.visibleObjects.end());
 struct Scope{
  Scope(const Scene& scene,HeldUpdateCall& call,const HeldMagnetCall& magnets,std::set<uint32_t>& visible){
   active=&scene;heldUpdate=&call;heldMagnet=&magnets;visibleObjects=&visible;
  }
  uint8_t* base=nullptr;uint32_t priorView=0,priorLocalMap=0;
  ~Scope(){
   active=nullptr;heldUpdate=nullptr;heldMagnet=nullptr;visibleObjects=nullptr;
   monitorView=nullptr;obstructionRay=nullptr;
   if(base){word(base,0x11000+100,priorView);word(base,0x11000+160,priorLocalMap);}
  }
 } scope(scene,call,magnets,visible);
 scope.base=base;scope.priorView=priorView;scope.priorLocalMap=priorLocalMap;
 if(follow){
  word(base,0x11000+160,0xc7300);word(base,0x11000+100,0xc7000);
  monitorView=&viewCall;obstructionRay=&followQuery;
 }
 PPCContext ctx{};ctx.fpscr.loadFromHost();ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;ctx.r3.u32=0xc6000;
 // Original function includes the conditional correction, body-cache refresh,
 // both bounds clamps, contact projection, displacement cap, quantization,
 // magnet caller and controller request. Do not reorder its internal stages.
 if(follow){
  h4_forge_original::sub_8244AF48(ctx,base);
  if(viewCall.notified!=world.localHolder)
   throw std::runtime_error("Unexpected original monitor local-view result");
  if(viewCall.notified){
   call.result.viewAngles=viewCall.angles;
   call.result.viewDirection=viewCall.direction;
  }
  // Follow writes its two private ray exclusions into persistent state.
  // Convert only those identities; all original smoothing fields survive.
  if(base[editor+80]){
   word(base,editor+256,held);word(base,editor+260,world.monitorDatum);
  }
 }else h4_forge_original::sub_8244A8D8(ctx,base);
 const auto selected=REX_LOAD_U32(editor+4);
 uint32_t selectedNative=0xffffffff;
 if(selected==66)selectedNative=previous; // Original early return retains it.
 else if(selected!=0xffffffff){
  if(selected>=scene.objects.size())throw std::runtime_error("Original held candidate outside scene");
  selectedNative=scene.objects[selected].datum;
 }
 word(base,editor,held);word(base,editor+4,selectedNative);
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
 state.visibleObjects.assign(visible.begin(),visible.end());
 call.result.targetDatum=selectedNative;
 call.result.visibleObjects=state.visibleObjects;
 return call.result;
}
std::array<float,13> Bridge::PrepareHeldSubmission(HeldEditorState& state){
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||heldMagnet)
  throw std::runtime_error("Reentrant H4 held submission preparation");
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,submission=0x31000;
 std::memcpy(base+editor,state.bytes.data(),state.bytes.size());
 const auto mode=REX_LOAD_U32(editor+224);
 if(mode>5)throw std::runtime_error("Invalid original rotation-step mode");
 for(unsigned i=0;i<13;++i)if(!std::isfinite(get(base,editor+84+i*4)))
  throw std::runtime_error("Nonfinite persistent held pose");
 std::memcpy(base+submission,base+editor+84,52);
 if(mode&&base[editor+81]){
  //8244ADD0..8244ADEC: original image table and degree-to-radian constant.
  const float degrees=static_cast<float>(static_cast<int32_t>(REX_LOAD_U32(0x833f195c+mode*4)));
  const float step=static_cast<float>(static_cast<double>(degrees)*get(base,0x82128a20));
  PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
  ctx.r3.u32=submission;ctx.f1.f64=step;
  h4_forge_original::sub_82451A38(ctx,base);
  //8244ADF0..8244AED4 compares the nine basis floats against the remembered
  // quantized basis, not against the current unquantized target. Equal basis
  // leaves the accumulated target intact while submission stays quantized.
  const float epsilon=get(base,0x82128a54);
  bool same=true;
  for(unsigned i=0;i<9;++i){
   const float difference=static_cast<float>(static_cast<double>(get(base,editor+136+i*4))-get(base,submission+4+i*4));
   if(!(std::abs(difference)<epsilon)){same=false;break;}
  }
  if(!same){
   std::memcpy(base+editor+84,base+submission,52);
   std::memcpy(base+editor+136,base+submission+4,36);
  }
 }
 std::array<float,13> result;
 for(unsigned i=0;i<13;++i)result[i]=get(base,submission+i*4);
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
 return result;
}
HeldMagnetSubmission Bridge::ApplyHeldMagnets(HeldEditorState& state,const Scene& scene,bool localHolder){
 ValidateSceneQuery(scene);
 if(monitorView||obstructionRay||selectionRay||controlledBody||active||visibleObjects||coordinateEdit||physicsSelection||physicsTransition||editorEventSink||heldSelection||manipulationInput||heldMagnet)
  throw std::runtime_error("Reentrant H4 held magnet update");
 if(scene.objects.empty()||scene.objects.size()>65)throw std::runtime_error("Invalid held magnet scene");
 auto staged=state;
 const auto prepared=PrepareHeldSubmission(staged);
 auto base=impl_->base;
 constexpr uint32_t editor=0x21aec,submission=0x31000;
 std::memcpy(base+editor,staged.bytes.data(),staged.bytes.size());
 const auto held=REX_LOAD_U32(editor),previous=REX_LOAD_U32(editor+4);
 if(held==0xffffffff||held!=scene.objects[0].datum||REX_LOAD_U32(editor+268)>4)
  throw std::runtime_error("Held magnet scene/editor mismatch");
 std::set<uint32_t> datums;
 uint32_t previousIndex=previous==0xffffffff?0xffffffff:66;
 for(uint32_t i=0;i<scene.objects.size();++i){
  const auto& o=scene.objects[i];
  if(o.datum==0xffffffff||!datums.insert(o.datum).second||o.markers.size()>32||!std::isfinite(o.radius)||o.radius<0)
   throw std::runtime_error("Invalid held magnet object");
  const uint32_t data=0xa0000+i*0x100;
  word(base,0x41000+i*16+12,data);
  for(unsigned j=0;j<3;++j){
   if(!std::isfinite(o.position[j]))throw std::runtime_error("Nonfinite held magnet position");
   real(base,data+0x40+j*4,o.position[j]);
  }
  real(base,data+0x4c,o.radius);
  if(o.datum==previous)previousIndex=i;
 }
 for(unsigned i=0;i<13;++i)if(!std::isfinite(get(base,editor+84+i*4)))
  throw std::runtime_error("Nonfinite persistent held pose");
 word(base,editor,0);word(base,editor+4,previousIndex);
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,0xb3000);
 word(base,0xb3000+36,monitorIndex);word(base,0x41000+monitorIndex*16+12,0xb4000);
 for(unsigned j=0;j<3;++j){
  if(!std::isfinite(scene.processedMovement[j]))throw std::runtime_error("Nonfinite held movement");
  real(base,0xb4000+1348+j*4,scene.processedMovement[j]);
 }
 // Quantized submission can differ from the retained accumulator even when
 // no magnet is selected. Never reconstruct it from editor84 here.
 for(unsigned i=0;i<13;++i)real(base,submission+i*4,prepared[i]);
 HeldMagnetCall call{localHolder,previous};
 std::set<uint32_t> visible(state.visibleObjects.begin(),state.visibleObjects.end());
 struct Scope{
  Scope(const Scene& scene,const HeldMagnetCall& call,std::set<uint32_t>& visible){
   active=&scene;heldMagnet=&call;visibleObjects=&visible;
  }
  ~Scope(){active=nullptr;heldMagnet=nullptr;visibleObjects=nullptr;}
 } scope(scene,call,visible);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=0;ctx.r5.u32=editor;ctx.r6.u32=submission;
 h4_forge_original::sub_8244EED8(ctx,base);
 HeldMagnetSubmission result;
 for(unsigned i=0;i<13;++i)result.pose[i]=get(base,submission+i*4);
 const auto selected=REX_LOAD_U32(editor+4);
 if(selected==66)result.targetDatum=previous;
 else if(selected!=0xffffffff){
  if(selected>=scene.objects.size())throw std::runtime_error("Original magnet candidate outside scene");
  result.targetDatum=scene.objects[selected].datum;
 }
 word(base,editor,held);word(base,editor+4,result.targetDatum);
 std::memcpy(state.bytes.data(),base+editor,state.bytes.size());
 state.visibleObjects.assign(visible.begin(),visible.end());
 result.visibleObjects=state.visibleObjects;
 return result;
}
Result Bridge::Evaluate(const Scene& scene){
 ValidateSceneQuery(scene);
 if(active||physicsTransition||editorEventSink)throw std::runtime_error("Reentrant H4 Forge evaluation");
 if(scene.objects.empty()||scene.objects.size()>65||scene.sensitivity>4)throw std::runtime_error("Invalid H4 Forge scene bounds");
 for(const auto& o:scene.objects){
  if(o.markers.size()>32||!std::isfinite(o.radius)||o.radius<0)throw std::runtime_error("Invalid object bounds/markers");
  for(float v:o.position)if(!std::isfinite(v))throw std::runtime_error("Nonfinite object position");
 }
 for(float v:scene.processedMovement)if(!std::isfinite(v))throw std::runtime_error("Nonfinite processed movement");
 struct Scope{Scope(const Scene& s){active=&s;}~Scope(){active=nullptr;}} scope(scene);
 auto base=impl_->base;
 for(uint32_t i=0;i<scene.objects.size();++i){
  uint32_t data=0xa0000+i*0x100;
  word(base,0x41000+i*16+12,data);
  for(unsigned j=0;j<3;++j)real(base,data+0x40+j*4,scene.objects[i].position[j]);
  real(base,data+0x4c,scene.objects[i].radius);
 }
 // Private player/unit records for the unchanged H4 movement predicate.
 // Monitor index67 is separate from scene indices0..64.
 word(base,0x11000+24,0xb2000);word(base,0xb2000+68,0xb3000);
 word(base,0xb3000+36,monitorIndex);word(base,0x41000+monitorIndex*16+12,0xb4000);
 for(unsigned j=0;j<3;++j)real(base,0xb4000+1348+j*4,scene.processedMovement[j]);
 constexpr uint32_t player=0x21aec;
 std::memset(base+player,0,0x150);
 word(base,player,0);word(base,0x21bf8,scene.sensitivity);
 real(base,player+0x24,1);
 for(unsigned j=0;j<3;++j)real(base,player+0x38+j*4,scene.cursor[j]-scene.objects[0].position[j]);
 real(base,player+0x54,1);
 for(unsigned j=0;j<9;++j)real(base,player+0x58+j*4,scene.heldBasis[j]);
 PPCContext ctx{};ctx.r1.u32=0x180000;ctx.r13.u32=0x10000;
 ctx.r3.u32=0;ctx.r4.u32=0;ctx.r5.u32=0x30000;
 h4_forge_original::sub_82582250(ctx,base);
 Result result;
 auto target=REX_LOAD_U32(0x30074);
 // Retail caller 8244EF08 retains the candidate for marker visibility even
 // when selection hasn't reached the snap threshold (8244EF0C).
 if(target!=0xffffffff){
  if(target>=scene.objects.size())throw std::runtime_error("Original H4 result outside scene");
  result.targetDatum=scene.objects[target].datum;
 }
 if(ctx.r3.u32!=2)return result;
 if(target==0xffffffff)throw std::runtime_error("Original H4 snap has no target");
 // Original8244EED8 retains selection but suppresses alignment while moving.
 ctx.r3.u32=0;h4_forge_original::sub_82582178(ctx,base);
 if(ctx.r3.u32)return result;
 ctx.r3.u32=0;ctx.r4.u32=0x30004;ctx.r5.u32=0x30078;ctx.r6.u32=0x31000;ctx.r7.u32=0x31100;
 h4_forge_original::sub_82582AD0(ctx,base);
 for(unsigned j=0;j<4;++j)result.rotation[j]=get(base,0x31000+j*4);
 for(unsigned j=0;j<3;++j)result.position[j]=get(base,0x31100+j*4);
 result.snapped=true;result.targetDatum=scene.objects[target].datum;
 return result;
}
}
