// Spartan Advanced Forge core: clean-room implementation of
// tools/h4-forge/ADVANCED-FORGE.md. See forge_core.h.
#include "forge_core.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace forge {
namespace {
constexpr float kEps = 1e-4f;
constexpr float kPi = 3.14159265358979323846f;
constexpr float kDegToRad = 0.017453292f;
constexpr float kRadToDeg = 57.29578f;
constexpr float kFltMax = std::numeric_limits<float>::max();
float Sign(float v) { return v > 0 ? 1.f : (v < 0 ? -1.f : 0.f); }
// Round half away from zero (truncate after adding +-0.5).
float RoundAway(float v) { return std::trunc(v + (v >= 0 ? 0.5f : -0.5f)); }
float Clamp(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
}  // namespace

// ------------------------------------------------------------------ Pose
std::array<float, 13> Pose::Packed() const {
  return {scale, forward[0], forward[1], forward[2], left[0], left[1], left[2],
          up[0], up[1], up[2], position[0], position[1], position[2]};
}
Pose Pose::Unpack(const std::array<float, 13>& v) {
  Pose p;
  p.scale = v[0];
  for (unsigned i = 0; i < 3; ++i) {
    p.forward[i] = v[1 + i]; p.left[i] = v[4 + i]; p.up[i] = v[7 + i]; p.position[i] = v[10 + i];
  }
  return p;
}
Basis Pose::GetBasis() const {
  return {forward[0], forward[1], forward[2], left[0], left[1], left[2], up[0], up[1], up[2]};
}
void Pose::SetBasis(const Basis& b) {
  for (unsigned i = 0; i < 3; ++i) { forward[i] = b[i]; left[i] = b[3 + i]; up[i] = b[6 + i]; }
}

// ------------------------------------------------------------------ maths
Vec3 Add(const Vec3& a, const Vec3& b) { return {a[0] + b[0], a[1] + b[1], a[2] + b[2]}; }
Vec3 Sub(const Vec3& a, const Vec3& b) { return {a[0] - b[0], a[1] - b[1], a[2] - b[2]}; }
Vec3 Mul(const Vec3& a, float s) { return {a[0] * s, a[1] * s, a[2] * s}; }
float Dot(const Vec3& a, const Vec3& b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
Vec3 Cross(const Vec3& a, const Vec3& b) {
  return {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]};
}
float Length(const Vec3& a) { return std::sqrt(Dot(a, a)); }
float Normalize(Vec3& v) {
  const float l = Length(v);
  if (std::abs(l) < kEps) return 0;
  v = Mul(v, 1.f / l);
  return l;
}
bool Limit(Vec3& v, float m) {
  const float l2 = Dot(v, v);
  if (l2 > m * m) { v = Mul(v, m / std::sqrt(l2)); return true; }
  return false;
}
Vec3 ClampBox(const Vec3& p, const std::array<float, 6>& b) {
  Vec3 r = p;
  for (unsigned i = 0; i < 3; ++i) {
    const float lo = b[i * 2], hi = b[i * 2 + 1];
    if (lo > p[i]) r[i] = lo;
    else if (hi < p[i]) r[i] = hi;
  }
  return r;
}

Quat QuatFromBasis(const Basis& b) {
  // Columns are forward, left, up: m[row][col].
  const float m00 = b[0], m10 = b[1], m20 = b[2];
  const float m01 = b[3], m11 = b[4], m21 = b[5];
  const float m02 = b[6], m12 = b[7], m22 = b[8];
  const float trace = m00 + m11 + m22;
  Quat q;
  if (trace > 0) {
    const float s = std::sqrt(trace + 1.f) * 2.f;
    q.w = 0.25f * s; q.x = (m21 - m12) / s; q.y = (m02 - m20) / s; q.z = (m10 - m01) / s;
  } else if (m00 > m11 && m00 > m22) {
    const float s = std::sqrt(1.f + m00 - m11 - m22) * 2.f;
    q.w = (m21 - m12) / s; q.x = 0.25f * s; q.y = (m01 + m10) / s; q.z = (m02 + m20) / s;
  } else if (m11 > m22) {
    const float s = std::sqrt(1.f + m11 - m00 - m22) * 2.f;
    q.w = (m02 - m20) / s; q.x = (m01 + m10) / s; q.y = 0.25f * s; q.z = (m12 + m21) / s;
  } else {
    const float s = std::sqrt(1.f + m22 - m00 - m11) * 2.f;
    q.w = (m10 - m01) / s; q.x = (m02 + m20) / s; q.y = (m12 + m21) / s; q.z = 0.25f * s;
  }
  return q;
}
Basis BasisFromQuat(const Quat& q) {
  const float n = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
  const float s = n > 0.0001f ? 2.f / n : 0.f;
  const float x = q.x, y = q.y, z = q.z, w = q.w;
  return {1 - s * (y * y + z * z), s * (x * y + w * z), s * (x * z - w * y),
          s * (x * y - w * z), 1 - s * (x * x + z * z), s * (y * z + w * x),
          s * (x * z + w * y), s * (y * z - w * x), 1 - s * (x * x + y * y)};
}
Quat QuatMul(const Quat& a, const Quat& b) {
  return {a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
          a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
          a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
          a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z};
}
Quat QuatNormalize(const Quat& q) {
  const float n = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
  if (!(n > 0)) return Quat{};
  const float l = std::sqrt(n);
  return {q.x / l, q.y / l, q.z / l, q.w / l};
}
Quat QuatConj(const Quat& q) { return {q.x, q.y, q.z, -q.w}; }
Vec3 QuatRotate(const Quat& q, const Vec3& v) {
  const Basis b = BasisFromQuat(q);
  return {b[0] * v[0] + b[3] * v[1] + b[6] * v[2], b[1] * v[0] + b[4] * v[1] + b[7] * v[2],
          b[2] * v[0] + b[5] * v[1] + b[8] * v[2]};
}
float QuatAngle(const Quat& a, const Quat& b) {
  const float d = Clamp(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w, -1.f, 1.f);
  return 2.f * std::acos(std::abs(d));
}
Vec3 QuatToEuler(const Quat& q, float epsilon) {
  const float x = q.x, y = q.y, z = q.z, w = q.w;
  const float n = x * x + y * y + z * z + w * w;
  const float t = z * x - y * w;
  float pitch = std::asin(Clamp(Clamp(2 * t, -1.f, 1.f) / n, -1.f, 1.f));
  float yaw, roll;
  if (std::abs(std::abs(t) - 0.5f) < epsilon) {
    roll = 0;
    yaw = 2.f * Sign(t) * std::atan2(x, w);
    pitch = Sign(t) * (kPi / 2);
  } else {
    roll = std::atan2(2 * (x * w + y * z), w * w - x * x - y * y + z * z);
    yaw = std::atan2(2 * (z * w + x * y), w * w + x * x - y * y - z * z);
  }
  return {yaw, pitch, roll};
}
Quat EulerToQuat(const Vec3& ypr) {
  const float A = ypr[0] * 0.5f, B = ypr[1] * 0.5f, C = ypr[2] * 0.5f;
  const float sA = std::sin(A), cA = std::cos(A), sB = std::sin(B), cB = std::cos(B);
  const float sC = std::sin(C), cC = std::cos(C);
  return {cB * cA * sC + sB * sA * cC, sC * cB * sA - cC * sB * cA,
          cC * cB * sA + sC * sB * cA, cB * cA * cC - sB * sA * sC};
}
Vec3 EulerFromBasis(const Vec3& forward, const Vec3& up) {
  const Vec3 left = Cross(up, forward);
  const double pitch = -std::asin(double(Clamp(up[0], -1.f, 1.f)));
  const double c = std::cos(pitch);
  double yaw, roll;
  if (c > 0.0001) {
    roll = std::atan2(-double(up[1]) / c, double(up[2]) / c);
    yaw = std::atan2(-double(left[0]) / c, double(forward[0]) / c);
  } else {
    roll = 0;
    yaw = std::atan2(double(forward[1]), double(left[1]));
  }
  return {float(yaw), float(pitch), float(roll)};
}
void BasisFromEuler(const Vec3& ypr, Vec3& forward, Vec3& up) {
  const float sy = std::sin(ypr[0]), cy = std::cos(ypr[0]);
  const float sp = std::sin(ypr[1]), cp = std::cos(ypr[1]);
  const float sr = std::sin(ypr[2]), cr = std::cos(ypr[2]);
  forward = {cy * cp, sy * cr - cy * sp * sr, cy * sp * cr + sy * sr};
  up = {-sp, -cp * sr, cp * cr};
}
Vec3 RotateAbout(const Vec3& v, const Vec3& a, float s, float c) {
  // v cos + (a x v) sin + a (a.v)(1 - cos)
  const Vec3 axv = Cross(a, v);
  const float d = Dot(a, v) * (1 - c);
  return {v[0] * c + axv[0] * s + a[0] * d, v[1] * c + axv[1] * s + a[1] * d,
          v[2] * c + axv[2] * s + a[2] * d};
}
Vec3 Apply(const Pose& t, const Vec3& p) {
  Vec3 r = t.position;
  for (unsigned i = 0; i < 3; ++i)
    r[i] += t.scale * (p[0] * t.forward[i] + p[1] * t.left[i] + p[2] * t.up[i]);
  return r;
}
Pose Compose(const Pose& a, const Pose& b) {
  Pose r;
  r.scale = a.scale * b.scale;
  auto rot = [&](const Vec3& v) {
    return Vec3{v[0] * a.forward[0] + v[1] * a.left[0] + v[2] * a.up[0],
                v[0] * a.forward[1] + v[1] * a.left[1] + v[2] * a.up[1],
                v[0] * a.forward[2] + v[1] * a.left[2] + v[2] * a.up[2]};
  };
  r.forward = rot(b.forward); r.left = rot(b.left); r.up = rot(b.up);
  r.position = Apply(a, b.position);
  return r;
}

// ------------------------------------------------------------------ markers
std::vector<Marker> BuildMarkers(const MagnetTable& table, const Pose& node) {
  std::vector<Marker> result;
  const uint32_t count = std::min<uint32_t>(table.count, tuning::kMaxMarkers);
  result.reserve(count);
  for (uint32_t i = 0; i < count; ++i) {
    const auto& m = table.magnets[i];
    Pose local;
    local.forward = m.forward; local.up = m.up; local.left = Cross(m.up, m.forward);
    local.position = m.position;
    const Pose world = Compose(node, local);
    Marker out;
    out.localBasis = local.GetBasis();
    out.localPosition = local.position;
    out.worldBasis = world.GetBasis();
    out.worldPosition = world.position;
    result.push_back(out);
  }
  return result;
}

// ------------------------------------------------------------------ editor
void InitializeEditor(Editor& e) {
  // 03 1.2: only these fields; aimPoint, pose, origin are left as they were.
  e.held = e.magnetTarget = e.aimed = kNone;
  e.holdDistance = tuning::kDefaultFocalDistance;
  e.leash = e.offsetScale = e.offsetDecay = e.pitchHistory = 0;
  e.grabOffset = {}; e.contactPoint = {};
  e.focusOutside = e.rotated = e.magnetsEnabled = false;
  e.rotationSnapMode = 0;
  e.obstruction = ObstructionState{};
  e.sensitivity = tuning::kDefaultSensitivity;
}

std::array<float, 2> ShapeInput(InputState& s, const InputFrame& f) {
  if (!f.eligible || !(f.trigger > tuning::kTriggerThreshold)) {
    s.active = false;
    return {f.forward, f.left};
  }
  if (f.rotationAvailable) {
    if (std::abs(f.lookA) > std::abs(f.lookB)) { s.yaw = f.lookA; s.pitch = 0; }
    else { s.yaw = 0; s.pitch = f.lookB; }
  }
  s.active = true;
  if (std::abs(f.forward) > std::abs(f.left)) { s.distance = f.forward; s.roll = 0; }
  else { s.distance = 0; s.roll = f.left; }
  return {0.f, 0.f};
}

float EvaluateCurve(const ravine::CurveSegment* seg, unsigned count, float x) {
  unsigned i = 0;
  while (i + 1 < count && !(x <= seg[i].end)) ++i;
  const auto& s = seg[i];
  float y = ((s.a * x + s.b) * x + s.c) * x + s.d;
  return Clamp(y, 0.f, 1.f);
}
namespace {
// Stage B (04 1.2): axial dead zone per axis, then the radial one.
void DeadZones(int16_t rawX, int16_t rawY, float& x, float& y) {
  const float D = float(ravine::kStickDeadZone);
  auto axial = [&](int16_t v) -> float {
    if (v > D) return std::trunc((float(v) - D) * 32767.f / (32767.f - D));
    if (v < -D) return std::trunc((float(v) + D) * 32768.f / (32768.f - D));
    return 0.f;
  };
  x = axial(rawX); y = axial(rawY);
  const float angle = std::atan2(y, x);
  float m = std::min(std::sqrt(x * x + y * y), 32767.f);
  if (m <= D) { x = y = 0; return; }
  m = (m - D) * 32767.f / (32767.f - D);
  x = std::cos(angle) * m; y = std::sin(angle) * m;
}
void Curve(float& x, float& y, const ravine::CurveSegment* seg, unsigned count, bool squareToCircle) {
  const float m = std::sqrt(x * x + y * y);
  if (m > 0) {
    const float out = EvaluateCurve(seg, count, m);
    x = x / m * out; y = y / m * out;
  }
  if (squareToCircle && std::abs(x) > 0.0001f && std::abs(y) > 0.0001f) {
    const float big = std::max(std::abs(x), std::abs(y)), small = std::min(std::abs(x), std::abs(y));
    const float k = std::sqrt(1.f + (small / big) * (small / big));
    x = Clamp(x * k, -1.f, 1.f); y = Clamp(y * k, -1.f, 1.f);
  }
}
}  // namespace
ProcessedSticks ProcessSticks(const RawSticks& raw) {
  float lx, ly, rx, ry;
  DeadZones(raw.lx, raw.ly, lx, ly);
  DeadZones(raw.rx, raw.ry, rx, ry);
  lx = Clamp(lx / 32767.f, -1.f, 1.f); ly = Clamp(ly / 32767.f, -1.f, 1.f);
  rx = Clamp(rx / 32767.f, -1.f, 1.f); ry = Clamp(ry / 32767.f, -1.f, 1.f);
  Curve(lx, ly, ravine::kLeftStickCurve, 1, false);   // left: type 1, no correction
  Curve(rx, ry, ravine::kRightStickCurve, 2, true);   // right: type 2, square-to-circle
  ProcessedSticks out;
  out.forward = ly; out.left = -lx;   // movement (Ly, -Lx)
  out.lookA = -rx; out.lookB = ry;    // look (-Rx, Ry), no inversion
  out.trigger = raw.rt / 255.f;       // first trigger analog, default layout RT
  return out;
}

VisibilityChange UpdateVisibility(const Editor& e, uint32_t priorHeld, uint32_t priorTarget) {
  VisibilityChange v;
  if (e.magnetsEnabled) {
    if (e.magnetTarget != priorTarget) {
      if (priorTarget != kNone) v.hide.push_back(priorTarget);
      if (e.magnetTarget != kNone) v.show.push_back(e.magnetTarget);
    }
    if (e.held != priorHeld) {
      if (priorHeld != kNone) v.hide.push_back(priorHeld);
      if (e.held != kNone) v.show.push_back(e.held);
    }
  } else {
    for (uint32_t d : {priorHeld, e.held, priorTarget, e.magnetTarget})
      if (d != kNone) v.hide.push_back(d);
  }
  return v;
}

VisibilityChange SelectHeld(Editor& e, uint32_t newHeld, const SelectionWorld& w) {
  const uint32_t priorHeld = e.held, priorTarget = e.magnetTarget;
  if (priorHeld != newHeld && newHeld == kNone) {
    e.held = e.magnetTarget = e.aimed = kNone;
    e.pitchHistory = 0;
    e.holdDistance = tuning::kDefaultFocalDistance;
    e.leash = e.offsetScale = e.offsetDecay = 0;
    e.grabOffset = {}; e.contactPoint = {};
    e.focusOutside = false; e.rotated = false;
    e.obstruction = ObstructionState{};
  }
  e.held = newHeld;
  if (newHeld != kNone && w.origin) e.heldOrigin = w.origin(newHeld);
  e.restoreFlag = false;
  e.rotated = false;
  VisibilityChange v;
  if (w.localPlayer) {
    v = UpdateVisibility(e, priorHeld, priorTarget);
    if (newHeld != kNone && w.physicsPoint) {
      Vec3 p = Add(w.physicsPoint(newHeld), Mul(e.grabOffset, e.offsetScale));
      if (w.monitor != kNone) {
        Vec3 d = Sub(p, w.physicsPoint(w.monitor));
        Normalize(d);
        e.pitchHistory = d[2];
      }
    }
  }
  return v;
}

VisibilityChange SetMagnetTarget(Editor& e, uint32_t target, bool localPlayer) {
  const uint32_t priorHeld = e.held, priorTarget = e.magnetTarget;
  e.magnetTarget = target;
  if (!localPlayer) return {};
  return UpdateVisibility(e, priorHeld, priorTarget);
}

bool ObjectDeleted(Editor& e, uint32_t datum, const SelectionWorld& w, VisibilityChange& v) {
  bool released = false;
  if (e.aimed == datum) e.aimed = kNone;
  if (e.held == datum) {
    auto change = SelectHeld(e, kNone, w);
    v.hide.insert(v.hide.end(), change.hide.begin(), change.hide.end());
    v.show.insert(v.show.end(), change.show.begin(), change.show.end());
    released = true;
  }
  if (e.magnetTarget == datum) {
    auto change = SetMagnetTarget(e, kNone, w.localPlayer);
    v.hide.insert(v.hide.end(), change.hide.begin(), change.hide.end());
    v.show.insert(v.show.end(), change.show.begin(), change.show.end());
  }
  return released;
}

float ClampHoldDistance(const Editor&, const InputState& in, float d, bool held, float r) {
  if (!held) return tuning::kDefaultFocalDistance;
  if (in.active) d = std::fma(-in.distance, tuning::kPushPullRate, d);
  const float a = r * 1.25f, b = r + 0.4f;
  const float lower = a - b >= 0 ? a : b;
  const float upperCandidate = tuning::kFocalDistanceMultiplier * lower;
  const float upper = upperCandidate - tuning::kMaximumFocalDistance >= 0 ? tuning::kMaximumFocalDistance
                                                                          : upperCandidate;
  // min(max(d, L), U); NaN d selects L.
  const float inner = (d - lower >= 0) ? d : lower;
  return (inner - upper >= 0) ? upper : inner;
}

// ------------------------------------------------------------------ rotation
bool RotationAllowed(const RotationGate& g) {
  if (!g.typeAllowed || !g.connected || !g.hasInstance) return false;
  for (bool fixed : g.bodyFixed)
    if (fixed || g.instanceBlocked) return false;
  return true;
}

bool RotateHeld(Editor& e, const InputState& in, const Vec3& monitorView, float dt,
                const RotationGate& gate) {
  bool result = false;
  if (in.active && e.held != kNone && RotationAllowed(gate)) {
    Vec3 v = monitorView;
    Normalize(v);
    const Vec3 yawAxis{0, 0, -1};
    Vec3 pitchAxis = Cross(Vec3{0, 0, 1}, v);
    Normalize(pitchAxis);
    const auto shape = [](float x) { return x * std::abs(x) * tuning::kRotationGain; };
    const float yaw = in.yaw, pitch = in.pitch, roll = -in.roll;
    Vec3 w = Add(Add(Mul(yawAxis, shape(yaw)), Mul(pitchAxis, shape(pitch))), Mul(v, shape(roll)));
    const float length = Normalize(w);
    const float theta = length * dt;
    if (theta > 0.0001f) {
      const float s = std::sin(theta), c = std::cos(theta);
      e.target.forward = RotateAbout(e.target.forward, w, s, c);
      e.target.left = RotateAbout(e.target.left, w, s, c);
      e.target.up = RotateAbout(e.target.up, w, s, c);
      result = true;
    }
  }
  e.rotated = e.rotated || result;
  if (result && e.offsetDecay == 0) e.offsetDecay = dt * 5.0f;
  return result;
}

void QuantizeOrientation(Pose& s, float step) {
  const Vec3 angles = EulerFromBasis(s.forward, s.up);
  Vec3 q{};
  const float inv = 1.f / step;
  for (unsigned i = 0; i < 3; ++i) {
    const float v = angles[i] * inv;
    q[i] = std::trunc(v + (v >= 0 ? 0.5f : -0.5f)) * step;
  }
  BasisFromEuler(q, s.forward, s.up);
  s.left = Cross(s.up, s.forward);
}

// ------------------------------------------------------------------ magnets
Vec3 MagnetReferencePoint(const Editor& e, const Vec3& p) {
  Vec3 r;
  for (unsigned i = 0; i < 3; ++i) r[i] = std::fma(e.grabOffset[i], e.offsetScale, p[i]);
  return r;
}

namespace {
float Distance2YZX(const Vec3& a, const Vec3& b) {
  const float dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2];
  return std::fma(dx, dx, std::fma(dz, dz, dy * dy));
}
void Thresholds(const Editor& e, float radiusBase, float& R, float& theta) {
  const unsigned k = e.sensitivity;
  R = k <= 4 ? tuning::kSnapRadiusFactor[k] * radiusBase : radiusBase;
  theta = tuning::kMagnetAngleDegrees * kDegToRad;
}
Quat TargetRotation(const Editor& e) {
  Basis basis = e.target.GetBasis();
  if (e.rotationSnapMode != 0 && e.rotated) basis = e.snappedBasis;
  const Quat held = QuatFromBasis(basis);
  return QuatNormalize(EulerToQuat(QuatToEuler(held, 0.0001f)));
}
}  // namespace

