#pragma once
#include "forge_bridge.h"
#include <chrono>
#include <mutex>
#include <optional>

namespace advanced_forge {
// UI and guest threads exchange values only. A generation prevents a queued
// edit from affecting a later selection, including release/re-grab of a datum.
class CoordinateSession {
public:
 struct View {
  uint64_t generation=0;
  uint32_t map=0,datum=0xffffffff;
  CoordinatePose pose;
  std::array<float,3> angles{};
  bool locked=false;
  std::chrono::steady_clock::time_point updated{};
  bool fresh()const{return datum!=0xffffffff&&std::chrono::steady_clock::now()-updated<std::chrono::milliseconds(500);}
 };
 View Read(){std::lock_guard lock(mutex_);return view_;}
 // Numeric menus may preview several choices before accepting one. Keep the
 // original lock state as well as its pose: cancelling Free must remain Free.
 bool BeginPreview(const View& selected){
  std::lock_guard lock(mutex_);
  if(!Matches(selected)||preview_)return false;
  preview_=view_;return true;
 }
 bool FinishPreview(const View& selected,bool accept){
  std::lock_guard lock(mutex_);
  if(!Matches(selected)||!preview_)return false;
  if(!accept){view_=*preview_;view_.updated=std::chrono::steady_clock::now();pending_.reset();}
  preview_.reset();return true;
 }
 bool Queue(const View& selected,std::array<float,3> position,std::array<float,3> angles,bool resume=false){
  std::lock_guard lock(mutex_);
  if(!Matches(selected))return false;
  pending_=Command{view_.generation,position,angles,resume};return true;
 }
 // Publish the actually constrained target so the menu does not display or
 // later reapply an out-of-bounds request. Preserve preview and lock state.
 bool ReconcilePose(const View& selected,const CoordinatePose& pose,Bridge& bridge){
  std::lock_guard lock(mutex_);
  if(!Matches(selected))return false;
  view_.pose=pose;view_.angles=bridge.CoordinateAngles(pose);
  view_.updated=std::chrono::steady_clock::now();return true;
 }
 // Event13 changes a target; it does not install a permanent drag lock.
 // Menu previews retain their target only until confirmation/cancellation.
 void FinishMenuEdit(){
  std::lock_guard lock(mutex_);view_.locked=false;pending_.reset();
 }
 bool Locked(){std::lock_guard lock(mutex_);return view_.locked;}
 void Reset(){std::lock_guard lock(mutex_);ResetLocked();}
 std::optional<CoordinatePose> Update(uint32_t map,uint32_t datum,const CoordinatePose& current,Bridge& bridge){
  std::lock_guard lock(mutex_);
  if(view_.datum!=datum||view_.map!=map){ResetLocked();view_.map=map;view_.datum=datum;}
  if(!view_.locked)view_.pose=current;
  if(pending_){
   const auto command=*pending_;pending_.reset();
   if(command.generation==view_.generation){
    if(command.resume){view_.locked=false;view_.pose=current;}
    else{view_.pose=bridge.EditCoordinates(datum,view_.pose,command.position,command.angles);view_.locked=true;}
   }
  }
  view_.angles=bridge.CoordinateAngles(view_.pose);
  view_.updated=std::chrono::steady_clock::now();
  return view_.locked?std::optional(view_.pose):std::nullopt;
 }
private:
 bool Matches(const View& selected)const{
  return view_.fresh()&&selected.generation==view_.generation&&selected.datum==view_.datum&&selected.map==view_.map;
 }
 struct Command {uint64_t generation;std::array<float,3> position,angles;bool resume;};
 void ResetLocked(){const auto generation=view_.generation+1;view_={};view_.generation=generation;pending_.reset();preview_.reset();}
 std::mutex mutex_;
 View view_;
 std::optional<Command> pending_;
 std::optional<View> preview_;
};
}
