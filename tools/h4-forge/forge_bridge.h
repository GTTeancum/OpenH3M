#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>
namespace advanced_forge {
// Original H4 menu values. These belong to private editor state only, never
// to an H3 variant record or its placement flags.
enum class PhysicsMode : uint16_t { Normal=0, Fixed=0x40, Phased=0xc0 };
// Original H4 runtime marker layout: two rigid transforms plus node metadata.
// Data providers supply local/world transforms; the original routines choose
// and align the pair. Marker metadata never enters the H3 saved variant.
using Marker = std::array<uint8_t,112>;
// Original big-endian render-model marker record, including region,
// permutation, node and the authored float at32. No inferred metadata.
using MarkerDefinition = std::array<uint8_t,48>;
struct Object {
 uint32_t datum{};
 std::array<float,3> position{};
 float radius{};
 std::vector<Marker> markers;
 // Candidate-model group existence (82937F50), independent of root-object
 // marker collection (82582610). Unspecified is for legacy diagnostic scenes.
 std::optional<bool> hasMagnetGroup;
};
struct Scene {
 std::vector<Object> objects; // held first plus at most64 query results: at most65 records
 std::array<float,3> cursor{};
 std::array<float,9> heldBasis{1,0,0,0,1,0,0,0,1};
 // Processed monitor movement, mapped from H3 unit+496/+500/+504.
 // Menu-only and legacy diagnostic scenes default to stationary movement.
 std::array<float,3> processedMovement{};
 unsigned sensitivity=2;
 // Private object indices in native spatial-query order. The held object stays
 // at storage index zero, but need not be first (or present) in query results.
 // Empty vector means an actual empty query; nullopt is legacy storage order.
 std::optional<std::vector<uint32_t>> nearbyOrder;
};
struct Result {
 bool snapped=false;
 uint32_t targetDatum=0xffffffff;
 std::array<float,4> rotation{};
 std::array<float,3> position{};
};
// The submission pose may be magnet-aligned; editor.bytes retains the
// unsnapped target. Do not feed this pose back into persistent editor storage.
struct HeldMagnetSubmission {
 std::array<float,13> pose{};
 uint32_t targetDatum=0xffffffff;
 std::vector<uint32_t> visibleObjects;
};
struct CoordinatePose {
 std::array<float,3> position{};
 std::array<float,9> basis{1,0,0,0,1,0,0,0,1};
};
struct CoordinateRange {float minimum,maximum,step;};
// Flags here use the original H4 layout in private memory. The native adapter
// must translate them; they must never be copied into an H3 object or save.
struct PhysicsBodyUpdate {
 uint64_t flags{};
 std::array<float,3> point{};
 bool hasInstance=true;
};
struct PhysicsTransition {
 uint32_t state{};
 uint64_t flags{};
 bool held=false,localHolder=false,hasPhysicsModel=true,hasInstance=true;
 std::array<float,3> point{},grabOffset{};
 float offsetScale=1,offsetDecay=0;
};
using PhysicsBodyAdapter=std::function<PhysicsBodyUpdate(uint64_t flags,bool create)>;
// Exact original per-player editor bytes. Construction requires a captured
// original initialization result; zero-initialization is not a grab operation.
struct HeldEditorState {
 explicit HeldEditorState(const std::array<uint8_t,336>& initialized):bytes(initialized){}
 std::array<uint8_t,336> bytes;
 // Host rendering bookkeeping belongs to this editor, not the shared bridge.
 // Original825827B0/82582950 create/remove markers for a specific player.
 // This vector is never copied into guest editor bytes or saved variants.
 std::vector<uint32_t> visibleObjects;
};

// Post-physics inputs for original82450E10's placement initialization.
// The caller queries these after ownership/selection/dequeue/physics updates.
// Original8244EF80 non-phased placement prefix. Budget/collision queries
// remain native integration services; this result precedes the collision query.
struct SpawnPlacement {
 std::array<float,3> point{};
 float radius=0;
};
struct GrabPlacement {
 uint32_t datum=0xffffffff;
 bool hasBodies=false,inputActive=false;
 std::array<float,13> pose{};
 std::array<float,6> variantBounds{};
 std::array<float,3> heldPoint{},monitorPoint{},monitorForward{};
 float radius=0,distanceInput=0;
};

// Original player1888..1907, kept separately from native H3 player storage.
struct ManipulationInputState {
 bool active=false;
 float distance=0,roll=0,yaw=0,pitch=0;
};
struct ManipulationInput {
 bool eligible=false,hasHeldObject=false,rotationAvailable=false;
 float trigger=0;
 std::array<float,2> movement{},look{};
};
struct ManipulationInputResult {
 ManipulationInputState state;
 std::array<float,2> remainingMovement{};
};

// Original H4-layout metadata for8244A6A8. Native adapters translate the
// type, flags and body motion classes explicitly; these never enter H3 saves.
struct RotationPhysics {
 uint8_t objectType=0;
 uint64_t objectFlags=0;
 bool hasInstance=false;
 uint32_t instanceFlags=0;
 std::vector<uint8_t> bodyMotion;
};

struct HeldSelectionWorld {
 bool localHolder=false;
 // Native counterparts of original82260B58 and8225EA20, respectively.
 std::function<std::array<float,3>(uint32_t)> objectPoint,objectReferenceVector;
 // Original82505DE8(player,0): controlled unit (H4 player36 / H3 player40).
 // Return -1 when the player has no controlled unit; this is not an aim query.
 std::function<uint32_t(uint32_t)> focusObject;
 std::function<void(const std::string&)> eventSink;
};
struct SelectionRayRequest {
 uint32_t layer=0;
 uint64_t flags=0;
 std::array<float,3> origin{},endpoint{};
 std::vector<uint32_t> exclusions;
};
struct SelectionRayHit {
 uint32_t category=0,datum=0xffffffff;
 std::array<float,3> point{};
 float fraction=1;
};
struct SelectionRayWorld {
 std::array<float,3> origin{},direction{};
 // Already selected by the original seatless-biped rule, in header order.
 std::vector<uint32_t> exclusions;
 int16_t heldVariantSlot=-1;
 std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)> query;
};
struct SelectionRayResult {bool hit=false;uint32_t datum=0xffffffff;};
// Geometry records consumed by original824863F8/82486220. The collector
// supplies these values; the bridge does not choose or rank collision hits.
struct ContactSample {
 std::array<float,3> normal{},closestPoint{};
 std::array<std::array<float,3>,3> triangle{};
 float planeDistance=0,closestDistance=0; // original record offsets12/16
};
struct ContactSet {
 int32_t primary=-1;
 float closestDistance=0; // original header4
 std::vector<ContactSample> samples; // original capacity256
};
struct ContactCollection {ContactSet geometry;uint32_t flags=0;};
struct SceneryContactWorld {
 // The native adapter must establish an unparented scenery/crate root.
 uint8_t objectType=6; // private H4 scenery6/crate11
 uint64_t objectFlags=0;
 uint32_t collisionFlags=0;
 float definitionRadius=0,tickInterval=0;
 std::array<float,3> velocity{},physicsPoint{};
 // Original global response fields16/20/24; must come from source data.
 std::array<float,3> responseSettings{};
 std::function<ContactCollection(const std::array<float,3>&,float,float)> collect;
 std::function<void(const std::array<float,3>&)> setLinearVelocity;
};
struct SceneryContactResult {
 bool contact=false;
 std::array<float,3> cachedPoint{},normal{};
 uint64_t objectFlags=0;
};
// Original82235650 biped branch, used only for the Forge monitor adapter.
// These are transient editor/runtime inputs, never H3 saved-layout fields.
struct MonitorContactWorld {
 SceneryContactWorld contact; // objectType must be original H4 biped0
 std::array<float,4> responseSettings{}; // original globals0/4/8/12
 std::array<float,3> previousNormal{}; // original player152 persists across suppressed calls
 uint8_t movementMode=0,surfaceFlags=0; // original unit3910/4015
 uint32_t surfaceTimestamp=0xffffffff,tick=0; // original unit2188/time12
 uint16_t tickRate=0; // original time4, consumed as signed16 by source
 // Original82943B08(held monitor,0,1,1,0), at its original call position.
 std::function<void()> surfaceNotification;
};
struct MonitorContactResult {
 SceneryContactResult response;
 uint32_t surfaceTimestamp=0xffffffff;
 uint8_t surfaceFlags=0;
};
struct ContactResolution {
 std::array<float,3> normal{};
 std::vector<uint32_t> contributingSamples;
 float distance=0,residualSquared=0;
};
// Snapshot of the selected native body, mapped to the original H4 controller.
// Four lanes preserve Havok vector/quaternion storage exactly.
struct ControlledBody {
 std::array<float,4> position{},orientation{},linearVelocity{},angularVelocity{};
 float angularResponseLimit=0; // native body344; encoded by original82C969B0 into H4 body411
 std::function<void()> activate;
 std::function<void(const std::array<float,4>&,const std::array<float,4>&)> relocate;
 std::function<void(const std::array<float,4>&)> setLinearVelocity,setAngularVelocity;
};
// Inputs consumed by unchanged8244A8D8. The host must map these from native
// state/services; zero/default stand-ins are not valid world implementations.
struct HeldUpdateWorld {
 bool localHolder=false,hasInstance=false;
 uint32_t bodyCount=0,tick=0,monitorDatum=0xffffffff;
 float tickInterval=0;
 std::array<float,3> desiredView{}; // H4 unit1212..1220, not current view1260
 bool movementFlag=false; // H4 unit1200 bit0
 float definitionMovementMultiplier=0; // monitor tag1428
 float movementMultiplierFraction=0; // monitor unit2168
 std::array<float,6> variantBounds{};
 std::function<std::array<float,3>(uint32_t)> objectMotion,objectReferencePoint;
 // Both outputs from one native physics snapshot, used by mode1 prediction.
 std::function<std::array<std::array<float,3>,2>(uint32_t)> objectVelocities;
 float heldDefinitionRadius=0; // H4 object definition32, native H3 definition4
 std::function<std::array<float,3>(uint32_t)> objectPhysicsPoint,objectPredictionLocalPoint;
 std::function<std::array<std::array<float,3>,2>(uint32_t)> objectOrientation;
 std::function<bool(uint32_t)> geometryContainsObject;
 // Original follow8244AF48 consumes only the boolean result from82415970.
 std::function<bool(const std::array<float,3>&)> pointOutsideWorld;
 std::function<std::array<float,13>(uint32_t)> bodyTransform;
 // Original82235650 is a contact RESPONSE, not a read-only normal query.
 // It may update cachedPoint even on a false/no-normal result, and applies
 // velocity/flags/notifications to the native object before returning.
 std::function<std::optional<std::array<float,3>>(uint32_t,std::array<float,3>& cachedPoint)> resolveContact;
};
struct MonitorFollowWorld {
 // Snapshot from the original monitor contact response, never guessed from
 // an unrelated native player field. The native producer remains required.
 bool contactActive=false;
 std::array<float,3> contactNormal{};
 std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)> query;
};
struct HeldUpdateResult {
 // Observed at original8244AB68, before its first bounds clamp.
 std::array<float,3> movementDelta{},referencePoint{},priorTarget{};
 // False is the original no-instance/no-body return, not a submission of zero.
 bool submitted=false;
 uint32_t submittedDatum=0xffffffff;
 std::optional<std::array<float,3>> viewAngles;
 // Exact original facing input, retained for native H3 two-angle controls.
 std::optional<std::array<float,3>> viewDirection;
 std::array<float,13> pose{};
 float controllerParameter=0;
 uint32_t targetDatum=0xffffffff;
 std::vector<uint32_t> visibleObjects;
};
class Bridge {
public:
 Bridge(const std::string& decodedImage,const std::string& forgeConfig);
 ~Bridge();
 Bridge(const Bridge&)=delete;
 Bridge& operator=(const Bridge&)=delete;
 Result Evaluate(const Scene& scene);
 // Original824499A8 editor reference, then82582250's exact query radius.
 float MagnetQueryRadius(const HeldEditorState& editor,
                         const std::array<float,3>& physicsPoint,float runtimeRadius);
 // Original8259E9A8, supplied with live node matrices and optional current
 // region permutations. Original code filters and caps the output at32.
 std::vector<Marker> BuildMarkers(const std::vector<MarkerDefinition>& definitions,
     const std::vector<std::array<float,13>>& nodes,
     const std::optional<std::vector<uint8_t>>& permutations,bool mirrored);
 // Original8249B418 target construction and82C01FB8 body controller.
 // Caller selects the body using82452930's routing and maps returned flags.
 uint64_t ControlBody(const std::array<float,13>& pose,float parameter,
                      const ControlledBody& body);
 //82939248's controller-flag branch: reverse one original tick of root
 // motion, then compose the attached node through the original math helpers.
 // Caller must prove original root/instance/flag eligibility and phase.
 std::array<float,13> CompensateAttachmentPose(const std::array<float,13>& root,
                     const std::array<float,13>& node,const std::array<float,3>& linear,
                     const std::array<float,3>& angular,float tickInterval);
 // Original82235650 scenery-root response. Native callbacks collect geometry
 // and apply its velocity request; returned flags/cached point must be applied.
 SceneryContactResult ResolveSceneryContact(const SceneryContactWorld& world,
                                     const std::array<float,3>& cachedPoint);
 // Includes original biped coefficients, surface timing and notification order.
 MonitorContactResult ResolveMonitorContact(const MonitorContactWorld& world,
                                     const std::array<float,3>& cachedPoint);
 // Pure original multi-plane response selection; native geometry collection
 // and the enclosing velocity/flag response are separate required stages.
 std::optional<ContactResolution> SelectContactResponse(const ContactSet& contacts,
                                  const std::array<float,3>& point,bool reverse);
 // Entire original held-update routine. Rotation/input processing precedes
 // this call. The native caller submits the returned target through its mapped
 // physics controller; it must not directly teleport or feed it into editor84.
 HeldUpdateResult UpdateHeld(HeldEditorState& editor,const Scene& scene,
                              const HeldUpdateWorld& world);
 // Entire original8244AF48 after the held-object update. Caller must submit
 // its returned monitor target, then apply the local view when present.
 HeldUpdateResult UpdateMonitorFollow(HeldEditorState& editor,const Scene& scene,
                 const HeldUpdateWorld& world,const MonitorFollowWorld& follow);
 // Original held-caller quantization stage: return the submission pose and
 // retain the last quantized basis according to8244ADA0..8244AF10.
 std::array<float,13> PrepareHeldSubmission(HeldEditorState& editor);
 // Execute original8244EED8 over a copy of the completed held target.
 // Scene supplies nearby objects/movement only: editor preferences, offset,
 // basis and target persist across frames. Local ownership controls visuals.
 HeldMagnetSubmission ApplyHeldMagnets(HeldEditorState& editor,const Scene& scene,
                                       bool localHolder);

