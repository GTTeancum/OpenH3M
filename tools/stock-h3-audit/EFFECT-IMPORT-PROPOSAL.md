# Battle Canyon effects: proposed narrow exception

Status: proposal only. The user requested a proposal, not an implementation.

Retain the original Reach rainbow and three decorative laser variants rather
than substitute weapon effects. Limit the exception to these four effect roots
and their necessary visual dependencies. All other asset selection remains
stock H3 first. No engine changes or bespoke conversion code.

Verified source references, read through official ManagedBlam:

| Source root under `levels/dlc/cex_beaver_creek/fx` | Required visual components |
| --- | --- |
| `ca_beaver_rainbow.effect` | Rainbow lens flare and rainbow particle |
| `laser_emitter.effect` | Original effect's referenced beam/flare/particle assets |
| `laser_emitter_skyward.effect` | Original skyward variant's referenced visual assets |
| `laser_emitter_alt.effect` | Laser and anamorphic lens flares, alternate beam system, cyan plasma and alternate beam particles |

Exact references and field paths are in
`work/stock-h3-audit/reach-source-references.json`, `effect_references`.
No direct stock equivalent has been established; this is not a claim that every
stock effect has been visually compared. Sun flare, mist and dripping effects
are outside this proposed exception.

Proposed execution after approval:

1. Establish an existing community-tool path for these effect types into H3
   editing tags. Foundry's geometry importer does not establish that capability.
   No working cross-game effect importer has yet been verified here.
2. If that path exists, import only these roots and necessary dependencies in
   the repository, using original Reach inputs and official H3 tools for the
   destination. Record exactly which non-stock dependencies are required.
3. Compile and test in H3 MCC, with the user driving. Check beam placement,
   direction and length, rainbow appearance, transparency, clipping and motion.
   A successful build is not acceptance. These checks remain part of approval
   of the complete MCC map, not permission to start 360 conversion early.
4. If the established tools cannot preserve a component, report that specific
   limitation for a new decision. Do not invent a converter, patch the engine,
   approximate it with another effect, or silently omit it.

Approval requested: permission for this bounded exception and tool-supported
import attempt. This proposal does not guarantee current tool compatibility or
later Xbox 360 compatibility. Neither has been demonstrated for these effects.
