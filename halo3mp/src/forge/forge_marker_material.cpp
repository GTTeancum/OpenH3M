// Spartan's own magnet-marker look, drawn procedurally from the description in
// tools/h4-forge/spec/07-marker-look.md (no Halo 4 shaders or textures).
//
// Each marker is two layers of camera-facing particles at the magnet point:
//  - a soft red/orange plasma ring (3 overlapping particles, a new one every
//    1/6 s, each living 0.5 s and flaring to full brightness at mid-life);
//  - a larger orange starburst of uneven rays (5 overlapping particles, a new
//    one every 0.1 s, each slowly spinning and shrinking).
// Sizes are world units; distance fades 0.40-0.61 wu (near) and 21-23 wu (far).
#include "forge_marker_material.h"
#include <d3dcompiler.h>
#include <rex/logging.h>
#include <cstring>
#include <string>

namespace forge {
namespace {
// Constant layout and bindings shared with the SDK's scene-marker renderer
// (rexglue-sdk src/graphics/d3d12/scene_markers.cpp): u0 output, t0 scene
// depth, b0 24 dwords. color = (seed, shown-since time, unused, half size).
constexpr const char* kMarkerShader = R"(
RWTexture2D<float4> target : register(u0);
#ifdef MULTISAMPLED
Texture2DMS<float> scene : register(t0);
#else
Texture2D<float> scene : register(t0);
#endif
cbuffer Marker : register(b0) {
  float2 center; float radius; float marker_depth;
  uint2 origin; uint2 output_size;
  float2 depth_scale; float2 depth_offset;
  float4 color;
  uint sample_mask; float epsilon; float elapsed; float view_depth;
  float4 depth_coverage;
};
static const float kPi = 3.14159265;

float Hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
float Hash1(float n) { return frac(sin(n * 12.9898) * 43758.5453); }

// Tiling value noise on an 8x8 lattice, four octaves: soft fractal clouds
// that repeat once across the sprite (spec 07 3.1).
float Cloud(float2 uv, float salt) {
  float sum = 0, amp = 0.5, norm = 0; float cells = 8;
  for (int o = 0; o < 4; ++o) {
    float2 p = frac(uv) * cells; float2 i = floor(p); float2 f = p - i;
    f = f * f * (3 - 2 * f);
    float a = Hash(fmod(i, cells) + salt), b = Hash(fmod(i + float2(1, 0), cells) + salt);
    float c = Hash(fmod(i + float2(0, 1), cells) + salt), d = Hash(fmod(i + float2(1, 1), cells) + salt);
    sum += amp * lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
    norm += amp; amp *= 0.5; cells *= 2; salt += 17.0;
  }
  return sum / norm;
}

// Palette strip, value 0..1 -> colour (spec 07 3.1 table).
float3 Palette(float u) {
  const float3 c0 = float3(123, 12, 0), c1 = float3(156, 16, 0), c2 = float3(206, 20, 0);
  const float3 c3 = float3(255, 28, 0), c4 = float3(255, 73, 0), c5 = float3(255, 130, 8);
  float3 c;
  if (u < 0.25) c = lerp(c0, c1, u / 0.25);
  else if (u < 0.5) c = lerp(c1, c2, (u - 0.25) / 0.25);
  else if (u < 0.75) c = lerp(c2, c3, (u - 0.5) / 0.25);
  else if (u < 0.875) c = lerp(c3, c4, (u - 0.75) / 0.125);
  else c = lerp(c4, c5, (u - 0.875) / 0.125);
  return c / 255.0;
}

// Ring mask: soft annulus, peak at 0.71 of the half-width, half brightness at
// 0.60 and 0.83, nothing inside 0.47 or outside 0.96 (spec 07 3.1).
float RingMask(float r) {
  float s = r < 0.71 ? 0.0934 : 0.1019;
  float g = exp(-0.5 * pow((r - 0.71) / s, 2));
  return g * saturate((r - 0.45) / 0.04) * saturate((0.97 - r) / 0.03);
}

// Starburst: about thirteen uneven tapered rays around a dark centre
// (spec 07 4.1). Radial peak 0.44, above half between 0.33 and 0.60.
float Rays(float2 q) {
  float r = length(q);
  float radial = exp(-0.5 * pow((r - 0.44) / (r < 0.44 ? 0.095 : 0.135), 2));
  radial *= saturate((r - 0.23) / 0.06) * saturate((0.92 - r) / 0.12);
  float angle = atan2(q.y, q.x);
  float total = 0;
  [unroll] for (int i = 0; i < 13; ++i) {
    // Our own fixed arrangement: irregular angles with two wider gaps.
    // Fifteen slots, two left empty (gaps of about 48 degrees).
    float slot = i + (i >= 7 ? 1 : 0) + (i >= 11 ? 1 : 0);
    float centreAngle = slot * 2 * kPi / 15 + (Hash1(i + 1.7) - 0.5) * 0.15;
    float width = radians(15.0 + 10.0 * Hash1(i + 9.1)) * 0.5;
    float strength = 0.55 + 0.45 * Hash1(i + 3.3);
    float d = abs(atan2(sin(angle - centreAngle), cos(angle - centreAngle)));
    total += strength * exp(-0.5 * pow(d / (width * 0.55), 2));
  }
  return radial * saturate(total) * 0.56;
}

float Triangle(float t, float peakT, float start, float peak, float finish) {
  return t < peakT ? lerp(start, peak, t / peakT) : lerp(peak, finish, (t - peakT) / (1 - peakT));
}

float3 MarkerLight(float2 world, float seed, float shown, float time) {
  float3 light = 0;
  // Plasma ring: lifespan 0.5 s, one particle per 1/6 s (spec 07 2.4, 3).
  const float ringPeriod = 1.0 / 6.0;
  float since = time - shown;
  for (int k = 0; k < 3; ++k) {
    float spawn = floor(since / ringPeriod) - k;
    if (spawn < 1) continue;
    float age = since - spawn * ringPeriod;
    if (age < 0 || age >= 0.5) continue;
    float t = age / 0.5;
    float width = lerp(0.30, 0.35, t) * lerp(0.50, 0.40, t) * 0.25;
    float2 q = world / (width * 0.5);
    float r = length(q);
    if (r > 1) continue;
    float h = Hash1(seed * 7.1 + spawn * 1.37);
    float rot = h * 2 * kPi;
    float2 pq = float2(cos(rot) * q.x - sin(rot) * q.y, sin(rot) * q.x + cos(rot) * q.y);
    if (Hash1(h * 91.7) > 0.5) pq.x = -pq.x;
    if (Hash1(h * 53.3) > 0.5) pq.y = -pq.y;
    float2 uv = pq * 0.5 + 0.5;
    float a = Cloud(uv + 0.5 * time, 0.0), b = Cloud(uv - 0.5 * time, 41.0);
    float plasma = abs(a - b);
    float alpha = t * 0.25;
    float m = RingMask(r) * alpha;
    float u = saturate((1 - m) + plasma);
    float intensity = Triangle(t, 0.48, 1.0, 29.9, 1.0) * Triangle(t, 0.5, 0.0, 0.99, 0.0);
    light += Palette(u) * intensity * m;
  }
  // Ray burst: lifespan 0.5 s, one particle per 0.1 s (spec 07 4).
  const float rayPeriod = 0.1;
  for (int j = 0; j < 5; ++j) {
    float spawn = floor(since / rayPeriod) - j;
    if (spawn < 1) continue;
    float age = since - spawn * rayPeriod;
    if (age < 0 || age >= 0.5) continue;
    float t = age / 0.5;
    float width = lerp(0.40, 0.20, t) * lerp(0.50, 0.40, t) * 1.4;
    float2 q = world / (width * 0.5);
    if (length(q) > 1) continue;
    float h = Hash1(seed * 3.3 + spawn * 2.11);
    float spin = 0.15 - 0.30 * Hash1(h * 17.9);
    float rot = 2 * kPi * (0.25 + Hash1(h * 5.7) + spin * age);
    float2 pq = float2(cos(rot) * q.x - sin(rot) * q.y, sin(rot) * q.x + cos(rot) * q.y);
    if (Hash1(h * 29.1) > 0.5) pq.x = -pq.x;
    float shape = Rays(pq);
    float3 tint = lerp(float3(255, 89, 35), float3(255, 92, 0), t) / 255.0;
    float flicker = 11.2 + 1.1 * sin(2 * kPi * (4.2 * t + 0.05)) * (0.8 + 0.2 * sin(2 * kPi * 9.0 * t));
    float intensity = flicker * Triangle(t, 0.5, 0.0, 0.133, 0.0);
    light += shape * tint * intensity;
  }
  // Distance fades along the view axis (spec 07 6).
  float fade = saturate((view_depth - 0.4032) / 0.2016) * saturate((23.0 - view_depth) / 2.0);
  return light * fade;
}

[numthreads(8,8,1)] void main(uint3 tid:SV_DispatchThreadID) {
  uint2 p = origin + tid.xy;
  if (any(p >= output_size)) return;
  float2 uv = (float2(p) + .5 - center) / (2 * radius) + .5;
  if (any(uv < 0) || any(uv > 1)) return;
  float2 depth_position = (float2(p) + .5) * depth_scale + depth_offset;
  uint depth_width, depth_height;
#ifdef MULTISAMPLED
  uint depth_samples;
  scene.GetDimensions(depth_width, depth_height, depth_samples);
#else
  scene.GetDimensions(depth_width, depth_height);
#endif
  if (any(!isfinite(depth_position)) || any(depth_position < 0) ||
      depth_position.x >= depth_width || depth_position.y >= depth_height) return;
  if (any(depth_position < depth_coverage.xy) || any(depth_position >= depth_coverage.zw)) return;
  int2 dp = int2(depth_position);
  float visible = 0;
#ifdef MULTISAMPLED
  uint used = 0;
  for (uint i = 0; i < depth_samples; ++i) if (sample_mask & (1u << i)) {
    visible += marker_depth + epsilon >= scene.Load(dp, i); ++used;
  }
  if (!used) return;
  visible /= used;
#else
  visible = marker_depth + epsilon >= scene.Load(int3(dp, 0));
#endif
  if (visible <= 0) return;
  float halfSize = color.w;
  float2 world = (uv - 0.5) * 2 * halfSize * float2(1, -1);
  float3 light = MarkerLight(world, color.x, color.y, elapsed) * visible;
  float4 old = target[p];
  target[p] = float4(saturate(old.rgb + light), old.a);
}
)";

std::vector<uint8_t> Compile(bool multisampled) {
  const D3D_SHADER_MACRO defines[] = {{"MULTISAMPLED", "1"}, {nullptr, nullptr}};
  Microsoft::WRL::ComPtr<ID3DBlob> code, errors;
  const HRESULT hr = D3DCompile(kMarkerShader, std::strlen(kMarkerShader), "forge_marker", multisampled ? defines : nullptr,
                                nullptr, "main", "cs_5_0", D3DCOMPILE_OPTIMIZATION_LEVEL3, 0, &code, &errors);
  if (FAILED(hr)) {
    REXLOG_ERROR("Forge marker shader failed to compile: {}",
                 errors ? std::string(static_cast<const char*>(errors->GetBufferPointer()), errors->GetBufferSize())
                        : std::string("unknown error"));
    return {};
  }
  const auto* bytes = static_cast<const uint8_t*>(code->GetBufferPointer());
  return std::vector<uint8_t>(bytes, bytes + code->GetBufferSize());
}
}  // namespace

std::shared_ptr<const rex::graphics::SceneMarkerMaterial> BuildMarkerMaterial() {
  auto material = std::make_shared<rex::graphics::SceneMarkerMaterial>();
  material->programs[0] = Compile(false);
  material->programs[1] = Compile(true);
  if (material->programs[0].empty() || material->programs[1].empty()) return nullptr;
  // The renderer requires a non-empty side buffer; this look uses none.
  material->pixels.assign(16, 0);
  return material;
}

}  // namespace forge