void AlignMagnet(const Editor& e, const Marker& h, const Marker& c, Quat& rotation, Vec3& position) {
  // 01 4.1 face-to-face rotation is computed and discarded by the original;
  // it has no effect on any output and is not reproduced.
  rotation = TargetRotation(e);
  position = Sub(c.worldPosition, QuatRotate(rotation, h.localPosition));
}

MagnetPair FindMagnetCandidate(const Editor& e, const MagnetWorld& w) {
  MagnetPair out;
  if (!w.held || w.held->markers.empty()) return out;
  float R, theta;
  Thresholds(e, w.held->radius, R, theta);
  const Vec3 ref = MagnetReferencePoint(e, w.heldPhysicsPoint);
  const float offset = std::sqrt(Distance2YZX(w.heldPhysicsPoint, ref));
  const float queryRadius = w.held->radius + offset;
  const auto nearby = w.nearby ? w.nearby(w.heldPhysicsPoint, queryRadius) : std::vector<MagnetObject>{};
  if (nearby.empty()) return out;
  const Quat qTarget = TargetRotation(e);
  float bestScore = -kFltMax, bestCentre = kFltMax;
  const float weight = tuning::kMagnetOffsetWeight;
  for (const auto& candidate : nearby) {
    if (!candidate.hasGroup) continue;
    if (candidate.datum == w.held->datum) continue;
    // 01 3.2 best pair for this candidate.
    float score = -kFltMax;
    const Marker* bestH = nullptr; const Marker* bestC = nullptr;
    for (const auto& h : w.held->markers) {
      float a = Distance2YZX(h.localPosition, ref);
      const Quat qActual = QuatMul(QuatNormalize(QuatFromBasis(h.worldBasis)),
                                   QuatNormalize(QuatConj(QuatFromBasis(h.localBasis))));
      const float angle = 2.f * std::acos(std::abs(Clamp(
          qActual.x * qTarget.x + qActual.y * qTarget.y + qActual.z * qTarget.z + qActual.w * qTarget.w,
          -1.f, 1.f)));
      for (const auto& c : candidate.markers) {
        const float pair = Distance2YZX(c.worldPosition, h.worldPosition);
        if (!(angle < theta) || !(pair < R * R)) continue;
        a = a + 0.0001f;
        const float b = pair + 0.0001f;
        const float s = weight / a + (1 - weight) / b;
        if (s > score) { score = s; bestH = &h; bestC = &c; }
      }
    }
    float d2 = kFltMax;
    if (bestH && bestC) d2 = Distance2YZX(bestH->worldPosition, bestC->worldPosition);
    if (score > bestScore && d2 < R * R) {
      bestScore = score;
      out.heldMarker = *bestH; out.candidateMarker = *bestC;
      out.candidate = candidate.datum;
      out.state = 2;
    } else if (out.state != 2) {
      const float c2 = Distance2YZX(candidate.center, w.held->center);
      if (c2 < bestCentre) { bestCentre = c2; out.candidate = candidate.datum; out.state = 1; }
    }
  }
  return out;
}

