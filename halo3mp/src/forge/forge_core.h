#pragma once
// Spartan Advanced Forge core.
//
// Clean-room implementation written only from the specification in
// tools/h4-forge/ADVANCED-FORGE.md (sections 00-07). It contains no Halo 4
// program code, data, layouts or assets. Everything here operates on plain
// host values; the Halo 3 integration (advanced_forge.cpp) reads the game
// world into these structures and writes the results back through Halo 3's
// own services. Section references (e.g. "02 1.2") point into that spec.
#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <vector>

namespace forge {

inline constexpr uint32_t kNone = 0xffffffffu;
using Vec3 = std::array<float, 3>;
using Basis = std::array<float, 9>;  // forward, left, up

struct Quat { float x = 0, y = 0, z = 0, w = 1; };

// 13-float transform: scale, forward, left, up, position (01 0).
struct Pose {
  float scale = 1;
  Vec3 forward{1, 0, 0}, left{0, 1, 0}, up{0, 0, 1}, position{};
  std::array<float, 13> Packed() const;
  static Pose Unpack(const std::array<float, 13>& v);
  Basis GetBasis() const;
  void SetBasis(const Basis& b);
};

// ---------------------------------------------------------------- maths
Vec3 Add(const Vec3& a, const Vec3& b);
Vec3 Sub(const Vec3& a, const Vec3& b);
Vec3 Mul(const Vec3& a, float s);
float Dot(const Vec3& a, const Vec3& b);
Vec3 Cross(const Vec3& a, const Vec3& b);
float Length(const Vec3& a);
// Rule N: shorter than 1e-4 stays unchanged and reports 0.
float Normalize(Vec3& v);
// limit(v,m): scale to length m when longer.
bool Limit(Vec3& v, float m);
// clampBox with bounds (minX,maxX,minY,maxY,minZ,maxZ); min tested first.
Vec3 ClampBox(const Vec3& p, const std::array<float, 6>& b);

Quat QuatFromBasis(const Basis& b);
Basis BasisFromQuat(const Quat& q);
Quat QuatMul(const Quat& a, const Quat& b);
Quat QuatNormalize(const Quat& q);
Quat QuatConj(const Quat& q);
Vec3 QuatRotate(const Quat& q, const Vec3& v);
float QuatAngle(const Quat& a, const Quat& b);
// Quaternion <-> (yaw, pitch, roll) as used by the magnet alignment (01 0).
Vec3 QuatToEuler(const Quat& q, float epsilon);
Quat EulerToQuat(const Vec3& ypr);
// Pose <-> (yaw, pitch, roll) used by snap and the coordinate panel (04 5.3).
Vec3 EulerFromBasis(const Vec3& forward, const Vec3& up);
void BasisFromEuler(const Vec3& ypr, Vec3& forward, Vec3& up);
// Rodrigues rotation of v about unit axis a by angle (sine, cosine).
Vec3 RotateAbout(const Vec3& v, const Vec3& axis, float s, float c);
Pose Compose(const Pose& a, const Pose& b);
Vec3 Apply(const Pose& t, const Vec3& p);

// ---------------------------------------------------------------- tuning
// Values stated by the specification as our chosen values (sections 01-05).
namespace tuning {
inline constexpr float kMagnetMovementThreshold = 0.5f;             // 01 6
inline constexpr std::array<float, 5> kSnapRadiusFactor{0.10f, 0.25f, 0.50f, 0.75f, 1.00f};
inline constexpr float kMagnetAngleDegrees = 45.0f;                 // 01 6
inline constexpr float kMagnetOffsetWeight = 0.75f;                 // 01 3.2
inline constexpr unsigned kDefaultSensitivity = 2;
inline constexpr unsigned kMaxMarkers = 32, kMaxNearby = 64;
inline constexpr std::array<int, 6> kRotationSnapDegrees{0, 90, 45, 30, 15, 5};
inline constexpr float kGrabRange = 7.5f;                           // 03 6.2
inline constexpr float kDefaultFocalDistance = 7.5f;
inline constexpr float kMaximumFocalDistance = 22.0f;
inline constexpr float kFocalDistanceMultiplier = 5.0f;
inline constexpr float kPushPullRate = 0.3f;                        // 03 4.2
inline constexpr float kTriggerThreshold = 0.1f;                    // 03 4.3
inline constexpr float kRotationGain = 5.0f;                        // 04 2.2
inline constexpr float kHeldDriveTime = 0.2f, kMonitorDriveTime = 0.05f;
inline constexpr float kMovementSpeed = 4.0f, kPrecisionFactor = 0.1f;
inline constexpr float kMonitorStepCap = 2.0f;
// Soft-ceiling response coefficients (02 3.1 step 3).
inline constexpr std::array<float, 4> kBipedContact{45.0f, 10.0f, 2.0f, 4.0f};
inline constexpr std::array<float, 3> kObjectContact{20.0f, 4.0f, 1.0f};
// Monitor camera obstruction (05 B.2): cylinder fraction, test angle, return delay.
inline constexpr float kObstructionCylinderFraction = 0.0f;
inline constexpr float kObstructionTestAngle = 0.17453292f;
inline constexpr float kObstructionReturnDelay = 0.0f;
}

// Ravine map data supplied in the specification (03/04/05 "Ravine values").
namespace ravine {
// Stick dead zones (04 Round 5): inner per-axis and radial, both 0.125 x 32767.
inline constexpr int kStickDeadZone = 4095;
// Response curves y = a x^3 + b x^2 + c x + d, segment applies while x <= end.
struct CurveSegment { float end, a, b, c, d; };
inline constexpr CurveSegment kLeftStickCurve[] = {{3.40282347e38f, -0.5830377f, 0.9754766f, 0.6075611f, 0.f}};
inline constexpr CurveSegment kRightStickCurve[] = {{0.505f, 1.5447578f, -0.6235934f, 0.2508628f, 0.f},
                                                    {3.40282347e38f, -1.9517484f, 5.7023044f, -3.4632044f, 0.7126485f}};
// Collision-filter row 27 (camera obstruction rays, 05 Round 4): bit n set =
// a body on layer n blocks. Halo 3 has no layers; the integration admits the
// object kinds whose Ravine layers this row accepts (all crates, scenery,
// machines, items, units, vehicles, projectiles) and structure surfaces.
inline constexpr uint32_t kObstructionRow = 0xA7E2FFFB;
// Spawn search world-point height offset h (03 Round 4): scenario entry 0.
inline constexpr float kSpawnHeightOffset = 0.0f;
}

// ---------------------------------------------------------------- markers
struct MagnetDef {
  Vec3 position;          // object frame
  Vec3 forward, up;       // frame (no behavioural effect, kept for exactness)
};
struct MagnetTable {
  uint32_t map;           // map id
  uint32_t tag;           // object definition datum
  const char* name;
  const MagnetDef* magnets;
  uint32_t count;
};
// Look up the code-defined magnet set for a piece, or null (06 7).
const MagnetTable* FindMagnets(uint32_t map, uint32_t tag);
// Maps with Advanced Forge enabled (user decision; overview "Scope").
bool AdvancedForgeMap(uint32_t map);

// Runtime marker: local (node-relative) and world frames (01 1.2).
struct Marker {
  Basis localBasis;
  Vec3 localPosition;
  Basis worldBasis;
  Vec3 worldPosition;
};
// Build markers for an object given its node-0 world transform (01 1.2/Q2).
std::vector<Marker> BuildMarkers(const MagnetTable& table, const Pose& node);

// ---------------------------------------------------------------- editor
struct ObstructionState {
  float fraction = 1;      // +228 smoothed clear fraction (1.0 at construct)
  float velocity = 0;      // +232
  float timer = 0;
  Vec3 cached{};
  bool cachedValid = false;
};

// Per-player Forge editor (03 1.1). Named fields only; transient.
struct Editor {
  uint32_t held = kNone, magnetTarget = kNone, aimed = kNone;
  Vec3 heldOrigin{};
  float holdDistance = tuning::kDefaultFocalDistance;
  float leash = 0;              // retained distance (+32)
  float offsetScale = 0, offsetDecay = 0;
  Vec3 aimPoint{};
  Vec3 grabOffset{};
  Vec3 contactPoint{};          // held point at grab, then contact cache (+68)
  bool focusOutside = false;    // +80
  bool rotated = false;         // +81
  bool magnetsEnabled = false;  // +82
  Pose target;                  // persistent unsnapped target (+84)
  Basis snappedBasis{};         // +136
  Pose bodyCache;               // +172
  unsigned rotationSnapMode = 0;  // +224
  ObstructionState obstruction;   // +228
  unsigned sensitivity = tuning::kDefaultSensitivity;  // +268
  float pitchHistory = 0;       // +276
  bool restoreFlag = false;
};

// Per-player manipulation input (04 1).
struct InputState {
  bool active = false;
  float distance = 0, roll = 0, yaw = 0, pitch = 0;
};
struct InputFrame {
  bool eligible = false;        // edit eligibility with a held object
  float forward = 0, left = 0;  // movement stick
  float trigger = 0;
  bool rotationAvailable = false;
  float lookA = 0, lookB = 0;   // yaw, pitch look axes
};
// Returns the movement pair left in the packet (zeroed when consumed).
std::array<float, 2> ShapeInput(InputState& state, const InputFrame& frame);

// Controller sticks to the Forge inputs (04 1.2 stages B-C with the Ravine
// dead zones and curves). Raw XInput shorts in, +X right, +Y up.
struct RawSticks { int16_t lx = 0, ly = 0, rx = 0, ry = 0; uint8_t lt = 0, rt = 0; };
struct ProcessedSticks { float forward = 0, left = 0, lookA = 0, lookB = 0, trigger = 0; };
ProcessedSticks ProcessSticks(const RawSticks& raw);
float EvaluateCurve(const ravine::CurveSegment* segments, unsigned count, float x);

void InitializeEditor(Editor& e);

struct VisibilityChange {
  std::vector<uint32_t> hide, show;
};
// 04 6: marker visibility from the prior held/target pair.
VisibilityChange UpdateVisibility(const Editor& e, uint32_t priorHeld, uint32_t priorTarget);

struct SelectionWorld {
  bool localPlayer = true;
  std::function<Vec3(uint32_t)> physicsPoint;   // object physics point
  std::function<Vec3(uint32_t)> origin;         // object origin
  uint32_t monitor = kNone;
};
// 03 1.3: select / release reset. Returns marker visibility changes.
VisibilityChange SelectHeld(Editor& e, uint32_t newHeld, const SelectionWorld& world);
// 03 1.4
VisibilityChange SetMagnetTarget(Editor& e, uint32_t target, bool localPlayer);
// 03 1.5. Returns true when the held object was released by the deletion.
bool ObjectDeleted(Editor& e, uint32_t datum, const SelectionWorld& world, VisibilityChange& visibility);

// 03 4.2 rule D.
float ClampHoldDistance(const Editor& e, const InputState& in, float d, bool held, float runtimeRadius);

// ---------------------------------------------------------------- rotation
struct RotationGate {
  bool typeAllowed = false;    // object type in the allowed set
  bool connected = false;      // object connected to physics
  bool hasInstance = false;
  bool instanceBlocked = false;
  std::vector<bool> bodyFixed; // per body: motion Fixed
};
bool RotationAllowed(const RotationGate& g);
// 04 2.1 + 2.2. Returns true when rotated.
bool RotateHeld(Editor& e, const InputState& in, const Vec3& monitorView, float dt,
                const RotationGate& gate);
// 04 3.3
void QuantizeOrientation(Pose& s, float step);

// ---------------------------------------------------------------- magnets
struct MagnetObject {
  uint32_t datum = kNone;
  Vec3 center{};          // runtime bounding-sphere centre
  float radius = 0;       // runtime bounding radius
  bool hasGroup = false;  // the object itself carries magnets
  std::vector<Marker> markers;  // its root's markers
};
struct MagnetWorld {
  const MagnetObject* held = nullptr;
  Vec3 heldPhysicsPoint{};
  std::function<std::vector<MagnetObject>(const Vec3& center, float radius)> nearby;
  Vec3 processedMovement{};
};
struct MagnetPair {
  uint32_t candidate = kNone;
  int state = 0;
  Marker heldMarker{}, candidateMarker{};
};
Vec3 MagnetReferencePoint(const Editor& e, const Vec3& physicsPoint);
MagnetPair FindMagnetCandidate(const Editor& e, const MagnetWorld& world);
// The magnet step for one tick (01 5.2 steps 2-4): search, then translate the
// submission onto the target magnet unless the movement input exceeds 0.5.
// Returns the pair (candidate kept for state 1 and 2); snapped when aligned.
MagnetPair MagnetStep(const Editor& e, const MagnetWorld& world, Pose& submission, bool& snapped);
// Alignment output (01 4).
void AlignMagnet(const Editor& e, const Marker& h, const Marker& c, Quat& rotation, Vec3& position);

// ---------------------------------------------------------------- contacts
struct ContactSample {
  Vec3 normal{};
  float planeDistance = 0, closestDistance = 0;
  Vec3 closestPoint{};
  std::array<Vec3, 3> triangle{};
};
struct ContactSet {
  int primary = -1;
  float closestDistance = 0;
  std::vector<ContactSample> samples;
  uint32_t flags = 0;
};
struct ContactSelection { bool ok = false; Vec3 normal{}; float distance = 0, residual = 0; int count = 0; bool normalWritten = false; };
ContactSelection SelectContactPlanes(const ContactSet& set, const Vec3& point, bool reverse);
struct ContactInput {
  bool biped = false;
  bool optOut = false;         // collision flags bit 0x4
  bool previouslyActive = false;
  Vec3 velocity{}, physicsPoint{};
  float objectRadius = 0, dt = 0;
  std::function<ContactSet(const Vec3& center, float radius, float range)> collect;
};
struct ContactResult {
  bool contact = false;
  Vec3 normal{};
  Vec3 cachedPoint{};
  Vec3 velocity{};             // response velocity (only applied by callers that need it)
  uint32_t collectorFlags = 0;
};
// 02 3.1 (soft-ceiling push-back), with the cached point Q refreshed.
ContactResult ResolveContact(const ContactInput& in, const Vec3& cachedPoint);

// ---------------------------------------------------------------- body drive
struct BodyState {
  Vec3 position{};
  Quat orientation{};
  Vec3 linearVelocity{}, angularVelocity{};
};
struct BodyCommand {
  bool setAngular = false, setLinear = false;
  Vec3 angular{}, linear{};
};
// 02 4.2 keyframe drive.
BodyCommand DriveBody(const Pose& target, float tau, const BodyState& body);
// 02 4.4
Pose FlattenBipedTarget(const Pose& target, Vec3& flattenedForward);

// ---------------------------------------------------------------- held update
struct HeldWorld {
  bool hasBodies = false;
  uint32_t tick = 0;
  float dt = 0;
  Vec3 heldVelocity{};
  Vec3 heldOrigin{};                 // reference point R
  Vec3 heldPhysicsPoint{};
  float heldRuntimeRadius = 0;
  float heldDefinitionRadius = 0;
  Vec3 monitorDesiredFacing{};
  Vec3 monitorMovement{};            // processed (forward, left, up)
  bool precision = false;
  float boost = 1;
  std::array<float, 6> bounds{};
  Vec3 monitorReference{};           // monitor origin
  std::function<bool()> heldFullyOutside;
  std::function<Pose()> body0Transform;
  std::function<std::optional<Vec3>(Vec3& cachedPoint)> contact;   // returns normal
  // Magnet step: may rewrite the submission; returns the candidate (01 5.2).
  std::function<uint32_t(Pose& submission, bool& snapped)> magnets;
  Vec3 viewDirection{};              // for the mode-0 camera anchor
};
struct HeldResult {
  bool submitted = false;
  Pose submission;
  uint32_t magnetCandidate = kNone;
  bool snapped = false;
};
HeldResult UpdateHeld(Editor& e, const HeldWorld& w);

// ---------------------------------------------------------------- camera
float PitchCurve(float x);
float SpecArcsine(double t);
struct CameraInput {
  Vec3 heldPhysicsPoint{};
  Vec3 view{};                       // monitor desired view
  float definitionRadius = 0;
  // Prediction (05 A.3)
  bool predict = false;
  float dt = 0;
  Vec3 linearVelocity{}, angularVelocity{};
  Vec3 heldOriginNow{};
  bool hasBody = false;
  Quat heldOrientation{};
  Vec3 firstBodyLocalCenter{};
};
struct CameraPoint { Vec3 point{}, view{}; float distance = 0; Vec3 focus{}; };
CameraPoint HeldCamera(const Editor& e, const CameraInput& in);
struct RayHit { float fraction = 1; Vec3 point{}; };
struct FollowWorld {
  CameraInput camera;
  Vec3 monitorReference{};
  bool monitorContactActive = false;
  Vec3 monitorContactNormal{};
  std::function<bool(const Vec3&)> pointOutsideWorld;
  std::function<std::optional<RayHit>(const Vec3& from, const Vec3& to)> obstructionRay;
};
struct FollowResult {
  Pose monitorTarget;
  Vec3 facing{};
  float heading = 0, pitch = 0;
};
FollowResult MonitorFollow(Editor& e, const FollowWorld& w);
// 02 2.2 leash correction (mode-0 anchor).
Vec3 LeashCorrection(const Editor& e, const CameraInput& anchor, const Vec3& monitorReference);

// ---------------------------------------------------------------- physics
enum class PhysicsMode : uint16_t { Normal = 0x00, Fixed = 0x40, Phased = 0xc0 };
// 04 4.2. States 0..3.
unsigned SelectPhysicsState(PhysicsMode mode, bool variantObject, bool held,
                            bool hasKeyframedBody, bool settling);
struct PhysicsFlags { bool frozen = false, forceDynamic = false, keyframed = false, atRest = false; };
// 04 4.3 step 2 flag table. Returns false for states with no change (>3).
bool PhysicsStateFlags(unsigned state, bool localHolder, PhysicsFlags& flags);
// 04 4.3 step 5.
void CompensateHeldOffset(Editor& e, const Vec3& before, const Vec3& after);
// 04 4.1
uint16_t EditPhysicsProperty(uint16_t old, uint16_t value);

// ---------------------------------------------------------------- coordinates
struct CoordinateRange { float minimum, maximum, step; };
CoordinateRange PositionRange();
CoordinateRange AngleRange(unsigned snapMode);
unsigned RangeChoiceCount(const CoordinateRange& r);
float RangeChoice(const CoordinateRange& r, unsigned i);
unsigned RangeIndex(const CoordinateRange& r, float value);
struct CoordinatePanel {
  Vec3 position{};       // X, Y, Z (minus origin, rounded)
  Vec3 angles{};         // yaw, pitch, roll degrees (whole)
};
CoordinatePanel PopulateCoordinates(const Pose& pose, const Vec3& origin);
Pose CommitCoordinates(const CoordinatePanel& panel, float scale, const Vec3& origin);
// 04 5.5
void ApplyCoordinatePose(Editor& e, const Pose& pose, const std::array<float, 6>& bounds);

// ---------------------------------------------------------------- grab / spawn
struct GrabInput {
  bool hasBodies = false;
  Pose objectPose;
  std::array<float, 6> bounds{};
  Vec3 monitorPoint{}, monitorForward{};
  float runtimeRadius = 0;
  Vec3 heldPhysicsPoint{};
};
// 03 3.2 steps 8-10 (after selection and the physics transition).
bool InitializeGrab(Editor& e, const InputState& in, const GrabInput& g);
// 03 5.2 steps 3-4.
Vec3 PullSpawnPoint(const Vec3& requested, std::optional<Vec3> monitorPoint, float definitionRadius);

// ---------------------------------------------------------------- aim ray
struct AimResult { bool hit = false; uint32_t object = kNone; Vec3 point{}; };
float AimRange(const Editor& e);

}  // namespace forge
