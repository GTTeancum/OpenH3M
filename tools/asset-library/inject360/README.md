# Inject360 — MCC Halo 3 map content → original Xbox 360 Halo 3 maps

New code on top of XboxChaos Assembly's **Blamite** library (GPL-3.0, cloned to
`C:\Programming\GitHub\OpenH3M\.local\asset-tools\src\Assembly`). Blamite supplies cache-file reading/writing,
plugins and the tag injector; everything that crosses platforms is written here.

Build: `dotnet build -c Release C:\Programming\GitHub\OpenH3M\tools\asset-library\inject360\Inject360.csproj`
(output `C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\bin\Release\net48\Inject360.exe`).

## Commands

| Command | What it does |
|---|---|
| `port <mcc map> <360 map> <output map> <root tag>... [--retarget grp:old=new]...` | walks the roots' dependencies in the MCC map, reuses every tag the 360 map already has (same group + name), translates the rest to the 360 layout, converts their resources, injects them into a **copy** of the 360 map, optionally points scenario / multiplayer-globals references at the new tags, then rewrites the map's integrity values |
| `plan <mcc map> <360 map> <root>...` | the dependency walk only (what would be converted / reused) |
| `dump <map> <group> <name>` | every field of one tag, as text (compare MCC vs 360) |
| `res <map> <group> <name> [dir]` | a tag's resources: control bytes, fixups, pages, optional payload dump |
| `verify <360 map>` | recomputes the body checksum and the three salted header digests and compares them with the stored ones |
| `resave <in> <out>` | control experiment: load + save + integrity with nothing injected |
| `graft <donor 360 map> <target 360 map> <output map> <tag>...` | copies tags between two maps of the same engine unchanged, with their dependencies (used to borrow a stock shader template, with its compiled shaders, from another stock 360 map) |
| `templates <mcc map> <360 map> <folder of stock 360 maps> <root>...` | for every shader template the roots need, finds the same template (or failing that the closest) in any stock 360 map and prints the `graft` lines that bring it into the target |
| `texverify <mcc map> <360 map>` | converts every texture both maps share and compares the result with the real 360 bytes (padding ignored; DXN compared by decoded value because MCC re-compressed it) |
| `texscan <360 map>` | one line per stock texture: size, levels, type, format, fetch word, sizes |
| `animverify <mcc map> <360 map>` | the same check for animations |
| `sndinfo <map> <name part> [limit]` | how a map describes a sound: tag fields, codec, pitch ranges, permutations, chunks, resource |
| `check <map> <name part>` | every tag reference, block pointer and string id in the matching tags |
| `strings <map> <key part>` | which string lists hold a key, with the English text |
| `probe`, `zonerow`, `tiletest`, `pagehash` | inspection helpers |

`port_forge_world.ps1` is the recipe for Forge World's DMR (sounds from the Reach 360 game); `port_spectre.ps1` adds the
Spectre from Ultimate Forge 2.0's Mombasa Sandbox. `port_asset_library.ps1` is the recipe for this project's own rebuilt objects.

## What gets converted

| Part | Method | Verified against |
|---|---|---|
| Tag data | plugin-driven field translation (MCC plugin → 360 plugin, matched by type + name), little → big endian per field, every pointer / tag / string / resource reference moved to its new offset | — |
| Tag functions | header + opcode-specific payload swap | — |
| Shaders (`rmsh` and other render methods) | the PC compiled template is replaced by the original 360 template; options mapped to the 360 option count; textures and constants re-ordered **by parameter name** onto the 360 template; missing values from the 360 option defaults; nearest 360 template when the exact one is not on the map (cost: bump on = neutral, misc minor, alpha test / blend never) | three stock shaders ported MCC → 360 came out identical to the original 360 data |
| Textures | MCC linear BC/ARGB levels → Xenos tiled layout with packed mip tail, 8-in-16 / 8-in-32 byte order, DXN endpoint bias, 360 texture header | stock battle-rifle texture: every texel byte identical (only unused padding differs) |
| Model geometry | vertex formats rigid / skinned / world (positions and UVs swapped, normals/tangents/binormals packed to 10:11:11), PRT, index buffers, 360 control layout | layout matches stock 360 models |
| Animations | codec streams endian-converted without resampling, member names re-issued as 360 string ids | — |
| Integrity | page CRC + three salted SHA-1s; header body XOR checksum + three salted digests (salt from `default.xex`, stored at `C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\resource_salt.bin`) | reproduces the stored values of stock `sandbox.map` and `guardian.map` and of a stock page |

