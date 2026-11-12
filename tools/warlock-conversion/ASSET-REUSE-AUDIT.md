# Required stock and shared asset audit

User instruction, 2026-10-28. Applies to every map conversion and every asset
type, including existing conversions as their assets are revised. Perform this
audit before selecting custom imports, then verify reuse in the native output.
Only the user can authorize an exception to the original-H3 asset policy.

## Before import

1. Record the stock target cache identity/hash and its original shared-resource
   files. Inventory the target's tags and dependencies: textures, materials and
   shader programs, models, animation, collision/physics, effects, sounds,
   gameplay objects and any other referenced groups.
2. Trace each resource-bearing tag through its resource record, location and
   page descriptors to its actual file, including `shared.map`. Distinguish
   resources merely listed in the cache from dependencies of active content.
   Record conditional/streamed use separately; static references do not prove
   simultaneous residency. Tags without streamed payload still need an audit.
3. Match source content to suitable original-H3 equivalents already available
   through the target and shared resources. Check function, supported shader
   features, geometry/markers, animation, playback and other relevant behavior;
   matching names alone do not establish equivalence.
4. Search other original H3 disc maps for remaining equivalents. A missing tag
   in the chosen target or editing-kit subset does not establish absence from
   H3. `shared.map` is a resource store; inspect references from level resource
   tables rather than assuming it has a standalone searchable tag database.
5. Reuse the suitable stock asset with its native dependencies and behavior.
   Import custom content only where no equivalent exists or a recorded user
   exception applies. Preserve genuinely map-specific geometry and authorized
   source scenery. Do not replace an unrelated asset just to reduce file size.

## Evidence per decision

Record source path/type and active role; stock donor path/type, cache identity
and tag index; relevant dependency/resource IDs and local/shared file locations;
whether it is already referenced by the target or newly required; equivalence
evidence; selected action; and any user exception. Mark unresolved matches as
unresolved, not as permission to import. Keep generated inventories under the
repository's ignored work directory and reusable audit code in source control.

## Native-output verification

- Confirm selected references resolve to the intended native donor and that
  its dependent resources are available in the target installation.
- Retain valid shared-page references instead of embedding duplicate payloads.
  Deduplicate newly imported local dependencies where the format permits.
- Do not modify original `shared.map`, change codecs unnecessarily, or re-encode
  native sound/texture data merely because an intermediate uses MCC resources.
- Report reused shared resources, reused local donor resources, new custom
  resources and unresolved cases separately. Track added bytes; cache file size
  is not peak Xbox 360 RAM usage.
- Verify resulting visuals, audio and behavior at runtime. Static resolution
  alone is not proof that an asset looks or sounds correct.

## Current Battle Canyon evidence

`tools/battle-canyon-rebuild/audit_stock_audio.py` traces the installed original
disc level sound-resource tables, including referenced shared pages. Its report
is `work/battle-canyon/rebuild/reference/stock-audio-inventory.json`.
`plan_stock_audio.py` records stock selections and verifies their native sound
dependencies. These tools cover audio only; they do not satisfy the all-asset
audit by themselves. The remaining asset groups require equivalent inventories
and reference checks before the rebuilt map can be accepted.

`audit_shared_assets.py` additionally inventories every tag group and resolves
all resource-owner records in the stock target. Its report identifies shared
textures, models, animation and sound resources without assuming that ownership
proves active use or residency. `compare_stock_effect_bitmaps.py` found five
pixel-identical effect textures at different H3 paths; `reuse_stock_effect_assets.py`
retargets their staged references and the verified native drip sound. Flare
textures with different pixels remain unresolved. This is evidence-based reuse,
not a blanket filename substitution or a completed all-asset acceptance audit.
