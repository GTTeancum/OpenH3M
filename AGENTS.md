# Build and test artifact retention — user instruction, 2026-11-07

- Do not let generated files, builds, caches, logs or temporary test installations balloon.
- Retain one current candidate, one necessary rollback, and compact verification evidence for active work; do not accumulate successive full copies.
- Remove temporary test installations and superseded generated outputs after each run, once the process has exited and the useful evidence has been retained.
- Check repository artifact disk usage before staging another run. Reuse staging and caches where practical instead of duplicating them.
- Preserve source files, original assets, the shared installed build, accepted corrections and the retained rollback. Verify exact repository-confined paths before cleanup; do not recreate material the user discarded unless it is necessary for current work.
- All retained artifacts and temporary files remain inside this repository.

# Git workflow

- User instruction, 2026-10-28: always work on and push to `main`.
- Do not create or use another branch unless the user explicitly requests one.
- Merge existing branches into `main`; preserve uncommitted work when switching.

# Map conversion instructions

- User 2026-10-29: omit the dice from Battle Canyon. This supersedes retaining
  it in this map; preserve its unfinished library artifacts for possible reuse.


- Reach Forge dice exception, user 2026-10-29: retain the dice, textures,
  normal-mapped pips and physics, but omit the pips' view-dependent parallax
  depth. Record this reusable object conversion decision in the Reach-to-H3
  process; it does not authorize removing parallax from other materials.

- User instruction, 2026-10-28: retain converted Reach Forge objects for other
  maps. Consult `tools/reach-forge-library/README.md` and verify its catalog before
  repeating conversion work. Reuse matching assets and preserve their correction
  evidence. Cleanup must protect cataloged assets; keep unfinished/native-unverified
  entries clearly distinguished from accepted assets. Avoid duplicate asset builds.

- Battle Canyon sequencing, user 2026-10-28: lighting goes last. Keep the
  existing Draft lighting for the updated-map walkthrough. The user's walkthrough
  and remaining conversion corrections precede the final lighting bake.

- Battle Canyon, user 2026-10-28: remove the decorative Spartan doll. Exclude
  its placement and palette dependency from regenerated scenarios.



- Attribution, user 2026-10-25: every map conversion report must state the

  original map/game, exact source port/package and link, and credited source

  conversion author. Distinguish upstream authorship from this project's

  Xbox 360/OpenH3M adaptation. Verify credits; label unknown attribution rather

  than guessing. Maintain tools/warlock-conversion/MAP-CREDITS.md.



- Brightness correction, user 2026-10-25: per-map brightness fixes are authorized

  for the installed conversions even if their original H3 MCC ports are dark.

  Tune maps individually; source fidelity is not a reason to retain excessive

  darkness. Preserve core compatibility and avoid one global brightness change.



- User priority change, 2026-10-25: defer unfinished conversions to TODO.MD.

  Focus on corrections/performance for today's installed Battle Canyon,

  Rodentia, Lockout, 3longation and Sanctuary. Investigate darkness, choppiness,

  frame-rate drops and other incomplete issues. 3longation's conveyor force

  works but its visible track does not animate. This supersedes continuing

  High Noon or the remaining batch as the current work priority.



- Powerhouse exception, user 2026-10-25: omit its MCC-only sun-lightshaft post effect. Retain its sky, sun flares, animated clouds/dust, mist, lighting, bloom and other supported camera effects. This exception is specific to Powerhouse.



- Chiron decision, user 2026-10-23: remove the decorative CE marine placement from the HGC Chiron conversion.



## Binding Halo 3 asset policy � user instruction, 2026-10-20



- This policy applies to the entire map conversion process, all maps, and future replacement or DLC builds.

- Whenever an asset already exists in original Xbox 360 Halo 3, reuse that stock Halo 3 asset and its native dependencies, visuals, animations, physics, audio, and gameplay behavior.

- Convert/import custom or MCC assets only when no Halo 3 equivalent exists. Check the original disc maps and shared resources before declaring an asset unavailable; absence from the chosen replacement map is not absence from Halo 3.

