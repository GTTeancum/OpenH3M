#pragma once
#include <rex/graphics/scene_markers.h>
#include <memory>
#include <wrl/client.h>

namespace forge {
// Half the widest marker particle (ray burst at birth: 0.28 wu wide).
inline constexpr float kMarkerHalfSize = 0.14f;
// Compiles Spartan's own marker shader. Returns null on failure.
std::shared_ptr<const rex::graphics::SceneMarkerMaterial> BuildMarkerMaterial();
}
