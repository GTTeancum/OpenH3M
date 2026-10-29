#include "video_quality.h"
#include <rex/cvar.h>

REXCVAR_DEFINE_INT32(halo3mp_shadow_quality, 0, "Video", "Dynamic shadows: 0 Original, 1 Medium, 2 Low").range(0, 2);
REXCVAR_DEFINE_INT32(halo3mp_decorator_quality, 0, "Video", "Decorative detail distance: 0 Original, 1 Medium, 2 Near").range(0, 2);
REXCVAR_DEFINE_INT32(halo3mp_object_quality, 0, "Video", "Object mesh detail: 0 Original, 1 Medium, 2 Low").range(0, 2);
REXCVAR_DEFINE_INT32(halo3mp_effect_quality, 0, "Video", "Cosmetic effect detail distance: 0 Original, 1 Medium, 2 Near").range(0, 2);
REXCVAR_DEFINE_INT32(halo3mp_water_quality, 0, "Video", "Water detail: 0 Original, 1 Reduced, 2 Basic").range(0, 2);

namespace spartan::video {
Quality ReadQuality() {
  Quality quality{};
  for (size_t i = 0; i < quality.size(); ++i)
    quality[i] = rex::cvar::Query<int32_t>(kQualityFlags[i]);
  return quality;
}
}
