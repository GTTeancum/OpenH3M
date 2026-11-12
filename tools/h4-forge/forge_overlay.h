#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <imgui.h>
#include <vector>

namespace advanced_forge {
struct AnchorCamera {
 std::array<float,3> position{},forward{},up{};
 float horizontalFov=0,aspect=0;
};
struct VisibleAnchor {std::array<float,3> position{};bool held=false;uint32_t datum=0xffffffff;};
// Rendering adapter only: marker selection/visibility remain original H4 code.
inline bool ProjectAnchor(const AnchorCamera& c,const std::array<float,3>& point,
                          ImVec2 size,ImVec2& screen){
 if(size.x<=0||size.y<=0||!std::isfinite(c.horizontalFov)||
    c.horizontalFov<=0||c.horizontalFov>=3.13f||!std::isfinite(c.aspect)||c.aspect<=0)return false;
 std::array<float,3> right{c.forward[1]*c.up[2]-c.forward[2]*c.up[1],
                         c.forward[2]*c.up[0]-c.forward[0]*c.up[2],
                         c.forward[0]*c.up[1]-c.forward[1]*c.up[0]};
 float depth=0,x=0,y=0;
 for(unsigned i=0;i<3;++i){
  const float d=point[i]-c.position[i];
  depth+=d*c.forward[i];x+=d*right[i];y+=d*c.up[i];
 }
 if(!std::isfinite(depth)||!std::isfinite(x)||!std::isfinite(y)||depth<=.01f)return false;
 const float extent=depth*std::tan(c.horizontalFov*.5f);
 x/=extent;y*=c.aspect/extent;
 if(std::abs(x)>1||std::abs(y)>1)return false;
 screen={(x+1)*size.x*.5f,(1-y)*size.y*.5f};return true;
}
}