MagnetPair MagnetStep(const Editor& e, const MagnetWorld& w, Pose& S, bool& snapped) {
  snapped = false;
  const MagnetPair pair = FindMagnetCandidate(e, w);
  if (pair.state != 2) return pair;
  const Vec3& v = w.processedMovement;
  // |v| accumulated y first, then x and z (01 5.2 step 4).
  const float length = std::sqrt(std::fma(v[2], v[2], std::fma(v[0], v[0], v[1] * v[1])));
  if (length > tuning::kMagnetMovementThreshold) return pair;
  Quat rotation; Vec3 position;
  AlignMagnet(e, pair.heldMarker, pair.candidateMarker, rotation, position);
  S.SetBasis(BasisFromQuat(rotation));
  S.position = position;
  snapped = true;
  return pair;
}

// ------------------------------------------------------------------ contacts
namespace {
float PointSegmentDistance2(const Vec3& p, const Vec3& a, const Vec3& b, bool& inside) {
  const Vec3 ab = Sub(b, a);
  const float l2 = Dot(ab, ab);
  inside = false;
  if (l2 <= 0) return Dot(Sub(p, a), Sub(p, a));
  const float t = Dot(Sub(p, a), ab) / l2;
  if (t < 0 || t > 1) return kFltMax;
  inside = true;
  const Vec3 q = Add(a, Mul(ab, t));
  return Dot(Sub(p, q), Sub(p, q));
}
bool Adjacent(const ContactSet& set, int i) {
  if (i == set.primary) return true;
  const Vec3& pc = set.samples[set.primary].closestPoint;
  const auto& s = set.samples[i];
  constexpr float kAdj = 0.0025f;
  for (const auto& v : s.triangle)
    if (Dot(Sub(pc, v), Sub(pc, v)) < kAdj) return true;
  if (Dot(Sub(pc, s.closestPoint), Sub(pc, s.closestPoint)) < kAdj) return true;
  for (unsigned k = 0; k < 3; ++k) {
    bool inside;
    const float d = PointSegmentDistance2(pc, s.triangle[k], s.triangle[(k + 1) % 3], inside);
    if (inside && d < kAdj) return true;
  }
  return false;
}
}  // namespace