 // Run the original editor constructor over supplied backing storage. Fields
 // not written by H4 are preserved; this initializes an editor, not a grab.
 HeldEditorState InitializeHeldEditorState(const std::array<uint8_t,336>& storage,
                                          const std::function<void(const std::string&)>& eventSink);

 // Original82D813F8 collision-group predicate. Inputs are physics filter-info
 // words, not object types or Forge ray request flags. The table is source data.
 // This is only the upstream layer gate; collector/exclusion gates still apply.
 bool CollisionGroupAllows(uint32_t queryInfo,uint32_t shapeInfo,
                           const std::array<uint32_t,32>& lookup);
 // Original8244C740 range, endpoint and persistent editor44/48/52 writes.
 // Query maps the native-world collision contract; no native flags are inferred.
 SelectionRayResult UpdateSelectionRay(HeldEditorState& editor,const SelectionRayWorld& world);
 // Active-biped branch of82452930: original8257FB98 flattens the requested
 // basis for the object's facing notification, then the controller receives
 // the source identity basis. Caller retains current up and submits the
 // orientation notification before the body target, as the source does.
 std::array<float,13> PrepareActiveBipedTarget(const std::array<float,13>& pose,
                                              std::array<float,3>& facing);
 // Original823FC348 basis-to-view conversion, including yaw wrapping.
 // Returns the three native-facing angle values only after the original
 // notification boundary. Caller must map the H3 view destination separately.
 std::array<float,3> ConvertMonitorView(const std::array<float,3>& forward,
                                       const std::array<float,3>& up);
 // Original824F5CF0/824F5F78 obstruction stage, called only after the enclosing
 // monitor-follow containment predicate succeeds. Updates editor228..263.
 void UpdateMonitorObstruction(HeldEditorState& editor,uint32_t monitor,float tickInterval,
               const std::array<float,3>& target,const std::array<float,3>& origin,
               const std::function<std::optional<SelectionRayHit>(const SelectionRayRequest&)>& query);