- Do not substitute Halo 2-faithful variants, MCC variants, altered tuning, or custom approximations for existing Halo 3 assets.

- Preserve custom map geometry and authored placement while applying this asset-selection policy. Retain the requested full Forge palette using Halo 3 equivalents where available.

- Only the human user can override this policy. Agent judgment, source-map preferences, convenience, and prior conversion choices do not authorize exceptions. Record any explicit user override and its scope.

- Keep original disc assets unchanged; perform conversion relocation/remapping in the generated cache and conversion tools.

- Shared-resource audit, user 2026-10-28: before importing/converting custom
  assets, audit what assets of every type the stock target already loads from
  shared.map and reuse suitable stock assets/resources wherever possible.
  This is not audio-only: include textures, materials/shaders, models, animations,
  effects, sounds and their dependencies. Trace actual tag/resource references;
  an asset name or a shared-page descriptor alone does not prove active use.
  Also check other original H3 maps for equivalents. Record donor identity,
  resource location, reuse decision and any explicit exception in the conversion
  evidence. Preserve original shared.map; do not duplicate its payload into a
  custom map unnecessarily. See tools/warlock-conversion/ASSET-REUSE-AUDIT.md.

- User clarification, 2026-10-20: engine/host-runtime patches for smoothness are authorized. Preserve compatibility with the original Xbox 360 core: gameplay rules, simulation rate, map formats, stock asset behavior, and system-link semantics. This supersedes the earlier blanket prohibition on modifying OpenH3M, only for this scope. Do not claim system-link compatibility verified without testing it.



- Forge World exception, user 2026-10-21: remove custom Forge objects and replace Reach weapons/vehicles with original Halo 3 assets. Sandbox is the selected replacement slot. The earlier full-custom-palette requirement applies to the previous conversions, not Forge World. Preserve original Xbox 360 budgets and core compatibility.



- Forge Gulch scenery exception, user 2026-10-22: retain the original Reach Forerunner scenery objects in Forge Gulch, including its Forge scenery selection; do not replace those objects with Halo 3 equivalents. This supersedes the blanket stock-Sandbox scenery policy for those objects only. Halo 3 weapons/vehicles and the original Xbox 360 budget/core-compatibility constraints remain binding. Unrelated custom objects are not authorized by this exception.

- Force Cove clarification, user 2026-10-22: keep Reach Forerunner scenery pieces on both halves (Forge Gulch and Force Cove). The same narrow scenery exception applies to both; weapons, vehicles and other existing Halo 3 assets remain stock Halo 3.

- Reach layout decision, user 2026-10-23: port Hemorrhage, Asylum, Pinnacle, Paradiso and The Cage as selectable saved Forge layouts sharing Gulch/Cove's map data. Do not duplicate the base maps into five separate main-map entries. Saved-content containers are authorized for these layouts; the shared base maps remain in the LIVE bundle.



- DLC clarification, user 2026-10-22: target OpenH3M and RGH/JTAG. Narrow custom-content validation changes are authorized on both targets so the LIVE bundle and custom metadata can load. This supersedes the earlier retail-only/no-authentication-exception constraint for this bundle. Preserve original gameplay, physics, map formats and network semantics. Do not claim retail acceptance or tested system-link compatibility. Keep the four custom identities alongside stock maps.

- Advanced Forge, user 2026-10-23: build a PC-only Advanced Forge mode first; prioritize its programmatic editing behavior over Halo 4 object matching. Preserve original Halo 3 saved-layout formats and Xbox 360 gameplay compatibility. This authorizes the host-side Forge editor integration; it does not authorize changing console gameplay rules.



- Advanced Forge correction, user 2026-10-23: use ReXGlue on Halo 4 and derive Advanced Forge from its actual program logic. Do not build a bespoke replacement snapping system. Halo 4 itself need not run. This supersedes the earlier implementation interpretation.



- Battle Canyon, user 2026-10-25: simplify rock and terrain collision as needed for original Halo 3 format limits while preserving visible geometry. This does not authorize raising engine limits.



- Boarding Action, user 2026-10-25: remove the CE-style health-pack placements and their Forge entries. This is a map-specific exception.