ContactSelection SelectContactPlanes(const ContactSet& set, const Vec3& P, bool reverse) {
  ContactSelection r;
  const int p = set.primary;
  if (p < 0 || p >= int(set.samples.size())) return r;
  const float band = set.closestDistance + 0.1f;
  std::vector<int> candidates;
  bool eligible = false;
  for (int i = 0; i < int(set.samples.size()); ++i) {
    if (!(set.samples[i].closestDistance < band) || !Adjacent(set, i)) continue;
    candidates.push_back(i);
    if (set.samples[i].planeDistance < 0) eligible = true;
  }
  if (!eligible) return r;
  Vec3 dir = Sub(P, set.samples[p].closestPoint);
  if (reverse) dir = Mul(dir, -1.f);
  if (Normalize(dir) == 0) return r;
  Vec3 w = dir;
  std::vector<int> picks;
  for (unsigned round = 0; round < 3; ++round) {
    int best = -1; float bestDot = -0.001f;
    for (int i : candidates) {
      const float d = Dot(set.samples[i].normal, w);
      if (d < bestDot) { bestDot = d; best = i; }
    }
    if (best < 0) break;
    picks.push_back(best);
    if (picks.size() == 1) {
      const Vec3& n1 = set.samples[best].normal;
      w = Sub(dir, Mul(n1, Dot(n1, dir)));
    } else if (picks.size() == 2) {
      Vec3 e = Cross(set.samples[picks[0]].normal, set.samples[picks[1]].normal);
      Normalize(e);
      w = Mul(e, Dot(e, dir));
    }
  }
  if (picks.empty()) return r;
  r.distance = set.samples[picks[0]].closestDistance;
  r.count = int(picks.size());
  int m = picks[0];
  for (int i : picks)
    if (Dot(set.samples[i].normal, dir) < Dot(set.samples[m].normal, dir)) m = i;
  Vec3 normal = set.samples[m].normal;
  if (picks.size() >= 2) {
    Vec3 c = Cross(set.samples[picks[0]].normal, set.samples[picks[1]].normal);
    Normalize(c);
    normal = Sub(normal, Mul(c, Dot(c, normal)));
    if (picks.size() == 3) {
      Vec3 k = Cross(normal, set.samples[picks[2]].normal);
      Normalize(k);
      normal = Sub(normal, Mul(k, Dot(k, normal)));
    }
  }
  if (Normalize(normal) == 0) {
    normal = Sub(set.samples[p].closestPoint, P);
    Normalize(normal);
  }
  r.normal = normal;
  r.normalWritten = true;
  r.residual = Dot(w, w);
  r.ok = Dot(normal, dir) < -0.001f;
  return r;
}

