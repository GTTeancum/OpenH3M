#include "forge_bridge.h"
#include "forge_coordinates.h"
#include "forge_physics.h"
#include "scene_snapshot.h"
#include <bit>
#include <cstring>
#include <iostream>
#include <iomanip>
#include <stdexcept>
#include <cmath>
using namespace advanced_forge;
static Marker marker(float x){
 Marker m{};
 auto put=[&](unsigned a,float v){uint32_t u=std::byteswap(std::bit_cast<uint32_t>(v));std::memcpy(m.data()+a,&u,4);};
 for(unsigned a:{8u,0x3cu})for(unsigned i=0;i<9;++i)put(a+i*4,i%4==0?1.f:0.f);
 put(4,1);put(0x38,1);put(0x60,x);return m;
}
int main(int argc,char** argv){try{
 Bridge b("work/h4-forge-research/h4-image.bin","work/h4-forge-research/isolated/forge-globals.bin");
 if(argc==2&&std::string(argv[1])=="--asymmetric-bounds"){
  const std::array<float,6> bounds{-203.60046f,277.6636f,-360.82645f,324.92484f,-25.010117f,117.79051f};
  std::array<float,13> pose{1,1,0,0,0,1,0,0,0,1,-51,-250,3.5f};
  if(b.ConstrainGrabPose(pose,bounds)!=pose)
   throw std::runtime_error("Interior Y incorrectly constrained by another axis");
  for(unsigned axis=0;axis<3;++axis)for(unsigned side=0;side<2;++side){
   auto outside=pose;outside[10+axis]=bounds[axis*2+side]+(side?10.f:-10.f);
   auto expected=pose;expected[10+axis]=bounds[axis*2+side];
   if(b.ConstrainGrabPose(outside,bounds)!=expected)
    throw std::runtime_error("Original bounds mapping changed an unrelated coordinate/basis");
  }
  std::cout<<"Original H4 asymmetric XYZ bounds: interior and all six faces passed\n";
  return 0;
 }
 if(argc==2&&std::string(argv[1])=="--held-physics"){
  for(auto mode:{PhysicsMode::Normal,PhysicsMode::Fixed,PhysicsMode::Phased}){
   PhysicsTransition current;current.held=true;current.localHolder=true;
   current.hasInstance=true;current.hasPhysicsModel=true;
   current.state=b.SelectPhysicsState(mode,true,false,false,true);
   auto result=b.TransitionPhysics(current,[&](uint64_t flags,bool create){
    std::cout<<"mode="<<unsigned(mode)<<" state="<<current.state<<" rebuild-flags="<<flags<<" create="<<create<<'\n';
    return PhysicsBodyUpdate{flags,{},true};
   });
   if(mode==PhysicsMode::Phased&&!(result.flags&(1ull<<22)))
    throw std::runtime_error("Original local held Phased transition did not request keyframed body");
  }
  return 0;
 }
 if(argc==3&&std::string(argv[1])=="--coincident-pack"){
  std::ifstream in(argv[2],std::ios::binary);char magic[4];uint32_t count=0;
  in.read(magic,4);in.read(reinterpret_cast<char*>(&count),4);
  if(!in||std::memcmp(magic,"AFM3",4)||count>1024)throw std::runtime_error("Expected current AFM3 pack");
  std::vector<MarkerDefinition> definitions;float radius=0;
  for(uint32_t i=0;i<count;++i){
   uint32_t map,tag,n,fixed;float r;
   in.read(reinterpret_cast<char*>(&map),4);in.read(reinterpret_cast<char*>(&tag),4);
   in.read(reinterpret_cast<char*>(&r),4);in.read(reinterpret_cast<char*>(&n),4);
   in.read(reinterpret_cast<char*>(&fixed),4);
   if(!in||n>32||!n)throw std::runtime_error("Invalid AFM3 binding");
   in.seekg(n*28,std::ios::cur);
   std::vector<MarkerDefinition> records(n);
   for(auto& record:records)in.read(reinterpret_cast<char*>(record.data()),record.size());
   if(!in)throw std::runtime_error("Truncated AFM3 records");
   if(map==1730&&tag==0x90002952){definitions=std::move(records);radius=r;}
  }
  if(definitions.empty()||in.peek()!=EOF)throw std::runtime_error("Base Round binding missing or trailing pack data");
  for(const auto& definition:definitions)
   if(definition[2]!=0||definition[0]!=255)throw std::runtime_error("Fixture requires original root-node, unrestricted-region records");
  for(bool opposed:{false,true}){
   Scene scene;
   for(unsigned i=0;i<2;++i){
    const float sign=i&&opposed?-1.f:1.f,y=i?.1f:0.f;
    const std::array<float,13> node{1,sign,0,0,0,sign,0,0,0,1,0,y,0};
    auto markers=b.BuildMarkers(definitions,{node},std::nullopt,false);
    scene.objects.push_back({i?456u:123u,{0,y,0},radius,std::move(markers),true});
   }
   scene.nearbyOrder=std::vector<uint32_t>{0,1};
   const auto result=b.Evaluate(scene);
   std::cout<<std::setprecision(9)<<"AFM3 Base Round opposed="<<opposed<<" snapped="<<result.snapped
    <<" target="<<result.targetDatum<<" position="<<result.position[0]<<","<<result.position[1]<<","<<result.position[2]
    <<" rotation="<<result.rotation[0]<<","<<result.rotation[1]<<","<<result.rotation[2]<<","<<result.rotation[3]<<'\n';
   // Exercise the original held-magnet caller as well as its selector. This
   // staged editor isolates that boundary; it does not simulate world collision.
   auto editor=b.InitializeHeldEditorState({},[](const std::string&){});
   auto word=[&](unsigned offset,uint32_t value){value=std::byteswap(value);std::memcpy(editor.bytes.data()+offset,&value,4);};
   auto real=[&](unsigned offset,float value){word(offset,std::bit_cast<uint32_t>(value));};
   word(0,123);word(4,0xffffffff);word(268,scene.sensitivity);editor.bytes[82]=1;
   const std::array<float,13> pose{1,1,0,0,0,1,0,0,0,1,0,0,0};
   for(unsigned j=0;j<pose.size();++j)real(84+j*4,pose[j]);
   real(36,1);real(40,1);
   const auto held=b.ApplyHeldMagnets(editor,scene,true);
   std::cout<<"held-caller opposed="<<opposed<<" target="<<held.targetDatum
    <<" position="<<held.pose[10]<<","<<held.pose[11]<<","<<held.pose[12]<<'\n';
  }
  return 0;
 }
 if(argc==2){
  auto scene=LoadScene(argv[1]);auto result=b.Evaluate(scene);
  std::cout<<std::setprecision(9)<<"Captured scene: "<<scene.objects.size()<<" objects; snap="<<result.snapped
           <<" target="<<result.targetDatum<<" position="<<result.position[0]<<","<<result.position[1]<<","<<result.position[2]<<"\n";
  std::cout<<"rotation="<<result.rotation[0]<<","<<result.rotation[1]<<","<<result.rotation[2]<<","<<result.rotation[3]<<"\n";
  return 0;
 }
 Scene s;s.objects={{123,{0,0,0},1,{marker(0)}},{456,{0.1f,0,0},1,{marker(.1f)}}};
 auto r=b.Evaluate(s);
 if(!r.snapped||r.targetDatum!=456||std::abs(r.position[0]-.1f)>.0001f)throw std::runtime_error("near target failed");
 // Candidate remains selected while original movement gate suppresses snapping.
 for(unsigned axis=0;axis<3;++axis)for(float speed:{1.f,0.f,-1.f,0.f}){
  s.processedMovement={};s.processedMovement[axis]=speed;
  auto moving=b.Evaluate(s);
  if(moving.targetDatum!=456||moving.snapped!=(speed==0.f))
   throw std::runtime_error("bridge movement/stop/resume gate failed");
 }
 // Diagnostic replay must retain movement; old AFS1 scenes mean stationary.
 s.processedMovement={1.f,0.f,0.f};
 const std::string diagnostic="work/h4-forge-research/isolated/bridge-scene-test.bin";
 SaveScene(diagnostic,s);auto replay=LoadScene(diagnostic);
 if(replay.processedMovement!=s.processedMovement||b.Evaluate(replay).snapped)
  throw std::runtime_error("moving diagnostic replay failed");
 std::ifstream diagnosticInput(diagnostic,std::ios::binary);
 std::string legacy((std::istreambuf_iterator<char>(diagnosticInput)),{});diagnosticInput.close();
 legacy[3]='1';legacy.erase(60,12);
 {std::ofstream legacyOut(diagnostic,std::ios::binary|std::ios::trunc);legacyOut.write(legacy.data(),legacy.size());}
 replay=LoadScene(diagnostic);
 if(replay.processedMovement!=std::array<float,3>{}||!b.Evaluate(replay).snapped)
  throw std::runtime_error("legacy stationary diagnostic failed");
 s.processedMovement={};
 std::cout<<"PASS original movement gate in bridge:12 moving/stopped/resumed evaluations; candidate retained. Live input not exercised by this fixture.\n";
 s.objects[1].position[0]=.75f;s.objects[1].markers={marker(.75f)};
 r=b.Evaluate(s);
 if(r.snapped||r.targetDatum!=456)throw std::runtime_error("nearby unsnapped target lost its anchor candidate");
 s.objects[1].position[0]=3;s.objects[1].markers={marker(3)};
 if(b.Evaluate(s).snapped)throw std::runtime_error("far target snapped");
 s.objects.push_back({789,{.2f,0,0},1,{marker(.2f)}});
 r=b.Evaluate(s);
 if(!r.snapped||r.targetDatum!=789)throw std::runtime_error("candidate selection failed");
 s.objects[2].markers.clear();
 if(b.Evaluate(s).snapped)throw std::runtime_error("markerless target snapped");
 constexpr uint32_t none=0xffffffff;
 // Exercise the actual original setter for every 16-bit incoming word.
 // H4 retains ten defined property bits, replacing only the physics pair.
 // The unrelated low bits must survive all three transitions; reserved high
 // bits must be cleared exactly as in the retail instruction sequence.
 for(uint32_t properties=0;properties<=0xffff;++properties){
  for(auto mode:{PhysicsMode::Normal,PhysicsMode::Fixed,PhysicsMode::Phased}){
   const auto changed=b.EditPhysics(uint16_t(properties),mode);
   if((changed&0xc0)!=static_cast<uint16_t>(mode)||
      (changed&0x33f)!=(properties&0x33f)||(changed&0xfc00))
    throw std::runtime_error("original H4 physics property transition failed");
  }
 }
 bool invalidPhysics=false;
 try{b.EditPhysics(0,static_cast<PhysicsMode>(0x80));}catch(const std::exception&){invalidPhysics=true;}
 if(!invalidPhysics)throw std::runtime_error("invalid physics mode accepted");
 PhysicsSession physics;
 physics.Update(123,PhysicsMode::Fixed);
 auto physicsSelection=physics.Read();
 if(!physics.Queue(physicsSelection,PhysicsMode::Phased)||physics.Update(123,PhysicsMode::Fixed)!=PhysicsMode::Phased)
  throw std::runtime_error("physics command not consumed");
 if(physics.Update(123,PhysicsMode::Phased))throw std::runtime_error("physics command repeated");
 physics.Queue(physics.Read(),PhysicsMode::Fixed);physics.Publish(123,PhysicsMode::Phased);
 if(physics.Update(123,PhysicsMode::Phased)!=PhysicsMode::Fixed)throw std::runtime_error("publishing physics state consumed a newer command");
 physics.Queue(physics.Read(),PhysicsMode::Normal);physics.Reset();physics.Update(123,PhysicsMode::Fixed);
 if(physics.Queue(physicsSelection,PhysicsMode::Normal)||physics.Update(123,PhysicsMode::Fixed))
  throw std::runtime_error("physics command survived release/regrab");
 physicsSelection=physics.Read();physics.Update(456,PhysicsMode::Normal);
 if(physics.Queue(physicsSelection,PhysicsMode::Phased))throw std::runtime_error("physics command applied to another object");
 auto expectVisibility=[&](uint32_t held,uint32_t target,bool enabled,std::vector<uint32_t> expected){
  if(b.UpdateVisibility(held,target,enabled)!=expected)throw std::runtime_error("original H4 marker visibility transition failed");
 };
 expectVisibility(123,456,true,{123,456});
 expectVisibility(123,456,true,{123,456});
 expectVisibility(123,789,true,{123,789});
 expectVisibility(456,none,true,{456});
 expectVisibility(456,none,false,{});
 expectVisibility(456,none,true,{456});
 expectVisibility(none,none,true,{});
 CoordinatePose pose;
 const auto ranges=b.CoordinateRanges();
 if(ranges[0].minimum!=-1000||ranges[0].maximum!=1000||std::abs(ranges[0].step-.1f)>1e-7f||
    ranges[1].minimum!=-180||ranges[1].maximum!=179||ranges[1].step!=1)
  throw std::runtime_error("Unexpected original H4 coordinate menu ranges/steps");
 auto positioned=b.EditCoordinates(123,pose,{-44.125f,-197.5f,3.f},{0,0,0});
 if(positioned.position!=std::array<float,3>{-44.125f,-197.5f,3.f}||positioned.basis!=pose.basis)
  throw std::runtime_error("original H4 coordinate translation failed");
 auto turned=b.EditCoordinates(123,positioned,positioned.position,{90,0,0});
 if(std::abs(turned.basis[0])>.0001f||std::abs(turned.basis[1]-1)>.0001f||std::abs(turned.basis[8]-1)>.0001f)
  throw std::runtime_error("original H4 coordinate yaw failed");
 const auto angles=b.CoordinateAngles(turned);
 if(std::abs(angles[0]-90)>.001f||std::abs(angles[1])>.001f||std::abs(angles[2])>.001f)
  throw std::runtime_error("original H4 coordinate angle readback failed");
 auto reset=b.EditCoordinates(123,turned,turned.position,{0,0,0});
 for(unsigned i=0;i<9;++i)if(std::abs(reset.basis[i]-pose.basis[i])>.0001f)
  throw std::runtime_error("original H4 coordinate reset failed");
 bool rejected=false;try{b.EditCoordinates(123,pose,{1001,0,0},{0,0,0});}catch(const std::exception&){rejected=true;}
 if(!rejected)throw std::runtime_error("H4 coordinate limit not enforced");
 CoordinatePose edge=pose;
 const float yaw=179.5f*3.14159265358979323846f/180.f;
 edge.basis={std::cos(yaw),std::sin(yaw),0,-std::sin(yaw),std::cos(yaw),0,0,0,1};
 const auto edgeAngles=b.CoordinateAngles(edge);
 if(edgeAngles[0]<=179)throw std::runtime_error("Boundary fixture did not exercise an authored fractional angle");
 const auto translatedEdge=b.EditCoordinates(123,edge,{1,2,3},edgeAngles);
 for(unsigned i=0;i<9;++i)if(std::abs(translatedEdge.basis[i]-edge.basis[i])>.00001f)
  throw std::runtime_error("Position edit altered the authored fractional angle");
 rejected=false;try{b.EditCoordinates(123,pose,{1,2,3},{180,0,0});}catch(const std::exception&){rejected=true;}
 if(!rejected)throw std::runtime_error("New out-of-range angle was accepted");
 CoordinateSession session;
 if(session.Update(30,123,pose,b))throw std::runtime_error("coordinates lock without request");
 auto selected=session.Read();
 if(!session.Queue(selected,{-44,-197,3},{90,0,0}))throw std::runtime_error("coordinate request rejected");
 auto exact=session.Update(30,123,pose,b);
 if(!exact||exact->position!=std::array<float,3>{-44,-197,3})throw std::runtime_error("coordinate request not applied");
 CoordinatePose drifting;drifting.position={6,7,8};
 exact=session.Update(30,123,drifting,b);
 if(!exact||exact->position!=std::array<float,3>{-44,-197,3})throw std::runtime_error("precise pose lost during native drag");
 session.Update(30,456,pose,b);
 if(session.Queue(selected,{1,2,3},{0,0,0})||session.Locked())throw std::runtime_error("stale selection applied");
 selected=session.Read();session.Queue(selected,{1,2,3},{0,0,0});session.Reset();session.Update(30,456,pose,b);
 if(session.Locked()||session.Queue(selected,{1,2,3},{0,0,0}))throw std::runtime_error("release/regrab retained pending edit");
 selected=session.Read();session.Queue(selected,{1,2,3},{0,0,0});session.Update(30,456,pose,b);
 session.Queue(session.Read(),{}, {},true);
 if(session.Update(30,456,drifting,b)||session.Locked())throw std::runtime_error("resume movement remained locked");
 if(session.Read().pose.position!=drifting.position)throw std::runtime_error("resume did not publish current native pose");
 std::cout<<"PASS original H4 bridge: near, unsnapped visible candidate, far, alternate candidate, missing markers\n";
 std::cout<<"PASS original H4 visibility: held/target, unchanged, target swap, held swap, disable, re-enable, release\n";
 std::cout<<"PASS original H4 coordinate commit: translation, yaw, angle readback, reset and retail limits\n";
 std::cout<<"PASS original H4 physics setter: 196608 property transitions and invalid-mode rejection; private H4 memory only\n";
 std::cout<<"PASS physics command handoff: single consumption, selection change and release/regrab invalidation\n";
 std::cout<<"PASS coordinate session: apply, held pose, stale selection rejection, release/regrab and resume\n";
 return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
