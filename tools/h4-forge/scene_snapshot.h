#pragma once
#include "forge_bridge.h"
#include <fstream>
#include <stdexcept>

namespace advanced_forge {
// Private diagnostic format, never a Halo 3 map or saved-layout extension.
// Host scalar fields are little-endian; original marker records remain BE.
inline void SaveScene(const std::string& path,const Scene& scene){
 bool extended=scene.nearbyOrder.has_value()||scene.objects.size()>64;
 for(const auto& o:scene.objects)extended=extended||o.hasMagnetGroup.has_value();
 std::ofstream f(path,std::ios::binary|std::ios::trunc);
 auto put=[&](const auto& v){f.write(reinterpret_cast<const char*>(&v),sizeof(v));};
 f.write(extended?"AFS3":"AFS2",4);uint32_t count=static_cast<uint32_t>(scene.objects.size());
 put(count);put(scene.sensitivity);put(scene.cursor);put(scene.heldBasis);put(scene.processedMovement);
 for(const auto& o:scene.objects){
  put(o.datum);put(o.position);put(o.radius);
  count=static_cast<uint32_t>(o.markers.size());put(count);
  for(const auto& m:o.markers)put(m);
  if(extended){uint8_t group=o.hasMagnetGroup?(*o.hasMagnetGroup?1:0):2;put(group);}
 }
 if(extended){
  count=scene.nearbyOrder?static_cast<uint32_t>(scene.nearbyOrder->size()):0xffffffff;
  put(count);
  if(scene.nearbyOrder)for(auto index:*scene.nearbyOrder)put(index);
 }
 if(!f)throw std::runtime_error("Could not write Advanced Forge scene diagnostic");
}
inline Scene LoadScene(const std::string& path){
 std::ifstream f(path,std::ios::binary);Scene scene;
 auto get=[&](auto& v){f.read(reinterpret_cast<char*>(&v),sizeof(v));};
 char magic[4];f.read(magic,4);uint32_t count;get(count);
 if(!f)throw std::runtime_error("Truncated scene diagnostic header");
 const std::string version(magic,4);
 if((version!="AFS1"&&version!="AFS2"&&version!="AFS3")||!count||count>(version=="AFS3"?65u:64u))throw std::runtime_error("Invalid scene diagnostic");
 get(scene.sensitivity);get(scene.cursor);get(scene.heldBasis);
 if(version!="AFS1")get(scene.processedMovement);
 scene.objects.resize(count);
 for(auto& o:scene.objects){
  get(o.datum);get(o.position);get(o.radius);get(count);
  if(!f||count>32)throw std::runtime_error("Invalid diagnostic marker count");
  o.markers.resize(count);for(auto& m:o.markers)get(m);
  if(version=="AFS3"){
   uint8_t group=2;get(group);
   if(!f||group>2)throw std::runtime_error("Invalid diagnostic marker eligibility");
   if(group!=2)o.hasMagnetGroup=group==1;
  }
 }
 if(version=="AFS3"){
  get(count);
  if(!f||(count!=0xffffffff&&count>64))throw std::runtime_error("Invalid diagnostic query count");
  if(count!=0xffffffff){
   scene.nearbyOrder.emplace();scene.nearbyOrder->resize(count);
   std::vector<bool> seen(scene.objects.size(),false);
   for(auto& index:*scene.nearbyOrder){
    get(index);
    if(!f||index>=seen.size()||seen[index])throw std::runtime_error("Invalid diagnostic query index");
    seen[index]=true;
   }
  }
 }
 if(!f||f.peek()!=std::ifstream::traits_type::eof())throw std::runtime_error("Truncated/trailing scene diagnostic");
 return scene;
}
}