ContactResult ResolveContact(const ContactInput& in, const Vec3& cachedPoint) {
  ContactResult out;
  out.cachedPoint = cachedPoint;
  out.velocity = in.velocity;
  if (in.optOut) return out;
  const Vec3 P = in.physicsPoint, v = in.velocity;
  const float sweep = 2.f * std::max(Length(Sub(P, cachedPoint)), Length(v) * in.dt);
  out.cachedPoint = P;
  const float cap = in.biped ? 6.f : 10.f;
  const float base = in.previouslyActive ? cap : (in.biped ? 1.f : 3.f);
  const float range = std::min(std::max(base, sweep), cap);
  if (!in.collect) return out;
  const ContactSet set = in.collect(P, in.objectRadius, range);
  out.collectorFlags = set.flags;
  if (set.samples.empty()) return out;
  const auto forward = SelectContactPlanes(set, P, false);
  if (forward.normalWritten) out.normal = forward.normal;
  if (!forward.ok) return out;
  const auto reverse = SelectContactPlanes(set, P, true);
  if (reverse.ok && forward.count <= reverse.count && forward.residual >= reverse.residual) return out;
  float k, cn, ct;
  if (in.biped) { k = tuning::kBipedContact[0]; cn = tuning::kBipedContact[1]; ct = tuning::kBipedContact[2]; }
  else { k = tuning::kObjectContact[0]; cn = tuning::kObjectContact[1]; ct = tuning::kObjectContact[2]; }
  const Vec3 n = forward.normal;
  const Vec3 v1 = Add(v, Mul(n, k * forward.distance * in.dt));
  const Vec3 vn = Mul(n, Dot(n, v1));
  const Vec3 vt = Sub(v1, vn);
  float tangent = ct;
  if (in.biped && !(Length(vt) >= tuning::kBipedContact[3])) tangent = 0;
  out.velocity = Add(Mul(vt, 1 - tangent * in.dt), Mul(vn, 1 - cn * in.dt));
  out.contact = true;
  return out;
}