 // Original82449ED8 selection/reset, including retained preferences and events.
 // This is one stage of grab/release; native ownership and full grab ordering
 // remain the caller's responsibility. Datum IDs stay native at this boundary.
 std::vector<uint32_t> SelectHeldObject(HeldEditorState& editor,uint32_t player,
                                      uint32_t datum,const HeldSelectionWorld& world);

 // Per-editor cleanup from original8244C000, using the unchanged selection
 // and target setters. Returns whether the deleted object was selected.
 bool NotifyObjectDeleted(HeldEditorState& editor,uint32_t player,
                          uint32_t datum,const HeldSelectionWorld& world);

 // Finish the placement-state portion of original82450E10. Returns false
 // when the original no-body branch leaves placement fields unchanged.
 // This does not replace native ownership/variant transactions or notifications.
 bool InitializeGrabPlacement(HeldEditorState& editor,const GrabPlacement& input);

 // Original82282580 clamp used by grab initialization and the held update.
 // Bounds are native variant min/max pairs X,Y,Z; pose is scale/basis/position.
 // Returns a clamped copy, preserving scale and basis exactly.
 SpawnPlacement PrepareSpawnPlacement(const std::array<float,3>& point,
                    const std::optional<std::array<float,3>>& monitorPoint,float definitionRadius);
 std::array<float,13> ConstrainGrabPose(const std::array<float,13>& pose,
                                      const std::array<float,6>& bounds);

