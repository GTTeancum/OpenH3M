# Warlock conversion: POC loading verified

Warlock MCC assets are converted into original Halo 3 Mythic cache structures in
Blackout's slot. OpenH3M and the original disc assets remain unchanged. This is a
map-specific proof of concept, not a general MCC converter or a fidelity claim.
The owner's successful solo collision/visual test covered the earlier checkpoint;
the expanded conversion has now passed a native loading check and still needs
the owner's gameplay testing.

## Loading repair verified

The owner's loading crash was traced to decal initialization. The converter had
compacted the scenario decal palette without remapping the 586 BSP runtime decal
indices. Both consumers now use the same remapping; the serialized build check
also rejects out-of-range BSP decal references. All 586 repaired entries resolve
to their authored source decal names.

Current staged map: `.local/integrated/lockout-decalfix.map`, SHA256
`ed8298b11375eb0c47c46069f3407a559e2d8931e9bace5f653c8696a72b025c`.
The existing launcher points to this repair. A native 135-second test reached
first-person Slayer on 2026-10-18: 448 decal initialization calls returned, five
resource hash checks passed, and no guest access violation occurred before the
watchdog stopped the child. The application's own capture at 120 seconds shows
the Warlock arena, first-person weapon and Slayer HUD. It also shows lighting /
shader noise; this is loading evidence, not a visual-fidelity or gameplay-parity
claim. Evidence is under `.local/decal-load-confirm/`; structural verification is
`.local/reports/decalfix-verification.json` and the build report is
`.local/reports/warlock-decalfix.json`.

The supported native diagnostic uses only the existing process-local controller
script and the application's native capture. No desktop input or capture is used:

```powershell
python -B tools/warlock-conversion/snapshot/tools/trace_loading.py `
  --project C:/X360/ISOs/H3M --exe D:/Programming/GitHub/H3M/OpenH3M.exe --capture
```

This diagnostic checks the exact supported executable hash before attaching its
build-specific breakpoints. It selects Custom Games, Blackout and Slayer, waits
for map readiness, then starts at 95 seconds. All output, cache and profile paths
are under a fresh `.local/loading-traces/` directory. It stops its own process at
135 seconds. The menu sequence assumes this disc's alphabetical map catalog and
a fresh profile; inspect logs/capture rather than assuming a future run succeeds.
The earlier A-only sequence selected Matchmaking and is no longer used.

## Inputs and build

Run from the Git checkout. Python 3.11+ and `requirements.txt` dependencies are
required. Keep any environment, pip cache and temporary files inside the project.
Private prerequisites are the original Mythic disc (including all donor maps and
`default.xex`), MCC Warlock workshop map, MCC Halo 3 FMOD sound bank and a local
vgmstream CLI. Assets and decoder binaries are not distributed here.

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project C:/X360/ISOs/H3M `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map `
  --basis ../../maps/lockout.map --xex ../../default.xex `
  --sound-bank "D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb" `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output ../integrated/lockout-final.map --report ../reports/warlock-final.json
```

All paths are configurable. `--disc-maps` defaults to PROJECT/maps. Use a fresh
output filename for rebuilding: existing maps are never overwritten. The original
disc Lockout is sufficient; **no earlier converted seed is required**. The builder
also accepts the old tested seed for historical comparison, but it is unnecessary.

The pipeline converts geometry/collision, decorators, lightmaps, terrain/water and
object materials, placements and variants, spawns, environment, audio, decals and
all seven Forge palettes. It copies scenario budget and object salts, replaces
visibility/audibility, clears unused script/editor blocks, and retains Blackout's
slot identity. Original simulation definitions remain alongside imported tags.
All 114 source scenario blocks are inventoried; newly populated unhandled blocks
or unsupported dependency layouts fail explicitly rather than silently dropping.

A same-directory temporary file is renamed only after serialized cache/tag checks.
Failures remove temporary maps and write their stage/error to the JSON report.
The report also records hashes, counts, imported tags and material approximations.
Audio decoder calls have a 45-second timeout and use project-local temporary files.

## Prepare and play

Prepare a fresh layout; this does not launch the game:

```powershell
python -B tools/warlock-conversion/snapshot/tools/warlock_handoff.py prepare `
  --project C:/X360/ISOs/H3M --game ../warlock-play --map ../integrated/lockout-final.map
```

Preparation checks file size, tag memory and the XEX-salted header hash. It creates
hardlinks to disc assets and the generated map, saving disk space. Never edit these
linked files in place. Existing game directories are refused; choose a fresh path
for another version. The original accepted `.local/test-game` layout is preserved.

```powershell
& tools/warlock-conversion/snapshot/tools/Run-Warlock.ps1 `
  -Project C:/X360/ISOs/H3M -Exe D:/Programming/GitHub/H3M/OpenH3M.exe `
  -Seconds 3600
```

The root `C:\X360\ISOs\H3M\Run-Warlock.cmd` is configured for this new layout and
calls the versioned script directly. Select **Custom Games > Blackout > Slayer**.
The launcher sends no UI input and takes no screenshots. Its default watchdog is
180 seconds; `-Seconds` can be 1–3600. On timeout it closes only its launched child.
For a data-only check use `warlock_handoff.py check --project ... --game ...`.

Each run writes `.local/warlock-runs/<timestamp-pid>/result.json`, `runtime.log`
and `console.log`. Temp/profile/cache destinations and the working directory are
inside that run directory. Reports include preflight failures, executable/map
hashes, process exit/watchdog status and a bounded excerpt of native failure logs.
An existing runtime instance prevents a parallel launch. Header preflight success
is **not evidence that gameplay loaded**. No EXE patching or debugger is required.

## Handoff evidence and limits

Current repaired map: 372,195,328 bytes, SHA256
`ed8298b11375eb0c47c46069f3407a559e2d8931e9bace5f653c8696a72b025c`.
The build imports 838 metadata records and all 162 Forge palette entries (161
non-null references). The report is `.local/reports/warlock-decalfix.json`.
Structural verification covers serialized registry addresses/salts/groups,
scenario coverage, Forge references, budget, cleared editor blocks and header
hash. The native loading check reached first-person Slayer; movement, audio, modes
and multiplayer have not been verified by the agent.

Known POC approximations include reduced texture resolution/mip coverage, native
reflection substitutions, frozen shader animation and selected original-disc
shader/material defaults. Detailed per-material notes are in the build report.
Audio, Forge interaction, all game modes, multiplayer and system link remain for
the owner's testing. Runtime compatibility is preserved by making map-side changes;
actual original-console/system-link compatibility is not certified.

The earlier owner-tested map remains `.local/candidate/lockout.map`, SHA256
`499f0516e016524f7f8a98ca580e4acb66c2b5d58403a5c755e4ed8f23de4279`.
It is retained as a fallback. Old standalone snapshot scripts document development history and are not the
supported build pipeline. The diagnostic command above is explicitly build-specific.
Do not copy the snapshot into another `.local/tools` directory or run its old
hardcoded diagnostic scripts; use the commands above directly from the checkout.

Only source/schema files belong in Git. Generated maps, logs, caches, screenshots,
private assets and binaries stay under the project `.local` and must not be pushed.
Keep the accepted fallback plus the current output; remove superseded generated
maps after checking their exact paths/hashes. Retain useful failure reports, prune
old run caches when no longer needed, and never recursively delete linked disc
asset directories without checking their resolved paths. Detailed development
history remains in Git rather than accumulating in this handoff.
