#!/bin/bash
# build_map.sh <map .cfg> <output map>   Repeatable Reach 360 -> Halo 3 360 map build (map-agnostic).
# Everything map-specific comes from the .cfg (tools\reach360-port\maps\*.cfg). Steps:
#   1. lightmaps: lmconvert (TagTool's converters) for every Reach Lbsp missing from the lightmap folder; the scenario's
#      sky_atm_parameters values from TagTool's Reach skya generation (lmconvert --skya)
#   2. port: the map (structure, lighting, materials, sky, scenery and placements) from the Reach scenario; TagTool's
#      Reach rules run inside the porter (lighting, shaders, scenario: ReachScenario.cs). Gameplay is stock Halo 3
#      (tools\warlock-conversion\REACH-CONVERSION-PROCESS.md, "Scope and invariants" / "Reusable user decisions" /
#      step 5): Reach weapons, equipment (including armor abilities), vehicles and bipeds are never converted; placed
#      ones become the cfg's stock Halo 3 assets, every other reference to them is cleared. Reach audio and animation
#      are not converted yet (stock reuse first); their references are cleared and listed as unresolved.
#      <output>.unresolved.txt lists every Reach tag that was not converted and why.
#   3. the ported scenario becomes the map's scenario (global tag table); the slot's map id is kept; the zone tag gets one
#      BSP zone per structure BSP
#   4. Forge palettes: the basis scenario's stock Halo 3 sandbox blocks are shared into the ported scenario
# Needs: ReachPort (bin\dev), lmconvert (.local\asset-tools\temp\lmconvert), Python 3 for nothing (bash + the exes).
set -e
CFG=$1; OUT=$2
[ -f "$CFG" ] && [ -n "$OUT" ] || { echo "usage: build_map.sh <map .cfg> <output map>"; exit 1; }
RP=/c/Programming/GitHub/OpenH3M/.local/asset-tools/src/Assembly/src/ReachPort/bin/dev/ReachPort.exe
LM=/c/Programming/GitHub/OpenH3M/.local/asset-tools/temp/lmconvert/lmconvert.exe
SALT='C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\resource_salt.bin'
val() { grep -E "^$1 " "$CFG" | head -1 | sed -E "s/^$1 +//; s/\r$//"; }
REACH=$(val reach_map); BASIS=$(val basis); BSCN=$(val basis_scenario); SCN=$(val scenario); LMD=$(val lightmaps)

# 1. lightmaps (only the ones not converted yet: .json + .spv.bin + .probes.bin)
mkdir -p "$(cygpath -u "$LMD")"
for lb in $("$RP" lbsps "$REACH" | tr -d '\r'); do
  leaf=${lb##*\\}
  if [ ! -f "$(cygpath -u "$LMD")/$leaf.probes.bin" ] && [ ! -f "$(cygpath -u "$LMD")/$leaf.none" ]; then echo "lightmap $leaf"; "$LM" "$REACH" "$LMD" "$leaf" | tail -3; fi
done
SKYA="$LMD\\${SCN##*\\}.skya.txt"
[ -f "$(cygpath -u "$SKYA")" ] || "$LM" --skya "$REACH" "$SCN" "$SKYA" | tail -1

# 2. port
ARGS=(--salt "$SALT" --lightmaps "$LMD" --skya "$SKYA")
while IFS= read -r line; do
  line=${line%$'\r'}; kind=${line%% *}; rest=${line#* }
  case "$kind" in
    weapon|equipment) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//')
       g=$([ "$kind" = weapon ] && echo weap || echo eqip); ARGS+=(--substitute "$g:$a=$b");;
    object) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//'); ARGS+=(--substitute "$a=$b");;
    remove) ARGS+=(--remove "$(echo "$rest" | sed 's/ *$//')");;
    fold) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//'); ARGS+=(--fold "$a=$b");;
    nofollow) ARGS+=(--no-follow "$rest");;
    shadergroup) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//'); ARGS+=(--group-substitute "$a=$b");;
  esac
done < "$CFG"
# general rule (all Reach maps): stock Halo 3 gameplay; Reach audio / animation not converted yet; Reach props with no
# Halo 3 equivalent stay as still scenery (user 2026-11-22), so Reach physics (phmo) is not converted
for g in weap eqip vehi bipd snd! lsnd jmad phmo; do ARGS+=(--skip "$g"); done
# engine settings with a stock Halo 3 equivalent use the basis map's (stock reuse first): performance throttles
BPERF=$("$RP" dump "$BASIS" scnr "$BSCN" | tr -d '\r' | grep -E "^/Performance Throttles = perf " | sed -E 's/^.* = perf //')
[ -n "$BPERF" ] && ARGS+=(--group-substitute "perf=perf:$BPERF")
"$RP" port "$REACH" "$BASIS" "$OUT" "${ARGS[@]}" $PORT_EXTRA "scnr:$SCN" 2>&1 | grep -E -A12 "walk:|copied|integrity|Exception|FAILED" | grep -vE "^--$" | head -20
LOG="$(cygpath -u "$OUT").log.txt"; UNR="$(cygpath -u "$OUT").unresolved.txt"
{ echo "# Reach tags not converted (build_map.sh general rule, cfg, or no Halo 3 group). Stock Halo 3 substitutes are"
  echo "# listed in the cfg; everything here had its references cleared."
  grep -E "^(skipped group|group not in Halo 3, not ported|Reach engine shader data not ported|resource not converted yet|bitmap not ported|not walked)" "$LOG" | sort | uniq -c | sort -rn; } > "$UNR"
echo "unresolved: $(grep -vc '^#' "$UNR") lines -> $UNR"

# 3. scenario + slot map id
"$RP" scenario "$OUT" "$SCN" | tail -2
MAPID=$("$RP" dump "$BASIS" scnr "$BSCN" | grep -E "^/Map Id = " | awk '{print $NF}')
"$RP" set "$OUT" "scnr:$SCN|Map Id=$MAPID" | tail -1
# one BSP zone per structure BSP (the basis slot has one; ZoneBsps.cs)
"$RP" zonebsps "$OUT" "$SCN" | grep -E "BSP References|Zone Usage" 

# 4. Forge palettes from the basis scenario
SB=(); while IFS= read -r line; do line=${line%$'\r'}; [ "${line%% *}" = sandbox ] && SB+=("${line#* }"); done < "$CFG"
[ ${#SB[@]} -gt 0 ] && "$RP" shareblocks "$OUT" "scnr:$BSCN" "scnr:$SCN" "${SB[@]}" | tail -2
echo "built $OUT"
