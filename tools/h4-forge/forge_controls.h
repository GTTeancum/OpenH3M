#pragma once
#include <imgui.h>
#include <atomic>
#include <cstdint>
#include <cmath>
#include "forge_coordinates.h"
#include "forge_physics.h"
namespace advanced_forge {
struct ControlState {std::atomic<bool> enabled=false,showAnchors=true;std::atomic<unsigned> sensitivity=2;};
struct PanelGeometry {ImVec2 toggleMin{},toggleMax{},sliderMin{},sliderMax{},applyMin{},applyMax{},resumeMin{},resumeMax{};std::array<ImVec2,3> physicsMin{},physicsMax{};};
struct CoordinateDraft {uint64_t generation=0;std::array<float,3> position{},angles{};bool dirty=false;};
inline void DrawCoordinates(CoordinateSession& session,CoordinateDraft& draft,PanelGeometry* geometry){
 auto view=session.Read();
 ImGui::Separator();ImGui::TextUnformatted("Precise movement (Halo 4)");
 if(!view.fresh()){ImGui::TextUnformatted("Hold an object in offline Forge to edit its coordinates.");return;}
 if(draft.generation!=view.generation||!draft.dirty){
  draft.generation=view.generation;draft.position=view.pose.position;draft.angles=view.angles;draft.dirty=false;
 }
 draft.dirty|=ImGui::InputFloat3("Position XYZ",draft.position.data(),"%.3f");
 draft.dirty|=ImGui::InputFloat3("Yaw / pitch / roll",draft.angles.data(),"%.1f");
 bool valid=true;
 for(float v:draft.position)valid&=std::isfinite(v)&&v>=-1000&&v<=1000;
 for(float v:draft.angles)valid&=std::isfinite(v)&&v>=-180&&v<=179;
 ImGui::BeginDisabled(!valid);
 if(ImGui::Button("Apply coordinates")){
  // Keep the draft until the guest consumes the request, rather than replacing
  // it with the preceding frame's snapshot while the command is pending.
  session.Queue(view,draft.position,draft.angles);
 }
 if(geometry){geometry->applyMin=ImGui::GetItemRectMin();geometry->applyMax=ImGui::GetItemRectMax();}
 ImGui::EndDisabled();
 if(!valid)ImGui::TextUnformatted("Position: -1000 to 1000. Angles: -180 to 179 degrees.");
 if(view.locked){
  ImGui::TextUnformatted("Coordinates held. Close this panel to place the object.");
  if(ImGui::Button("Resume free movement")){session.Queue(view,{}, {},true);draft.dirty=false;}
  if(geometry){geometry->resumeMin=ImGui::GetItemRectMin();geometry->resumeMax=ImGui::GetItemRectMax();}
 }
}
inline void DrawPhysics(PhysicsSession& session,PanelGeometry* geometry){
 auto view=session.Read();
 ImGui::Separator();ImGui::TextUnformatted("Physics while editing");
 if(!view.fresh()){ImGui::TextUnformatted("Hold a scenery object to change its physics.");return;}
 const PhysicsMode modes[]={PhysicsMode::Normal,PhysicsMode::Fixed,PhysicsMode::Phased};
 const char* names[]={"Normal","Fixed","Phased"};
 for(unsigned i=0;i<3;++i){
  if(i)ImGui::SameLine();
  if(ImGui::RadioButton(names[i],view.mode==modes[i]))session.Queue(view,modes[i]);
  if(geometry){geometry->physicsMin[i]=ImGui::GetItemRectMin();geometry->physicsMax[i]=ImGui::GetItemRectMax();}
 }
 ImGui::TextWrapped("Modes last until you return to player mode. Saved layouts use the object's original Halo 3 physics.");
}
// Historical host-panel prototype, retained for its isolated UI checks only.
// The production game no longer includes this header or registers this F7 UI.
inline void DrawControls(bool& visible,ControlState& state,const char* status,
                         uint64_t checks,uint64_t snaps,PanelGeometry* geometry=nullptr,
                         CoordinateSession* coordinates=nullptr,CoordinateDraft* draft=nullptr,
                         PhysicsSession* physics=nullptr){
 if(ImGui::IsKeyPressed(ImGuiKey_F7,false))visible=!visible;
 if(!visible)return;
 if(ImGui::Begin("Advanced Forge",&visible)){
  bool value=state.enabled.load();
  if(ImGui::Checkbox("Magnets (Halo 4)",&value))state.enabled=value;
  if(geometry){geometry->toggleMin=ImGui::GetItemRectMin();geometry->toggleMax=ImGui::GetItemRectMax();}
  static const char* levels[]={"Very low","Low","Medium","High","Very high"};
  int level=int(state.sensitivity.load());
  if(ImGui::SliderInt("Snap distance",&level,0,4,levels[level]))state.sensitivity=unsigned(level);
  if(geometry){geometry->sliderMin=ImGui::GetItemRectMin();geometry->sliderMax=ImGui::GetItemRectMax();}
  bool anchors=state.showAnchors.load();
  if(ImGui::Checkbox("Show anchors",&anchors))state.showAnchors=anchors;
  ImGui::TextUnformatted(value?status:"Off");
  ImGui::Text("Checks: %llu   Snaps: %llu",(unsigned long long)checks,(unsigned long long)snaps);
  ImGui::TextUnformatted("F7: show/hide. Offline Forge. Standard saved layouts.");
  if(coordinates&&draft)DrawCoordinates(*coordinates,*draft,geometry);
  if(physics)DrawPhysics(*physics,geometry);
 }ImGui::End();
}
}