// ------------------------------------------------------------------ body drive
BodyCommand DriveBody(const Pose& target, float tau, const BodyState& body) {
  BodyCommand cmd;
  const float g = 1.f / tau;
  const Vec3 vk = Mul(Sub(target.position, body.position), g);
  const Quat qt = QuatFromBasis(target.GetBasis());
  const Quat& qc = body.orientation;
  Quat qr;
  const Vec3 qtv{qt.x, qt.y, qt.z}, qcv{qc.x, qc.y, qc.z};
  const Vec3 cr = Cross(qcv, qtv);
  qr.x = qc.w * qt.x - qt.w * qc.x + cr[0];
  qr.y = qc.w * qt.y - qt.w * qc.y + cr[1];
  qr.z = qc.w * qt.z - qt.w * qc.z + cr[2];
  qr.w = qt.x * qc.x + qt.y * qc.y + qt.z * qc.z + qt.w * qc.w;
  Vec3 wk{};
  Vec3 axis{qr.x, qr.y, qr.z};
  if (Dot(axis, axis) > 1.42108547e-14f) {
    const float l = Length(axis);
    axis = Mul(axis, 1.f / l);
    const float aw = std::abs(qr.w);
    const float angle = aw < 1.f ? 2.f * std::acos(aw) : 0.f;
    if (qr.w < 0) axis = Mul(axis, -1.f);
    wk = Mul(axis, angle * g);
  }
  // Net controller result with these gains: v' = vk, w' = wk (02 4.2 5).
  for (unsigned i = 0; i < 3; ++i) {
    if (std::abs(wk[i] - body.angularVelocity[i]) > 1e-5f) cmd.setAngular = true;
    if (std::abs(vk[i] - body.linearVelocity[i]) > 1e-5f) cmd.setLinear = true;
  }
  cmd.angular = wk; cmd.linear = vk;
  return cmd;
}
Pose FlattenBipedTarget(const Pose& target, Vec3& flattened) {
  Vec3 f = target.forward;
  f[2] = 0;
  if (Normalize(f) == 0) f = {1, 0, 0};
  flattened = f;
  Pose out = target;
  out.forward = {1, 0, 0}; out.left = {0, 1, 0}; out.up = {0, 0, 1};
  return out;
}

// ------------------------------------------------------------------ camera
float SpecArcsine(double t) {
  if (t == 0) return 0.f;
  static constexpr double p[5] = {-27.368494524164255, 57.20822787789173, -39.68886299750488,
                                  10.152522233806463, -0.6967457344735065};
  static constexpr double q[5] = {-164.2109671449856, 417.14430248260413, -381.8630336175015,
                                  150.95270841030606, -23.823859153670238};
  const double at = std::abs(t);
  double g, y, base;
  if (at <= 0.5) { g = t * t; y = at; base = 0; }
  else { g = (1 - at) * 0.5; y = -2 * std::sqrt(g); base = 1.5707963267948966; }
  const double P = (((p[4] * g + p[3]) * g + p[2]) * g + p[1]) * g + p[0];
  const double Q = ((((g + q[4]) * g + q[3]) * g + q[2]) * g + q[1]) * g + q[0];
  double r = base + y + y * g * P / Q;
  if (t < 0) r = -r;
  return float(r);
}
float PitchCurve(float x) {
  float a, b, c, e;
  if (x <= 0.50134998f) { a = 3.9627557f; b = -1.9867272f; c = -1.0f; e = 1.0f; }
  else { a = 8.0274725f; b = -18.074102f; c = 12.065789f; e = -2.0191586f; }
  const float x2 = x * x, cx = c * x, x3 = x2 * x;
  float t = std::fma(b, x2, cx);
  t = std::fma(x3, a, t);
  float y = t + e;
  if (y <= 0) y = 0;
  else if (!(y < 1)) y = 1;
  return std::fma(2.f, y, -1.f);
}
namespace {
Vec3 ViewUp(const Vec3& f) {
  Vec3 s{f[1], -f[0], 0};
  if (Normalize(s) == 0) s = {1, 0, 0};
  return Cross(s, f);
}
Vec3 HeldAnchorPoint(const Editor& e, const CameraInput& in, bool predict) {
  Vec3 H = MagnetReferencePoint(e, in.heldPhysicsPoint);
  if (predict) {
    const float p = Length(in.linearVelocity) * in.dt;
    float k;
    if (p <= 0.001f) k = 0;
    else k = std::min(1.f, Length(Sub(e.heldOrigin, in.heldOriginNow)) / p);
    H = Add(H, Mul(in.linearVelocity, k * in.dt));
    if (in.hasBody) {
      const Vec3 cw = QuatRotate(in.heldOrientation, in.firstBodyLocalCenter);
      Vec3 axis = in.angularVelocity;
      const float w = Normalize(axis);
      const float angle = w * in.dt;
      const Vec3 rotated = RotateAbout(cw, axis, std::sin(angle), std::cos(angle));
      H = Add(H, Sub(rotated, cw));
    }
  }
  return H;
}
}  // namespace
CameraPoint HeldCamera(const Editor& e, const CameraInput& in) {
  CameraPoint out;
  Vec3 H = HeldAnchorPoint(e, in, in.predict);
  const Vec3 D = in.view;
  const float z = Clamp(D[2] - e.pitchHistory, -1.f, 1.f);
  const float a = SpecArcsine(z);
  float x = (1.5707964f - a) * 0.31830987f;
  x = Clamp(x, 0.f, 1.f);
  const float lift = PitchCurve(x) * in.definitionRadius;
  const Vec3 up = ViewUp(D);
  out.focus = Add(H, Mul(up, lift));
  out.point = Sub(out.focus, Mul(D, e.holdDistance));
  out.view = D;
  out.distance = e.holdDistance;
  return out;
}
Vec3 LeashCorrection(const Editor& e, const CameraInput& anchor, const Vec3& U) {
  CameraInput mode0 = anchor;
  mode0.predict = false;
  const Vec3 A = HeldCamera(e, mode0).focus;
  const Vec3 d = Sub(U, A);
  const float r = Length(d);
  const float excess = r - e.leash;
  if (excess > 1.f) return Mul(d, excess / r);
  return {};
}

