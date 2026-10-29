#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace spartan::video {
// Retail H3 s_performance_throttles, verified against 8246F638/8246F990.
// Host representation; guest fields are converted explicitly at the hook.
struct Throttles {
  uint32_t flags;
  float water, decorators, effects, instances, object_fade, object_lod, decals;
  int32_t cpu_lights;
  float cpu_light_scale;
  int32_t gpu_lights;
  float gpu_light_scale;
  int32_t shadows;
  float shadow_lod;
};
static_assert(sizeof(Throttles) == 0x38);
inline constexpr std::array<const char*, 5> kQualityFlags = {
    "halo3mp_shadow_quality", "halo3mp_decorator_quality", "halo3mp_object_quality",
    "halo3mp_effect_quality", "halo3mp_water_quality"};
using Quality = std::array<int, 5>;
inline Throttles Apply(const Throttles& original, Quality quality) {
  for (auto& level : quality) level = std::clamp(level, 0, 2);
  Throttles result = original;
  constexpr float scale[] = {1.f, .75f, .5f};
  if (quality[0]) {
    if (original.shadows > 0)
      result.shadows = std::max(1, int(std::ceil(original.shadows * scale[quality[0]] * scale[quality[0]])));
    result.shadow_lod *= scale[quality[0]];
  }
  result.decorators *= scale[quality[1]];
  result.object_lod *= scale[quality[2]];
  result.effects *= scale[quality[3]];
  // Native water thresholds: >.66 both features; .33..66 one; <.33 neither.
  // Water shading and underwater fog remain enabled in all three modes.
  if (quality[4]) result.water = std::min(original.water, quality[4] == 1 ? .5f : 0.f);
  return result;
}
Quality ReadQuality();
}
