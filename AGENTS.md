# Git workflow

- User instruction, 2026-10-28: always work on and push to `main`.
- Do not create or use another branch unless the user explicitly requests one.
- Merge existing branches into `main`; preserve uncommitted work when switching.

# Map conversion instructions

## Binding Halo 3 asset policy � user instruction, 2026-10-20

- This policy applies to the entire map conversion process, all maps, and future replacement or DLC builds.
- Whenever an asset already exists in original Xbox 360 Halo 3, reuse that stock Halo 3 asset and its native dependencies, visuals, animations, physics, audio, and gameplay behavior.
- Convert/import custom or MCC assets only when no Halo 3 equivalent exists. Check the original disc maps and shared resources before declaring an asset unavailable; absence from the chosen replacement map is not absence from Halo 3.
- Do not substitute Halo 2-faithful variants, MCC variants, altered tuning, or custom approximations for existing Halo 3 assets.
- Preserve custom map geometry and authored placement while applying this asset-selection policy. Retain the requested full Forge palette using Halo 3 equivalents where available.
- Only the human user can override this policy. Agent judgment, source-map preferences, convenience, and prior conversion choices do not authorize exceptions. Record any explicit user override and its scope.
- Keep original disc assets unchanged; perform conversion relocation/remapping in the generated cache and conversion tools.
- User clarification, 2026-10-20: engine/host-runtime patches for smoothness are authorized. Preserve compatibility with the original Xbox 360 core: gameplay rules, simulation rate, map formats, stock asset behavior, and system-link semantics. This supersedes the earlier blanket prohibition on modifying OpenH3M, only for this scope. Do not claim system-link compatibility verified without testing it.

- Forge World exception, user 2026-10-21: remove custom Forge objects and replace Reach weapons/vehicles with original Halo 3 assets. Sandbox is the selected replacement slot. The earlier full-custom-palette requirement applies to the previous conversions, not Forge World. Preserve original Xbox 360 budgets and core compatibility.

- Forge Gulch scenery exception, user 2026-10-22: retain the original Reach Forerunner scenery objects in Forge Gulch, including its Forge scenery selection; do not replace those objects with Halo 3 equivalents. This supersedes the blanket stock-Sandbox scenery policy for those objects only. Halo 3 weapons/vehicles and the original Xbox 360 budget/core-compatibility constraints remain binding. Unrelated custom objects are not authorized by this exception.
- Forge Island clarification, user 2026-10-22: keep Reach Forerunner scenery pieces on both halves (Forge Gulch and Forge Island). The same narrow scenery exception applies to both; weapons, vehicles and other existing Halo 3 assets remain stock Halo 3.

- DLC clarification, user 2026-10-22: target OpenH3M and RGH/JTAG. Narrow custom-content validation changes are authorized on both targets so the LIVE bundle and custom metadata can load. This supersedes the earlier retail-only/no-authentication-exception constraint for this bundle. Preserve original gameplay, physics, map formats and network semantics. Do not claim retail acceptance or tested system-link compatibility. Keep the four custom identities alongside stock maps.
