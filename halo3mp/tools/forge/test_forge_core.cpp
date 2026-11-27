// Standalone checks of forge_core against values stated in the specification.
// Build: clang++ -std=c++23 -O1 test_forge_core.cpp ../../src/forge/forge_core.cpp ../../src/forge/forge_magnets.cpp
#include "../../src/forge/forge_core.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <bit>

static int failures = 0;
static void Check(bool ok, const char* what) { if (!ok) { ++failures; std::printf("FAIL %s\n", what); } }
static bool Near(float a, float b, float e = 1e-5f) { return std::abs(a - b) <= e; }

int main() {
  using namespace forge;
  // Pitch curve samples (spec 05 B.3, by x), exact hex.
  struct S { float x; uint32_t hex; } samples[] = {{0.0f, 0x3F800000}, {0.25f, 0x3EC040E8}, {0.5f, 0xBB2F4A00},
                                                  {0.75f, 0xBEFFE830}, {1.0f, 0xBF7FFFE8}};
  for (auto s : samples) {
    const float v = PitchCurve(s.x);
    Check(Near(v, std::bit_cast<float>(s.hex), 2e-6f), "pitch curve sample");
  }
  // End to end by t = D.z - h (05 B.3): t=0 -> -0.0026747, t=+0.5 -> +0.1853758.
  auto lift = [](float t) {
    const float a = SpecArcsine(t);
    float x = (1.5707964f - a) * 0.31830987f;
    x = x < 0 ? 0 : (x > 1 ? 1 : x);
    return PitchCurve(x);
  };
  Check(Near(lift(0.0f), -0.0026747f, 2e-6f), "lift at level");
  Check(Near(lift(0.5f), 0.1853758f, 2e-5f), "lift looking up half");
  Check(Near(lift(-1.0f), -0.9999986f, 2e-6f), "lift straight down");
  // Euler conventions are mutual inverses away from the gimbal (04 5.3).
  for (float yaw : {-2.0f, 0.3f, 1.2f})
    for (float pitch : {-1.0f, 0.0f, 0.7f})
      for (float roll : {-0.5f, 0.0f, 2.5f}) {
        Vec3 f, u;
        BasisFromEuler({yaw, pitch, roll}, f, u);
        const Vec3 back = EulerFromBasis(f, u);
        Check(Near(back[0], yaw, 1e-4f) && Near(back[1], pitch, 1e-4f) && Near(back[2], roll, 1e-4f), "euler round trip");
        // Quaternion Euler pair (01 0) round trip.
        const Quat q = EulerToQuat({yaw, pitch, roll});
        const Vec3 qb = QuatToEuler(q, 0.0001f);
        Check(Near(qb[0], yaw, 1e-4f) && Near(qb[1], pitch, 1e-4f) && Near(qb[2], roll, 1e-4f), "quat euler round trip");
        // Basis/quaternion consistency.
        Pose p; p.forward = f; p.up = u; p.left = Cross(u, f);
        const Basis b = BasisFromQuat(QuatFromBasis(p.GetBasis()));
        for (int i = 0; i < 9; ++i) Check(Near(b[i], p.GetBasis()[i], 1e-5f), "quat basis round trip");
      }
  // Pure pitch raises the nose (01 0).
  { Vec3 f, u; BasisFromEuler({0, 0.5f, 0}, f, u); Check(f[2] > 0, "positive pitch raises the nose"); }
  // Rule D (03 4.2): r = 1 -> L = max(1.25, 1.4) = 1.4, U = min(7, 22) = 7.
  {
    Editor e; InputState in;
    Check(Near(ClampHoldDistance(e, in, 0.f, true, 1.f), 1.4f), "rule D lower");
    Check(Near(ClampHoldDistance(e, in, 100.f, true, 1.f), 7.f), "rule D upper");
    Check(Near(ClampHoldDistance(e, in, 3.f, false, 1.f), 7.5f), "rule D unheld");
    in.active = true; in.distance = 1.f;  // stick forward pulls in by 0.3
    Check(Near(ClampHoldDistance(e, in, 5.f, true, 1.f), 4.7f), "push/pull direction");
    Check(Near(ClampHoldDistance(e, in, 50.f, true, 20.f), 22.f), "large piece: maximum wins");
  }
  // Rotation (04 2.2): full yaw for one 30 Hz tick turns 5/30 rad clockwise from above.
  {
    Editor e; e.held = 1; InputState in; in.active = true; in.yaw = 1.f;
    RotationGate g; g.typeAllowed = g.connected = g.hasInstance = true; g.bodyFixed = {false};
    Check(RotateHeld(e, in, {1, 0, 0}, 1.f / 30.f, g), "rotation applied");
    Check(Near(e.target.forward[1], -std::sin(5.f / 30.f), 1e-5f), "yaw about world down");
    Check(e.rotated && Near(e.offsetDecay, 5.f / 30.f), "rotated flag and decay seeding");
    g.bodyFixed = {true};
    Editor f; f.held = 1;
    Check(!RotateHeld(f, in, {1, 0, 0}, 1.f / 30.f, g), "fixed body blocks rotation");
  }
  // Snap quantizer rounds half away from zero (04 3.3).
  {
    Pose p; Vec3 f, u; BasisFromEuler({0.40f, 0, 0}, f, u); p.forward = f; p.up = u; p.left = Cross(u, f);
    QuantizeOrientation(p, 90.f * 0.017453292f);
    Check(Near(EulerFromBasis(p.forward, p.up)[0], 0.f, 1e-5f), "snap rounds 23 degrees to 0");
    BasisFromEuler({0.80f, 0, 0}, f, u); p.forward = f; p.up = u;
    QuantizeOrientation(p, 90.f * 0.017453292f);
    Check(Near(EulerFromBasis(p.forward, p.up)[0], 1.5707963f, 1e-5f), "snap rounds 46 degrees to 90");
  }
  // Coordinate ranges (04 5.6): 20010 position choices, 360 angle choices.
  Check(RangeChoiceCount(PositionRange()) == 20010, "position choices");
  Check(RangeChoiceCount(AngleRange(0)) == 360, "angle choices");
  Check(RangeChoiceCount(AngleRange(4)) == 24, "angle choices at 15 degree snap");
  Check(RangeIndex(AngleRange(0), 0.f) == 180, "angle index of zero");
  // Physics state table (04 4.2).
  Check(SelectPhysicsState(PhysicsMode::Phased, true, true, false, false) == 2, "phased held");
  Check(SelectPhysicsState(PhysicsMode::Fixed, true, false, false, false) == 3, "fixed released");
  Check(SelectPhysicsState(PhysicsMode::Normal, true, false, false, true) == 1, "normal settling");
  Check(SelectPhysicsState(PhysicsMode::Normal, true, true, false, false) == 1, "normal held");
  // Spawn pull (03 5.2).
  {
    const Vec3 p = PullSpawnPoint({10, 0, 0}, Vec3{0, 0, 0}, 2.f);
    Check(Near(p[0], 8.f), "spawn pulled by radius");
    const Vec3 q = PullSpawnPoint({1, 0, 0}, Vec3{0, 0, 0}, 2.f);
    Check(Near(q[0], 0.5f), "spawn pulled half way when closer than one radius");
  }
  // Keyframe drive reaches the target in tau (02 4.2).
  {
    Pose target; target.position = {1, 0, 0};
    BodyState body;
    const auto cmd = DriveBody(target, 0.2f, body);
    Check(cmd.setLinear && Near(cmd.linear[0], 5.f), "drive linear velocity");
    Check(!cmd.setAngular, "no rotation needed");
  }
  // Magnets: a held 2x2 block beside another, within the snap radius, snaps flush.
  {
    const MagnetTable* block = FindMagnets(1731, 0x900029C2);  // Wall, 2x2 (bound from the palette)
    Check(block && block->count == 8, "wall 2x2 magnet table");
    if (block) {
      Editor e; e.held = 1; e.magnetsEnabled = true;
      Pose heldPose; heldPose.position = {2.3f, 0, 0};
      e.target = heldPose;
      MagnetObject held; held.datum = 1; held.center = heldPose.position; held.radius = 1.8f; held.hasGroup = true;
      held.markers = BuildMarkers(*block, heldPose);
      MagnetObject other; other.datum = 2; other.center = {0, 0, 0}; other.radius = 1.8f; other.hasGroup = true;
      other.markers = BuildMarkers(*block, Pose{});
      MagnetWorld w; w.held = &held; w.heldPhysicsPoint = heldPose.position;
      w.nearby = [&](const Vec3&, float) { return std::vector<MagnetObject>{held, other}; };
      const auto pair = FindMagnetCandidate(e, w);
      Check(pair.state == 2 && pair.candidate == 2, "snap available");
      Quat r; Vec3 pos;
      AlignMagnet(e, pair.heldMarker, pair.candidateMarker, r, pos);
      Check(Near(pos[0], 2.f, 1e-4f) && Near(pos[1], 0.f, 1e-4f) && Near(pos[2], 0.f, 1e-4f), "snapped flush beside");
    }
  }
  // Ravine stick curves (04 Round 5 sample table).
  {
    struct C { float x, left, right; } table[] = {{0.05f, 0.0327f, 0.0112f}, {0.25f, 0.2037f, 0.0479f},
        {0.5f, 0.4748f, 0.1626f}, {0.6f, 0.5898f, 0.2660f}, {0.75f, 0.7584f, 0.4994f}, {0.9f, 0.9119f, 0.7918f},
        {1.0f, 1.f, 1.f}, {1.3f, 1.f, 1.f}};
    for (auto c : table) {
      Check(Near(EvaluateCurve(ravine::kLeftStickCurve, 1, c.x), c.left, 6e-4f), "left stick curve sample");
      Check(Near(EvaluateCurve(ravine::kRightStickCurve, 2, c.x), c.right, 6e-4f), "right stick curve sample");
    }
    // Dead zone: inside 4095 nothing; full deflection reaches 1 after the curve.
    RawSticks r; r.ly = 4000; Check(ProcessSticks(r).forward == 0.f, "inside dead zone");
    r.ly = 32767; Check(Near(ProcessSticks(r).forward, 1.f, 1e-4f), "full forward");
    r.ly = -32768; Check(Near(ProcessSticks(r).forward, -1.f, 1e-4f), "full back");
    r = {}; r.lx = 32767; Check(Near(ProcessSticks(r).left, -1.f, 1e-4f), "stick right = negative left");
    r = {}; r.rx = 32767; Check(Near(ProcessSticks(r).lookA, -1.f, 1e-4f), "right stick right = -Rx yaw");
    // Half deflection on the move stick: axial then radial rescale, then curve.
    r = {}; r.ly = 18431;  // axial -> (18431-4095)*32767/28672 = 16383 -> radial -> 14042/32767 = 0.4285
    const float expect = EvaluateCurve(ravine::kLeftStickCurve, 1, std::trunc((18431.f - 4095.f) * 32767.f / 28672.f) - 4095.f > 0 ?
                         ((std::trunc((18431.f - 4095.f) * 32767.f / 28672.f) - 4095.f) * 32767.f / 28672.f) / 32767.f : 0.f);
    Check(Near(ProcessSticks(r).forward, expect, 1e-4f), "half deflection through both dead zones");
    r = {}; r.rt = 25; Check(!(ProcessSticks(r).trigger > 0.1f), "trigger 25/255 below threshold");
    r.rt = 26; Check(ProcessSticks(r).trigger > 0.1f, "trigger 26/255 above threshold (spec: about 26/255)");
  }
  // Magnet step: snap, pull-away, out of range, orientation gap (01 5.2-5.4).
  if (const MagnetTable* wall = FindMagnets(1731, 0x900029C2)) {
    auto setup = [&](float x, Vec3 movement, float heldYawDeg, Pose& S, bool& snapped) {
      Editor e; e.held = 1; e.magnetsEnabled = true;
      Pose requested; requested.position = {x, 0, 0};
      e.target = requested;
      // The physical piece may lag the requested orientation (heldYawDeg).
      Pose actual = requested; Vec3 f, u; BasisFromEuler({heldYawDeg * 0.017453292f, 0, 0}, f, u);
      actual.forward = f; actual.up = u; actual.left = Cross(u, f);
      MagnetObject held; held.datum = 1; held.center = actual.position; held.radius = 1.8f; held.hasGroup = true;
      held.markers = BuildMarkers(*wall, actual);
      MagnetObject other; other.datum = 2; other.center = {0, 0, 0}; other.radius = 1.8f; other.hasGroup = true;
      other.markers = BuildMarkers(*wall, Pose{});
      MagnetWorld w; w.held = &held; w.heldPhysicsPoint = actual.position; w.processedMovement = movement;
      w.nearby = [=](const Vec3&, float) { return std::vector<MagnetObject>{held, other}; };
      S = e.target;
      return MagnetStep(e, w, S, snapped);
    };
    Pose S; bool snapped;
    auto p = setup(2.3f, {0, 0, 0}, 0, S, snapped);
    Check(snapped && p.candidate == 2 && Near(S.position[0], 2.f, 1e-4f), "wall snaps flush beside wall");
    p = setup(2.3f, {0.6f, 0, 0}, 0, S, snapped);
    Check(!snapped && p.candidate == 2 && Near(S.position[0], 2.3f), "pull-away: stick past half releases, target kept");
    p = setup(2.3f, {0.4f, 0, 0}, 0, S, snapped);
    Check(snapped, "small stick input stays snapped");
    p = setup(2.3f, {0, 0, 1.f}, 0, S, snapped);
    Check(!snapped, "up/down button releases");
    p = setup(3.5f, {0, 0, 0}, 0, S, snapped);
    Check(!snapped && p.state == 1 && p.candidate == 2, "beyond snap radius: candidate shown, no snap");
    p = setup(2.3f, {0, 0, 0}, 50.f, S, snapped);
    Check(!snapped, "piece more than 45 degrees behind its requested turn: no snap");
  }
  // Held update: snap applies only after a turn, jumping at the half step (04 3.2).
  {
    Editor e; e.held = 1; e.rotationSnapMode = 1;  // 90 degrees
    Vec3 f, u; BasisFromEuler({0.6f, 0, 0}, f, u); e.target.forward = f; e.target.up = u; e.target.left = Cross(u, f);
    HeldWorld w; w.hasBodies = true; w.dt = 1.f / 30.f; w.bounds = {-1000, 1000, -1000, 1000, -1000, 1000};
    auto r = UpdateHeld(e, w);
    Check(Near(EulerFromBasis(r.submission.forward, r.submission.up)[0], 0.6f, 1e-4f), "no snapping before the first turn");
    e.rotated = true;
    r = UpdateHeld(e, w);
    Check(Near(EulerFromBasis(r.submission.forward, r.submission.up)[0], 0.f, 1e-4f), "34 degrees snaps to 0");
    BasisFromEuler({0.9f, 0, 0}, f, u); e.target.forward = f; e.target.up = u; e.target.left = Cross(u, f);
    r = UpdateHeld(e, w);
    Check(Near(EulerFromBasis(r.submission.forward, r.submission.up)[0], 1.5707963f, 1e-4f), "52 degrees snaps to 90");
    // Target leads the piece by at most 0.5 per tick when not moving with input.
    Editor m; m.held = 1; m.target.position = {10, 0, 0};
    HeldWorld w2 = w; w2.heldOrigin = {0, 0, 0};
    r = UpdateHeld(m, w2);
    Check(Near(r.submission.position[0], 0.5f), "target lead capped at 0.5");
    // Moving with input: lead cap 3 x boost.
    Editor n; n.held = 1; HeldWorld w3 = w; w3.monitorDesiredFacing = {1, 0, 0}; w3.monitorMovement = {1, 0, 0};
    w3.heldVelocity = {1, 0, 0};
    r = UpdateHeld(n, w3);
    Check(Near(r.submission.position[0], 4.f / 30.f, 1e-5f), "full stick moves 4 units per second");
    w3.precision = true; Editor q; q.held = 1;
    r = UpdateHeld(q, w3);
    Check(Near(r.submission.position[0], 0.4f / 30.f, 1e-6f), "precision mode 10 percent");
    // Bounds clamp.
    Editor b; b.held = 1; b.target.position = {5, 0, 0}; HeldWorld w4 = w; w4.heldOrigin = {5, 0, 0};
    w4.bounds = {-2, 2, -2, 2, -2, 2};
    r = UpdateHeld(b, w4);
    Check(Near(r.submission.position[0], 2.f), "target kept inside map bounds");
  }
  // Input shaping (04 1): dominant axes, trigger gate, packet consumption.
  {
    InputState st; InputFrame f; f.eligible = true; f.trigger = 0.5f; f.rotationAvailable = true;
    f.forward = 0.3f; f.left = 0.6f; f.lookA = -0.8f; f.lookB = 0.2f;
    auto rem = ShapeInput(st, f);
    Check(st.active && st.distance == 0 && st.roll == 0.6f && st.yaw == -0.8f && st.pitch == 0, "dominant axes kept");
    Check(rem[0] == 0 && rem[1] == 0, "movement consumed while manipulating");
    f.trigger = 0.1f; rem = ShapeInput(st, f);
    Check(!st.active && rem[0] == 0.3f, "trigger at 0.1 does not manipulate; movement passes through");
  }
  // Monitor follow: camera behind the piece, step cap 2, facing the focus (02 1.3 / 05 A.4).
  {
    Editor e; e.held = 1; e.holdDistance = 5;
    FollowWorld w; w.camera.heldPhysicsPoint = {10, 0, 0}; w.camera.view = {1, 0, 0}; w.camera.definitionRadius = 1;
    w.camera.dt = 1.f / 30.f; w.monitorReference = {0, 0, 0};
    w.pointOutsideWorld = [](const Vec3&) { return false; };
    auto r = MonitorFollow(e, w);
    Check(Near(r.monitorTarget.position[0], 2.f), "monitor moves at most 2 units per tick");
    w.monitorReference = {5, 0, 0};
    r = MonitorFollow(e, w);
    Check(Near(r.monitorTarget.position[0], 5.f, 1e-3f) && Near(r.facing[0], 1.f, 1e-3f), "monitor sits hold distance behind, facing the piece");
    Check(Near(r.heading, 0.f, 1e-4f), "view heading");
  }
  // Camera obstruction (05 A.4-A.5): rays only when the focus is outside the level;
  // a hit at half way pulls the camera in quickly (k = 75), then the upper clamp holds.
  {
    Editor e; e.held = 1; e.holdDistance = 6;
    FollowWorld w; w.camera.heldPhysicsPoint = {0, 0, 0}; w.camera.view = {1, 0, 0}; w.camera.dt = 1.f / 30.f;
    w.monitorReference = {-6, 0, 0};
    int rays = 0;
    w.obstructionRay = [&](const Vec3& a, const Vec3& b) -> std::optional<RayHit> { ++rays; return RayHit{0.5f, Add(a, Mul(Sub(b, a), 0.5f))}; };
    w.pointOutsideWorld = [](const Vec3&) { return false; };
    MonitorFollow(e, w);
    Check(rays == 0 && !e.focusOutside, "no obstruction rays while the focus is inside");
    w.pointOutsideWorld = [](const Vec3&) { return true; };
    MonitorFollow(e, w);
    Check(rays == 7, "seven obstruction rays per tick (centre + six)");
    Check(e.obstruction.fraction <= 0.5f + 1e-5f, "camera clamped to the centre ray's hit");
    Check(Near(e.leash, 3.f, 0.2f), "retained distance shrinks to the clear part");
    rays = 0;
    w.obstructionRay = [&](const Vec3&, const Vec3&) -> std::optional<RayHit> { ++rays; return std::nullopt; };
    for (int i = 0; i < 10; ++i) MonitorFollow(e, w);
    Check(e.obstruction.fraction <= 0.5f + 1e-4f, "remembered obstruction point holds while inside the ray cone (A.5.1 step 7)");
    w.camera.view = {0, 1, 0};  // view swings away: the remembered point leaves the cone
    for (int i = 0; i < 60; ++i) MonitorFollow(e, w);
    Check(e.obstruction.fraction > 0.95f && !e.obstruction.cachedValid, "camera eases back out once clear (k = 25)");
  }
  // Physics flags (04 4.3).
  {
    PhysicsFlags f;
    PhysicsStateFlags(2, true, f); Check(f.keyframed && f.forceDynamic && !f.frozen, "phased held locally is keyframed");
    PhysicsStateFlags(3, true, f); Check(f.frozen && !f.keyframed, "released fixed/phased is frozen");
    PhysicsStateFlags(0, true, f); Check(!f.frozen && !f.forceDynamic && !f.keyframed, "normal released is plain");
    Check(EditPhysicsProperty(0xff40, 0xc0) == 0x3c0, "property edit keeps bits 0-9, clears 10-15");
  }
  // Coordinate commit: whole degrees and 0.1 grid (04 5.2-5.4).
  {
    Pose p; p.position = {1.26f, -3.04f, 7.f};
    Vec3 f, u; BasisFromEuler({0.5f, 0.1f, -0.2f}, f, u); p.forward = f; p.up = u; p.left = Cross(u, f);
    auto panel = PopulateCoordinates(p, {});
    Check(Near(panel.position[0], 1.3f, 1e-5f) && Near(panel.position[1], -3.0f, 1e-5f), "positions rounded to 0.1");
    Check(panel.angles[0] == 29.f && panel.angles[1] == 6.f && panel.angles[2] == -11.f, "angles rounded to whole degrees");
    auto back = CommitCoordinates(panel, 1.f, {});
    Check(Near(EulerFromBasis(back.forward, back.up)[0], 29.f * 0.017453292f, 1e-4f), "commit rebuilds orientation");
  }
  Check(!FindMagnets(1730, 0x90002A87), "Cove-only block is not on Gulch");
  Check(!AdvancedForgeMap(1000), "other maps disabled");
  std::printf("%s (%d failures)\n", failures ? "FAILED" : "all checks passed", failures);
  return failures ? 1 : 0;
}
