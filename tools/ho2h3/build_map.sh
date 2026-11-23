#!/usr/bin/env bash
# ho2h3 build: one Halo Online (ElDewrito) map -> original Xbox 360 Halo 3 map in a stock slot.
#   build_map.sh <map cfg> <output map>
# The cfg is the per-map file shared with tools/reach360-port (maps/<name>.cfg): basis, basis_scenario, scenario,
# remove lines and sandbox lines are read here; Reach-route-only lines (reach_map, lightmaps, fold, shadergroup ...)
# are ignored. Source: ho_pak / ho_scenario lines in the cfg, else the Reach Advanced Multiplayer package.
#   1. ho2h3 convert: tags converted into a copy of the basis map (README.md)
#   2. resources of converted and copied tags marked required in every zone set (ReachPort activate)
#   3. the converted scenario becomes the map's scenario; the slot's map id is kept; one BSP zone per structure BSP
#   4. Forge palettes: the basis scenario's stock Halo 3 sandbox blocks are shared into the converted scenario
set -e
CFG=$1; OUT=$2
HO=/c/Programming/GitHub/OpenH3M/.local/asset-tools/temp/ho2h3/ho2h3.dll
RP=/c/Programming/GitHub/OpenH3M/.local/asset-tools/src/Assembly/src/ReachPort/bin/dev/ReachPort.exe
SALT='C:\Programming\GitHub\OpenH3M\.local\asset-tools\inject360\resource_salt.bin'
val() { grep -E "^$1 " "$CFG" | head -1 | sed -E "s/^$1 //" | tr -d '\r'; }
PAK=$(val ho_pak); [ -z "$PAK" ] && PAK='C:\Programming\GitHub\OpenH3M\.local\reference\eldewrito-reach-amp\reach_advanced_multiplayer_v2.pak'
BASIS=$(val basis); BSCN=$(val basis_scenario); SCN=$(val ho_scenario); [ -z "$SCN" ] && SCN=$(val scenario)
ARGS=()
while IFS= read -r line; do
  line=${line%$'\r'}; kind=${line%% *}; rest=${line#* }
  case "$kind" in
    remove) ARGS+=(--remove "$(echo "$rest" | sed 's/ *$//')");;
    object) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//'); ARGS+=(--substitute "$a=$b");;
    shadergroup) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//'); ARGS+=(--group-substitute "$a=$b");;
    weapon|equipment) a=$(echo "${rest%%=*}" | sed 's/ *$//'); b=$(echo "${rest#*=}" | sed 's/^ *//')
       g=$([ "$kind" = weapon ] && echo weap || echo eqip); ARGS+=(--substitute "$g:$a=$b");;
  esac
done < "$CFG"
# general rule: audio, animation and decorator (grass) data are not converted yet; their tags are left out
for g in snd! lsnd jmad dctr; do ARGS+=(--skip "$g"); done

# 1. convert
dotnet "$HO" convert "$PAK" "$SCN" "$BASIS" "$OUT" --salt "$SALT" "${ARGS[@]}" 2>&1 | grep -vE "^WARNING" | tail -6
# 3. scenario + slot map id + BSP zones
"$RP" scenario "$OUT" "$SCN" | tail -2
MAPID=$("$RP" dump "$BASIS" scnr "$BSCN" | grep -E "^/Map Id = " | awk '{print $NF}' | tr -d '\r')
"$RP" set "$OUT" "scnr:$SCN|Map Id=$MAPID" | tail -1
"$RP" zonebsps "$OUT" "$SCN" | grep -E "BSP References|Zone Usage" || true
# 4. Forge palettes from the basis scenario
SB=(); while IFS= read -r line; do line=${line%$'\r'}; [ "${line%% *}" = sandbox ] && SB+=("${line#* }"); done < "$CFG"
[ ${#SB[@]} -gt 0 ] && "$RP" shareblocks "$OUT" "scnr:$BSCN" "scnr:$SCN" "${SB[@]}" | tail -2
# 2. zone sets (last: it also finalizes the map's integrity data)
"$RP" activate "$OUT" "$OUT.keys.txt" | tail -3
echo "built $OUT"