 // Original824500A8 event13: replace only the selected editor transform,
 // then constrain its point through original82282580. Caller validates the
 // native player/object ownership before crossing this boundary.
 std::array<float,13> ApplyHeldCoordinatePose(HeldEditorState& editor,uint32_t datum,
                                            const std::array<float,13>& pose,
                                            const std::array<float,6>& bounds);

 // Original82368CE0 dominant-axis selection and frame-packet consumption.
 // Caller maps semantic axes before calling and retains state between ticks.
 ManipulationInputResult ConsumeManipulationInput(const ManipulationInputState& prior,
                                                  const ManipulationInput& input);

 // Original rotation-input caller, blocking predicate, transform and offset
 // decay initialization. Persistent unsnapped pose stays in this editor state.
 void RotateHeld(HeldEditorState& editor,const ManipulationInputState& input,
                 const std::array<float,3>& monitorView,float tickInterval,
                 const RotationPhysics& physics);

 // Original H4 radius/config distance policy, including processed push/pull.
 // Caller supplies already-mapped H4 input; this API does not infer device signs.
 // No held object returns the original configured release/default distance.
 // Original8244D5E4..D60C, after rotation and before held/follow submission.
 void AdvanceHeldPlacement(HeldEditorState& editor,const ManipulationInputState& input,float radius);
 float ConstrainHeldDistance(float distance,float radius,bool inputActive,
                             float distanceInput,bool hasHeldObject=true);

