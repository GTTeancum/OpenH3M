#pragma once
#include "forge_bridge.h"
#include <chrono>
#include <mutex>
#include <optional>

namespace advanced_forge {
// Commands cross threads as values. Runtime object pointers and saved variant
// memory never enter the UI. Release and selection changes invalidate commands.
class PhysicsSession {
public:
 struct View {
  uint64_t generation=0;
  uint32_t datum=0xffffffff;
  PhysicsMode mode=PhysicsMode::Normal;
  std::chrono::steady_clock::time_point updated{};
  bool fresh()const{return datum!=0xffffffff&&std::chrono::steady_clock::now()-updated<std::chrono::milliseconds(500);}
 };
 View Read(){std::lock_guard lock(mutex_);return view_;}
 bool Queue(const View& selected,PhysicsMode mode){
  std::lock_guard lock(mutex_);
  if(!view_.fresh()||selected.generation!=view_.generation||selected.datum!=view_.datum)return false;
  if(mode!=PhysicsMode::Normal&&mode!=PhysicsMode::Fixed&&mode!=PhysicsMode::Phased)return false;
  pending_=mode;return true;
 }
 std::optional<PhysicsMode> Update(uint32_t datum,PhysicsMode mode){
  std::lock_guard lock(mutex_);
  if(view_.datum!=datum){ResetLocked();view_.datum=datum;}
  view_.mode=mode;view_.updated=std::chrono::steady_clock::now();
  auto result=pending_;pending_.reset();return result;
 }
 void Publish(uint32_t datum,PhysicsMode mode){
  std::lock_guard lock(mutex_);
  if(view_.datum==datum){view_.mode=mode;view_.updated=std::chrono::steady_clock::now();}
 }
 void Reset(){std::lock_guard lock(mutex_);ResetLocked();}
private:
 void ResetLocked(){auto generation=view_.generation+1;view_={};view_.generation=generation;pending_.reset();}
 std::mutex mutex_;
 View view_;
 std::optional<PhysicsMode> pending_;
};
}