namespace {
void ObstructionTarget(const FollowWorld& w, ObstructionState& st, const Vec3& A, const Vec3& B,
                       float& target, float& upper) {
  target = 0; upper = 0;
  Vec3 seg = Sub(B, A);
  const float L = Length(seg);
  if (L <= 0.0001f) return;
  const Vec3 dir = Mul(seg, 1.f / L);
  auto cast = [&](const Vec3& from, const Vec3& to, float& fraction, Vec3& point) {
    const Vec3 d = Sub(to, from);
    if (Dot(d, d) <= 1.0e-6f || !w.obstructionRay) return;
    if (auto hit = w.obstructionRay(from, to)) { fraction = hit->fraction; point = hit->point; }
  };
  float fc = 1; Vec3 centrePoint = B;
  cast(A, B, fc, centrePoint);
  float best = fc; Vec3 bestPoint = centrePoint;
  const float cf = tuning::kObstructionCylinderFraction;
  const float R = float(std::sin(double(tuning::kObstructionTestAngle))) * L;
  const Vec3 v0 = Mul(ViewUp(dir), R);
  const Vec3 v1 = RotateAbout(v0, dir, 0.8660254f, 0.5f);
  const Vec3 v2 = RotateAbout(v0, dir, -0.8660254f, 0.5f);
  for (const Vec3* lateral : {&v0, &v1, &v2}) {
    for (float sign : {1.f, -1.f}) {
      const Vec3 wv = Mul(*lateral, sign);
      float f = 1; Vec3 p = Add(B, wv);
      cast(Add(A, Mul(wv, cf)), Add(B, wv), f, p);
      if (f < best) { best = f; bestPoint = p; }
    }
  }
  if (st.cachedValid) {
    const Vec3& Q = st.cached;
    const float t = Dot(dir, Sub(Q, A)) / L;
    bool valid = !(t < 0 || t > 1);
    if (valid) {
      const float rho = cf * R + (R - cf * R) * t;
      bool inside;
      float d2 = PointSegmentDistance2(Q, A, B, inside);
      if (!inside) d2 = std::min(Dot(Sub(Q, A), Sub(Q, A)), Dot(Sub(Q, B), Sub(Q, B)));
      if (d2 > rho * rho + 0.0001f) valid = false;
    }
    if (valid && Dot(Sub(Q, A), Sub(Q, A)) > Dot(Sub(bestPoint, A), Sub(bestPoint, A)) + 0.0001f)
      valid = false;
    if (valid) { best = t; bestPoint = Q; }
    else st.cachedValid = false;
  }
  if (!st.cachedValid && best < 1.f) { st.cached = bestPoint; st.cachedValid = true; }
  target = best; upper = fc;
}
void ObstructionSmooth(const FollowWorld& w, ObstructionState& st, const Vec3& A, const Vec3& B, float dt) {
  float g, U;
  ObstructionTarget(w, st, A, B, g, U);
  const float tau = tuning::kObstructionReturnDelay;
  if (dt == 0) {
    st.fraction = g;
  } else {
    float k;
    if (st.fraction < g) {
      k = st.velocity >= 0 ? 25.f : 75.f;
      if (g - st.fraction >= 0.05f) {
        if (st.timer > 0) { st.timer -= dt; st.velocity = 0; k = 0; }
        else st.timer = 0;
      }
    } else {
      k = 75.f;
      st.timer = tau;
    }
    const float a = k * (g - st.fraction) - 2.f * std::sqrt(k) * st.velocity;
    st.fraction = st.fraction + st.velocity * dt + 0.5f * a * dt * dt;
    st.velocity = st.velocity + a * dt;
  }
  if (U < st.fraction) { st.fraction = U; st.timer = tau; st.velocity = 0; }
}
}  // namespace

FollowResult MonitorFollow(Editor& e, const FollowWorld& w) {
  FollowResult out;
  CameraInput in = w.camera;
  in.predict = true;
  const CameraPoint cp = HeldCamera(e, in);
  const Vec3 P = cp.point, D = cp.view;
  const float d = cp.distance;
  Vec3 F = Add(P, Mul(D, d));
  e.focusOutside = w.pointOutsideWorld ? w.pointOutsideWorld(F) : false;
  Vec3 C = F;
  float r = d;
  if (e.focusOutside) {
    ObstructionSmooth(w, e.obstruction, F, P, w.camera.dt);
    const float s = e.obstruction.fraction;
    C = Sub(F, Mul(D, s * d));
    r = d - s * d;
  }
  const Vec3 M = w.monitorReference;
  Vec3 delta = Sub(P, M);
  if (Dot(delta, delta) > 4.f) delta = Mul(delta, tuning::kMonitorStepCap / Length(delta));
  if (w.monitorContactActive && Length(delta) > 0.0001f) {
    const Vec3& n = w.monitorContactNormal;
    const float nd = Dot(n, delta);
    if (nd < 0) delta = Sub(delta, Mul(n, nd));
  }
  const Vec3 T = Add(M, delta);
  Vec3 g = Sub(C, T);
  if (Length(g) < 0.0001f) { g = D; Normalize(g); }
  else Normalize(g);
  // Frame builder (02 1.3 step 9).
  Pose t;
  t.scale = 1; t.position = T;
  Vec3 fwd = g;
  if (Normalize(fwd) == 0) fwd = {1, 0, 0};
  const Vec3 worldUp{0, 0, 1};
  Vec3 left = Cross(worldUp, fwd);
  if (Normalize(left) == 0) {
    const bool vertical =
        (std::abs(fwd[0]) < kEps && std::abs(fwd[1]) < kEps && std::abs(fwd[2] - 1) < kEps) ||
        (std::abs(fwd[0]) < kEps && std::abs(fwd[1]) < kEps && std::abs(fwd[2] + 1) < kEps);
    const Vec3 helper = vertical ? Vec3{1, 0, 0} : Vec3{0, 0, 1};
    left = Cross(helper, fwd);
    Normalize(left);
  }
  Vec3 up = Cross(fwd, left);
  Normalize(up);
  t.forward = fwd; t.left = left; t.up = up;
  out.monitorTarget = t;
  out.facing = g;
  float heading = std::atan2(g[1], g[0]);
  if (heading < 0) heading += 6.2831855f;
  out.heading = heading;
  out.pitch = std::asin(Clamp(g[2], -1.f, 1.f));
  e.leash = std::min(Length(Sub(T, C)), r);
  const float z = g[2], h = e.pitchHistory;
  if (h > 0 && 0 < z && z < h) e.pitchHistory = z;
  else if (h < 0 && h < z && z < 0) e.pitchHistory = z;
  return out;
}

