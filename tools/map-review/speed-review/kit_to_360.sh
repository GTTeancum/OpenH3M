#!/usr/bin/env bash
# Build a map from the official H3 Editing Kit tags, then convert it to an original Xbox 360 cache with the
# repository converter. Usage: kit_to_360.sh <sky-bridge|reactor> <run label>
# Output: C:\Programming\GitHub\OpenH3M\.local\<map>-kit\zanzibar-<label>.map (+ build-<label>.json/.log)
set -u
MAP=$1; LABEL=$2
REPO=/c/Programming/GitHub/OpenH3M; KIT=$REPO/.local/h3ek-source
PY=/c/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe
PACK=D:/SteamLibrary/steamapps/workshop/content/976730/3003239190
case $MAP in
  sky-bridge) SCN='levels\multi\s3d_sky_bridgenew\s3d_sky_bridgenew'; FILE=s3d_sky_bridgenew.map ;;
  reactor)    SCN='levels\multi\s3d_reactor\s3d_reactor'; FILE=s3d_reactor.map ;;
  *) echo "unknown map $MAP"; exit 2 ;;
esac
OUT=$REPO/.local/$MAP-kit; mkdir -p "$OUT" "$KIT/temp" "$REPO/.local/build-temp" "$REPO/work/$MAP"
SRC=C:/Programming/GitHub/OpenH3M/.local/h3ek-source/maps/$FILE
cd "$KIT" || exit 1
export TEMP='C:\Programming\GitHub\OpenH3M\.local\h3ek-source\temp' TMP='C:\Programming\GitHub\OpenH3M\.local\h3ek-source\temp'
S=$(date +%s); ./tool.exe build-cache-file "$SCN" pc > "$OUT/kit-build-$LABEL.log" 2>&1; RC=$?
echo "kit build exit $RC $(( $(date +%s) - S ))s"; [ $RC -eq 0 ] || exit 1
cd "$REPO" || exit 1
export TEMP='C:\Programming\GitHub\OpenH3M\.local\build-temp' TMP='C:\Programming\GitHub\OpenH3M\.local\build-temp'
if [ "$MAP" = sky-bridge ]; then
  (cd tools/warlock-conversion/snapshot/tools && $PY -B rebuild_collision_references.py --source "$SRC" --scenario "$SCN" --work C:/Programming/GitHub/OpenH3M/work/sky-bridge > "$OUT/collision-$LABEL.log" 2>&1) || { echo "collision failed"; exit 1; }
else
  (cd tools/warlock-conversion/snapshot/tools && $PY -B rebuild_whole_collision.py --source "$SRC" --scenario "$SCN" --work C:/Programming/GitHub/OpenH3M/work/reactor > "$OUT/collision-$LABEL.log" 2>&1 \
    && $PY -B -c "
from pathlib import Path; from cache_reader import Cache; import rebuild_whole_collision as r
c = Cache('$SRC', mcc=True); r.prepare(c, Path('C:/Programming/GitHub/OpenH3M/work/reactor')); c.close()" >> "$OUT/collision-$LABEL.log" 2>&1) || { echo "collision failed"; exit 1; }
fi
echo "collision ok"
S=$(date +%s)
$PY -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py --project C:/Programming/GitHub/OpenH3M \
  --disc-maps C:/X360/ISOs/H3M/maps --slot zanzibar --stock-materials --mcc-shared "$PACK/halo3/maps/shared.map" --source "$SRC" \
  --basis C:/X360/ISOs/H3M/maps/zanzibar.map --xex C:/Programming/GitHub/OpenH3M/.local/xenia-canary/game-local/default.xex \
  --sound-bank "$PACK/halo3/fmod/pc/sfx.fsb" \
  --additional-sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' \
  --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe \
  --output ".local/$MAP-kit/zanzibar-$LABEL.map" --report ".local/$MAP-kit/build-$LABEL.json" > "$OUT/build-$LABEL.log" 2>&1
RC=$?; echo "convert exit $RC after $(( $(date +%s) - S ))s"
grep -E "Error:" "$OUT/build-$LABEL.log" | tail -1 | cut -c1-400
ls -la "$OUT/zanzibar-$LABEL.map" 2>/dev/null
exit $RC
