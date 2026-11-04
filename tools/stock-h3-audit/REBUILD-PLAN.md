# User-approved fresh Battle Canyon process

Approved 2026-11-03. Execute these steps in order. The rejected Battle Canyon
implementation is not an input to the new work.

1. Permanently delete the rejected Battle Canyon work: custom scripts, generated
   assets, builds, backups and installed copies. Preserve original game assets,
   other maps and the established shared MCC-to-Xbox-360 conversion tools.
2. Establish the stock-H3 list using original Xbox 360 Standoff and its vehicle-free
   Forge palette. Consult other stock maps for missing needs only. The fresh
   TagTool inventory is documented in README.md and is not old Battle Canyon work.
3. Before authoring, match stock objects and their dependencies to H3 MCC mod-tool
   tags. Identify MCC-only additions/changed behavior. Consult the user for any
   required feature without a stock-H3 alternative; do not fabricate one.
4. Start fresh from original Reach assets through the established Halo mod tools.
   Use stock H3 items, materials and effects. No unapproved custom fixes.
5. Import, compile and light for Halo 3 MCC with the official tools. Automation
   scripts may run existing tool commands; this is not permission to implement
   replacement asset/shader/conversion logic.
6. Test in actual Halo 3 MCC, with the user driving. Compare Reach references and
   inspect materials, sky, clipping/flicker, collision, traversal, audio,
   gameplay and Forge. Resolve problems in this stage.
7. Obtain the user's explicit MCC approval. No Xbox 360 conversion before it.
8. Use the established H3 MCC-to-original-H3 Xbox 360 conversion, reusing verified
   stock assets. Consult the user on unexpected compatibility problems.
9. Validate converted appearance, behavior, performance and native limits, then
   deploy to the shared installation. Build success alone is not acceptance.

All project writes stay inside this repository. No desktop/OS input or capture
app. Coordinate shared-content changes with the Sky Bridge chat. Do not restore
the rejected map from any backup, trace fixture or historical commit.

## Step 1 execution state (historical initial blocker)

Deletion inventory and protection hashes are in `work/retirement-20261103`.
The initial scope contains 3,381 targets and 17,316 files (about 106.64 GiB
logical size), with no reparse points found in the selected directories. Original
Reach editing-kit source tags are excluded. The generated Reach Forge library
from the rejected attempt is included; the newer explicit deletion instruction
supersedes the older instruction to retain those attempt-derived artifacts.

Both deletion attempts were rejected before execution by the execution tool's
automatic policy review, with reason `blocked by policy`:

- Repository-confined manifest deletion with resolved-path checks.
- Narrower nonrecursive removal of the seven explicitly named installed Battle
  Canyon map/metadata/preview files.

No files have been deleted. No bypass or alternative deletion mechanism is
authorized by this document. Steps 2 onward remain gated by step 1. Additional
renamed copies, combined packages, shared-file fragments and historical Git
copies still require inspection before a complete deletion claim is possible.

## User-directed transition after external cleanup

The user assigned cleanup to Claude. A subsequent read-only check confirmed the
dedicated rebuild source/work folders, generated scenario directory, installed
Battle Canyon map, cleanup inventory and handoff file were gone. Residual
Battle Canyon-specific branches in shared converter files and five historical
Git commits were reported to the user. The user explicitly replied **"Just move
on"**. This authorizes advancing to stock-asset matching without asserting a
complete historical purge. Do not reopen that cleanup gate unless the user does.
Do not restore or reuse the rejected implementation. No old code was copied into
the fresh stock audit. All later MCC testing and user-approval gates remain.
