#include "forge_controls.h"
#include "forge_overlay.h"
#include <rex/ui/keybinds.h>
#include <iostream>
#include <stdexcept>
using namespace advanced_forge;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main(){try{
 ImGui::CreateContext();auto& io=ImGui::GetIO();io.IniFilename=nullptr;io.LogFilename=nullptr;
 io.DisplaySize={1280,720};io.DeltaTime=1.f/60;
 unsigned char* pixels;int width,height;io.Fonts->GetTexDataAsRGBA32(&pixels,&width,&height);
 ControlState state;bool visible=false;PanelGeometry geometry;
 CoordinateSession coordinates;CoordinateDraft draft;PhysicsSession physics;bool coordinatePanel=false;
 auto frame=[&](){ImGui::NewFrame();ImGui::SetNextWindowPos({40,40});ImGui::SetNextWindowSize({440,coordinatePanel?560.f:180.f});
  DrawControls(visible,state,"Ready",0,0,&geometry,coordinatePanel?&coordinates:nullptr,&draft,coordinatePanel?&physics:nullptr);ImGui::Render();};
 frame();require(!visible&&!state.enabled,"default state");
 bool achievements=false;
 rex::ui::RegisterBind("bind_achievements","F7","Test SDK conflict",[&](){achievements=true;});
 auto key=[](){return rex::ui::KeyEvent(nullptr,rex::ui::VirtualKey::kF7,1,false,false,false,false,false);};
 auto consumed=key();require(rex::ui::ProcessKeyEvent(consumed)&&achievements,"reproduce achievements conflict");
 rex::ui::UnregisterBind("bind_achievements");achievements=false;
 auto freed=key();require(!rex::ui::ProcessKeyEvent(freed)&&!freed.is_handled()&&!achievements,"release F7 in SDK dispatcher");
 io.AddKeyEvent(ImGuiKey_F7,true);frame();require(visible,"F7 open");
 io.AddKeyEvent(ImGuiKey_F7,false);frame();frame();
 require(ImGui::GetDrawData()->TotalVtxCount>0,"panel draw data");
 auto click=[&](ImVec2 p){io.AddMousePosEvent(p.x,p.y);frame();io.AddMouseButtonEvent(0,true);frame();io.AddMouseButtonEvent(0,false);frame();};
 click({geometry.toggleMin.x+8,(geometry.toggleMin.y+geometry.toggleMax.y)/2});require(state.enabled,"checkbox enable");
 // The slider's frame width excludes the text label to its right.
 click({geometry.sliderMin.x+270,(geometry.sliderMin.y+geometry.sliderMax.y)/2});require(state.sensitivity==4,"highest sensitivity");
 click({geometry.sliderMin.x+2,(geometry.sliderMin.y+geometry.sliderMax.y)/2});require(state.sensitivity==0,"lowest sensitivity");
 click({geometry.toggleMin.x+8,(geometry.toggleMin.y+geometry.toggleMax.y)/2});require(!state.enabled,"checkbox disable");
 io.AddKeyEvent(ImGuiKey_F7,true);frame();require(!visible,"F7 close");
 AnchorCamera camera{{0,0,0},{1,0,0},{0,0,1},1.57079632679f,16.f/9};ImVec2 pixel;
 require(ProjectAnchor(camera,{10,0,0},{1280,720},pixel)&&std::abs(pixel.x-640)<.001f&&std::abs(pixel.y-360)<.001f,"anchor center projection");
 require(ProjectAnchor(camera,{10,-5,0},{1280,720},pixel)&&std::abs(pixel.x-960)<.001f,"anchor right projection");
 require(ProjectAnchor(camera,{10,0,2.5f},{1280,720},pixel)&&std::abs(pixel.y-200)<.001f,"anchor vertical projection");
 require(!ProjectAnchor(camera,{-1,0,0},{1280,720},pixel),"behind-camera anchor");
 require(!ProjectAnchor(camera,{1,10,0},{1280,720},pixel),"offscreen anchor");
 io.AddKeyEvent(ImGuiKey_F7,false);frame();
 Bridge bridge("work/h4-forge-research/h4-image.bin","work/h4-forge-research/isolated/forge-globals.bin");
 CoordinatePose current;coordinates.Update(1730,123,current,bridge);
 auto original=coordinates.Read();
 require(coordinates.BeginPreview(original),"begin free numeric preview");
 require(coordinates.Queue(original,current.position,{90,0,0}),"queue preview angle");
 auto preview=coordinates.Update(1730,123,current,bridge);
 require(preview&&std::abs(preview->basis[1]-1)<.0001f,"preview changes pose before commit");
 require(coordinates.FinishPreview(coordinates.Read(),false),"cancel preview");
 require(!coordinates.Locked()&&coordinates.Read().pose.basis==original.pose.basis,"cancel restores free mode and pose");
 require(coordinates.BeginPreview(coordinates.Read()),"begin accepted preview");
 require(coordinates.Queue(coordinates.Read(),current.position,{90,0,0}),"queue accepted preview");
 coordinates.Update(1730,123,current,bridge);
 require(coordinates.FinishPreview(coordinates.Read(),true)&&coordinates.Locked(),"accept retains preview");
 auto locked=coordinates.Read();
 require(coordinates.BeginPreview(locked),"begin locked preview");
 require(coordinates.Queue(locked,current.position,{45,0,0}),"queue second preview angle");
 coordinates.Update(1730,123,current,bridge);
 require(coordinates.FinishPreview(coordinates.Read(),false)&&coordinates.Read().pose.basis==locked.pose.basis&&coordinates.Locked(),"cancel restores prior locked pose");
 require(coordinates.BeginPreview(coordinates.Read()),"begin stale preview");
 coordinates.Update(1730,124,current,bridge);
 require(!coordinates.FinishPreview(locked,false),"old preview cannot restore another object");
 coordinates.Reset();coordinates.Update(1730,123,current,bridge);
 coordinatePanel=true;visible=true;frame();frame();
 draft.position={-44.125f,-197.5f,3};draft.angles={90,0,0};draft.dirty=true;
 click({geometry.applyMin.x+15,(geometry.applyMin.y+geometry.applyMax.y)/2});
 auto applied=coordinates.Update(1730,123,current,bridge);
 require(applied&&applied->position==draft.position&&std::abs(applied->basis[1]-1)<.0001f,"coordinate Apply button");
 frame();frame();
 click({geometry.resumeMin.x+15,(geometry.resumeMin.y+geometry.resumeMax.y)/2});
 require(!coordinates.Update(1730,123,current,bridge),"coordinate Resume button");
 frame();draft.position[0]=1001;draft.dirty=true;
 click({geometry.applyMin.x+15,(geometry.applyMin.y+geometry.applyMax.y)/2});
 require(!coordinates.Update(1730,123,current,bridge),"invalid coordinate Apply disabled");
 physics.Update(123,PhysicsMode::Normal);frame();frame();
 for(unsigned i:{1u,2u,0u}){
  const PhysicsMode modes[]={PhysicsMode::Normal,PhysicsMode::Fixed,PhysicsMode::Phased};
  click({geometry.physicsMin[i].x+8,(geometry.physicsMin[i].y+geometry.physicsMax[i].y)/2});
  require(physics.Update(123,modes[i])==modes[i],"physics radio control command");
  frame();frame();
 }
 ImGui::DestroyContext();std::cout<<"PASS process-local SDK F7 dispatch, ImGui open/close, toggle on/off, low/high sensitivity, anchor projection, coordinate Apply/Resume, invalid-input guard and Normal/Fixed/Phased controls; no OS input\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