// ------------------------------------------------------------------ held update
HeldResult UpdateHeld(Editor& e, const HeldWorld& w) {
  HeldResult out;
  const Vec3 v = w.heldVelocity;
  Vec3 correction{};
  if (Length(v) > 0) {
    CameraInput anchor;
    anchor.heldPhysicsPoint = w.heldPhysicsPoint;
    anchor.view = w.viewDirection;
    anchor.definitionRadius = w.heldDefinitionRadius;
    correction = LeashCorrection(e, anchor, w.monitorReference);
  }
  if (!w.hasBodies) return out;
  const bool outside = w.heldFullyOutside ? w.heldFullyOutside() : false;
  if (!outside && w.tick % 5 == 0 && w.body0Transform) e.bodyCache = w.body0Transform();
  // 02 2.1 input displacement.
  const Vec3& h = w.monitorDesiredFacing;
  const Vec3& m = w.monitorMovement;
  const Vec3 a{m[0] * h[0] - m[1] * h[1], m[0] * h[1] + m[1] * h[0], m[2]};
  const float p = w.precision ? tuning::kPrecisionFactor : 1.f;
  const float s = p * w.boost * tuning::kMovementSpeed;
  const Vec3 u = Mul(a, s);
  const Vec3 delta = Mul(u, w.dt);
  const Vec3 R = w.heldOrigin;
  Vec3 T = Add(e.target.position, Add(correction, delta));
  T = ClampBox(T, w.bounds);
  Vec3 d = Sub(T, R);
  if (outside) {
    Vec3 ad = d; Normalize(ad);
    Vec3 bd = Sub(e.bodyCache.position, R); Normalize(bd);
    d = Mul(d, std::max(Dot(ad, bd), 0.f));
  }
  float L = Dot(v, u) > 1e-4f ? 3.f * w.boost : 0.5f;
  if (w.contact) {
    if (auto n = w.contact(e.contactPoint)) {
      const float nd = Dot(*n, d);
      if (Length(d) > 1e-4f && nd < 0) { d = Sub(d, Mul(*n, nd)); L = 0.5f; }
    }
  }
  Limit(d, L);
  T = ClampBox(Add(R, d), w.bounds);
  e.target.position = T;
  Pose S = e.target;
  if (e.rotationSnapMode != 0 && e.rotated) {
    const float step = float(tuning::kRotationSnapDegrees[e.rotationSnapMode]) * kDegToRad;
    QuantizeOrientation(S, step);
    const Basis q = S.GetBasis();
    bool same = true;
    for (unsigned i = 0; i < 9; ++i)
      if (!(std::abs(e.snappedBasis[i] - q[i]) < 1e-4f)) same = false;
    if (!same) { e.target = S; e.snappedBasis = q; }
  }
  if (w.magnets) {
    bool snapped = false;
    out.magnetCandidate = w.magnets(S, snapped);
    out.snapped = snapped;
  }
  out.submitted = true;
  out.submission = S;
  return out;
}

// ------------------------------------------------------------------ physics
unsigned SelectPhysicsState(PhysicsMode mode, bool variantObject, bool held, bool keyframedBody,
                            bool settling) {
  if (!variantObject) return 0;
  const uint16_t bits = uint16_t(mode);
  if (bits & 0x80) return held ? 2 : (keyframedBody ? 0 : 3);
  if (bits & 0x40) return held ? 1 : (keyframedBody ? 0 : 3);
  return held ? 1 : (settling ? 1 : 0);
}
bool PhysicsStateFlags(unsigned state, bool localHolder, PhysicsFlags& f) {
  switch (state) {
    case 0: f.frozen = false; f.forceDynamic = false; f.keyframed = false; return true;
    case 1: f.frozen = false; f.forceDynamic = true; f.keyframed = false; return true;
    case 2:
      f.frozen = false; f.forceDynamic = localHolder; f.keyframed = localHolder; return true;
    case 3: f.frozen = true; f.forceDynamic = false; f.keyframed = false; return true;
    default: return false;
  }
}
void CompensateHeldOffset(Editor& e, const Vec3& before, const Vec3& after) {
  for (unsigned i = 0; i < 3; ++i)
    e.grabOffset[i] = e.grabOffset[i] * e.offsetScale - (after[i] - before[i]);
  e.offsetDecay = 0;
  e.offsetScale = 1;
}
uint16_t EditPhysicsProperty(uint16_t old, uint16_t value) {
  return uint16_t(((old & ~0xc0u) & 0x3ffu) | value);
}

// ------------------------------------------------------------------ coordinates
CoordinateRange PositionRange() { return {-1000.f, 1000.f, 0.1f}; }
CoordinateRange AngleRange(unsigned snapMode) {
  float step = 1.f;
  if (snapMode < tuning::kRotationSnapDegrees.size() && tuning::kRotationSnapDegrees[snapMode] > 0)
    step = std::max(1.f, float(tuning::kRotationSnapDegrees[snapMode]));
  return {-180.f, 179.f, step};
}
unsigned RangeChoiceCount(const CoordinateRange& r) {
  return unsigned(std::trunc(std::trunc(r.maximum - r.minimum + 1) / r.step));
}
float RangeChoice(const CoordinateRange& r, unsigned i) { return r.minimum + float(i) * r.step; }
unsigned RangeIndex(const CoordinateRange& r, float value) {
  const unsigned count = RangeChoiceCount(r);
  if (!count) return 0;
  const long long i = (long long)std::trunc((value + 0.49f * r.step - r.minimum) / r.step);
  long long m = i % (long long)count;
  if (m < 0) m += count;
  return unsigned(m);
}
CoordinatePanel PopulateCoordinates(const Pose& pose, const Vec3& origin) {
  CoordinatePanel panel;
  const Vec3 angles = EulerFromBasis(pose.forward, pose.up);
  for (unsigned i = 0; i < 3; ++i) {
    panel.angles[i] = RoundAway(angles[i] * kRadToDeg);
    panel.position[i] = RoundAway(pose.position[i] * 10.0f) * 0.1f - origin[i];
  }
  return panel;
}
Pose CommitCoordinates(const CoordinatePanel& panel, float scale, const Vec3& origin) {
  Pose pose;
  pose.scale = scale;
  for (unsigned i = 0; i < 3; ++i) pose.position[i] = panel.position[i] + origin[i];
  const Vec3 ypr = Mul(panel.angles, kDegToRad);
  BasisFromEuler(ypr, pose.forward, pose.up);
  pose.left = Cross(pose.up, pose.forward);
  return pose;
}
void ApplyCoordinatePose(Editor& e, const Pose& pose, const std::array<float, 6>& bounds) {
  e.target = pose;
  e.target.position = ClampBox(pose.position, bounds);
}

// ------------------------------------------------------------------ grab / spawn
bool InitializeGrab(Editor& e, const InputState& in, const GrabInput& g) {
  if (!g.hasBodies) return false;
  e.target = g.objectPose;
  e.target.position = ClampBox(g.objectPose.position, g.bounds);
  const Vec3 diff = Sub(e.aimPoint, g.monitorPoint);
  const float projected = std::fma(g.monitorForward[0], diff[0],
                                   std::fma(g.monitorForward[2], diff[2], g.monitorForward[1] * diff[1]));
  e.holdDistance = ClampHoldDistance(e, in, projected, true, g.runtimeRadius);
  e.contactPoint = g.heldPhysicsPoint;
  return true;
}
Vec3 PullSpawnPoint(const Vec3& requested, std::optional<Vec3> monitor, float rho) {
  if (rho < 0.0001f) rho = 1.0f;
  Vec3 p = requested;
  if (monitor) {
    Vec3 v = Sub(*monitor, p);
    const float s = Normalize(v);
    const float k = s == 0 ? 0.f : (rho < s ? rho : 0.5f * s);
    p = Add(p, Mul(v, k));
  }
  return p;
}
float AimRange(const Editor& e) { return std::max(e.holdDistance, tuning::kGrabRange); }

}  // namespace forge