 // Original H4 visibility transitions; returned IDs identify objects whose
 // markers the host renderer should draw. No helper objects enter H3's world.
 std::vector<uint32_t> UpdateVisibility(uint32_t held,uint32_t target,bool enabled);
 // Uses H4's coordinate editor constructor and commit/event path. Angles are
 // degrees in the original menu's yaw, pitch, roll storage order.
 CoordinatePose EditCoordinates(uint32_t datum,const CoordinatePose& current,
                                std::array<float,3> position,std::array<float,3> angles);
 std::array<float,3> CoordinateAngles(const CoordinatePose& pose);
 // Position and angle range/step from the original H4 editor constructor.
 std::array<CoordinateRange,2> CoordinateRanges();
 // Execute the original H4 masked-property setter in the isolated H4 arena.
 // The caller owns this transient H4 word; it must not be an H3 save field.
 uint16_t EditPhysics(uint16_t editorProperties,PhysicsMode mode);
 // Original four-state selector, distinct from the three menu values.
 // Host queries must establish the supplied body predicates; no approximation.
 uint32_t SelectPhysicsState(PhysicsMode mode,bool held,bool keyframed,
                             bool normalStateOverride,bool variantObject=true);
 // Executes original8244A2A0, calling the native adapter at its exact
 // create/rebuild boundary and compensating the held offset afterwards.
 PhysicsTransition TransitionPhysics(const PhysicsTransition& current,
                                     const PhysicsBodyAdapter& updateBody);
 // Retain original per-player offset state across a native physics transition.
 // The unsnapped transform and all unrelated original editor bytes are preserved.
 PhysicsTransition TransitionHeldPhysics(HeldEditorState& editor,
                                         PhysicsTransition current,
                                         const PhysicsBodyAdapter& updateBody);



private:
 MonitorContactResult RunContactResponse(const SceneryContactWorld& world,
                   const std::array<float,3>& cachedPoint,const MonitorContactWorld* monitor);
 HeldUpdateResult RunHeldStage(HeldEditorState& editor,const Scene& scene,
                 const HeldUpdateWorld& world,const MonitorFollowWorld* follow);
 struct Impl;
 std::unique_ptr<Impl> impl_;
};
}