## Added 2026-11-20 (each checked against stock 360 data where both games share the asset)

| Part | Method | Verified against |
|---|---|---|
| Textures, all layouts | tiled and untiled (stock stores many small single-level textures as plain rows at a 32-block pitch; ported textures are always written tiled, with the fetch word's tiled bit set) | `texverify` on the MCC test map vs stock Sandbox: every comparable texture in formats 9, 11, 14, 15, 16, 25 identical; the two that differ are different pictures in MCC |
| Cube maps | MCC stores level by level, unsplit; the 360 stores the top level of all six faces in the secondary page and the rest in the primary, six 4 KiB-aligned face slices per level, faces 1 and 2 exchanged | all ten cube maps both maps share identical (formats 11, 14, 16) |
| Texture formats without a 2007 equivalent | 28 (16-bit RGBA) -> 8-bit ARGB; 29 (16-bit two-channel normals) -> DXN, encoded here | no stock counterpart; by construction |
| Formats 0-3 (A8, Y8, AY8, A8Y8) | fetch words read from stock textures | fetch words only |
| Shader templates the target lacks | `templates` searches every stock 360 map for the same template, else the closest one, and `graft` copies it in; what stays approximate is logged with the options that differ | Forge World objects: 31 needed, 18 on Sandbox, 4 exact and 9 closer ones borrowed |
| Render methods inside other tags (decal systems, contrails, light volumes) and templates whose name is the same on both sides (decals, particles) | re-mapped like any other shader (they were being left in PC layout) | mortar scorch decal in game |
| Particle-model vertices (format 25) | floats -> unsigned 16-bit position / texcoord, 10:11:11 normal | positions and texcoords identical to stock; normals within one step |
| Resource "data present" bits | set from what the converted resource actually holds (1 = primary block, 3 = primary and secondary), never copied from MCC: MCC sound resources hold no data, and a sound copied with 0 is silent on the 360 | stock values read from Sandbox |
| Identity functions | MCC stores an identity tag function as type 0 with no payload (32 bytes); the 2007 engine has no such type and stock 360 tags hold the same function as type 8 with one linear segment (52 bytes). Converted on the way through, with the data reference length updated | ported DMR damage-effect function equals the stock battle rifle one byte for byte |
| Effect event length | one-tick events are 1/60 s in MCC and 1/30 s on the 360 (same stock effect in both games); converted | - |
| MCC-only material models | shaders that use a material model added after 2007 (options 8-16) take the original model it derives from: cook_torrance, or two_lobe_phong for two_lobe_phong_tint_map | Spectre hull in game |
| Effect flags | MCC inserted two flag bits at positions 8 and 9; higher bits are moved down two places. The 360 uses them, among other things, to play an effect's sound parts | same stock effects in both games: battle rifle firing 0x1402 / 0x502, wraith mortar firing 0x802 / 0x202 |
| Sounds | two sources. `--sound-donor <360 map>` (with `--sound-donor-prefix` for a prefix the mod added to the name): the same-named sound from an Xbox 360 map (Halo 3 or Reach) is copied byte for byte, XMA and all. Otherwise each permutation is decoded from the MCC FMOD bank with vgmstream, resampled to 44.1 kHz and encoded to XMA2 with the Xbox 360 SDK encoder (xma2encode.exe); big-endian PCM is only the fallback when the encoder is missing, and PCM was silent in play tests. Either way the sound resource gets its size record (the 360 learns the data length from it), is stored uncompressed like stock sounds, and its rows go in through Blamite's sound injection | Reach-donor sounds confirmed audible in play (DMR, 2026-11-20); encoder output compared with a Reach chunk of the same sound (same packet layout, block size and sample count) |

## Not yet converted (logged per tag, never silently dropped)

Shader templates no stock 360 map has (the 360 shader compiler is not available, so those shaders run on the nearest
stock template); localized (dialogue) sounds and sounds with lipsync data; the newer animation encoding some MCC mods
use (codec 9); array and volume textures; unic string lists (prompt strings are added with `--add-string`).