- Source-policy override, user 2026-10-25: Boarding Action, Desolation, Haven and Sword Base are straight ports from their original games (Halo CE, Halo 2, Halo 4 and Halo Reach respectively), rather than H3 MCC custom remakes. Verify source edition/cache before conversion. This changes source selection; existing stock-H3 gameplay-asset policy and original Xbox 360 compatibility/budget requirements remain unless the user overrides them. Boarding Action and Desolation remain deferred; High Noon remains active.


- User priority update, 2026-10-26: resume conversions in this order: Reflection,
  Sword Base, Powerhouse, Sky Bridge, Desolation, High Noon, Boarding Action,
  Erosion, Impact, Haven. Ignore the duplicate Reflection entry (explicitly
  confirmed). Penance, Breakneck, Diamondback and Reactor are shelved. Forge
  Island was omitted; retain pending/unprioritized rather than invent a slot.
- Boarding Action source-policy override, 2026-10-26: keep the H3 MCC conversion
  if it can achieve a measured solid 30 FPS with acceptable visuals. This
  supersedes the earlier requirement to discard it for a direct CE port.
  Preserve the removal of health packs. Verify traversal/frame pacing, not
  only displayed FPS. Do not silently accept lower performance.


- Battle Canyon restart, user 2026-10-27: rebuild from original Reach assets through the established Foundry/Reclaimer -> Blender -> H3 Editing Kit -> H3 MCC pipeline, then adapt to original H3/OpenH3M. Supersedes using the existing compiled H3 MCC port as this rebuild input. Preserve installed maps until the replacement passes checks; keep stock H3 gameplay assets and native budgets. See tools/battle-canyon-rebuild/README.md.

- Reach conversion gravity-lift exception, user 2026-10-28: if stock H3 lift forces
  or exit direction do not fit the authored passages, copying the relevant
  Reach item values is authorized for Reach-to-H3 conversions. Keep native H3 formats
  and the engine unchanged. This is a narrow exception to stock-asset tuning,
  not permission to retune unrelated assets. Stock values remain the first
  candidate until traversal identifies a need. Record source/target field semantics
  and units before copying values; see tools/warlock-conversion/REACH-CONVERSION-PROCESS.md.

- Reach health stations, user 2026-10-28 (scope clarified the same day): retain
  their appearance as nonfunctional scenery in Reach-to-H3 conversions. Do not
  add healing behavior to the original H3 core. Battle Canyon's four stations
  are an implementation of this reusable rule, not its scope limit. Earlier
  map-specific instructions removing CE-style health packs remain unchanged.

- Reach Forge decision, user 2026-10-28 (scope clarified the same day): replace the Reach armor-ability
  category with stock Halo 3 equipment. Do not implement Reach armor abilities
  or change the original H3 core to support them. Other palette categories remain
  subject to the existing stock-asset policy. Applies to Reach-to-H3 conversions
  overall, not only Battle Canyon.

- Decision documentation, user 2026-10-28: put today's reusable conversion
  decisions, and further reusable findings, in
  tools/warlock-conversion/REACH-CONVERSION-PROCESS.md. Do not confine a general
  Reach-to-H3 rule to the Battle Canyon implementation notes. Keep map-specific
  paths, counts and evidence in those notes and link to the shared rule.


- User decision, 2026-11-03: omit Battle Canyon's three unsupported ambient
  mist/drip plane emitters rather than approximate them with H3 line emitters.
  They belong to ca_bc_mist (two emitter layers) and ca_beaver_dripping_point
  (one emitter), occurring in eight effect-scenery placements in total. Preserve
  the rainbow, sun flare and laser effects. This omission is specific to these
  Battle Canyon effects; it does not authorize stripping other maps' atmosphere.


- Powerhouse performance steering, user2026-11-11: prioritize concrete optimizations and visual/preservation checks over repeated attempts to obtain clean FPS baselines. User says clean baselines will not be available for the foreseeable future. Known polygon reduction is actionable; record the actual reduction without claiming an unmeasured FPS gain. Leave concurrent applications running.
