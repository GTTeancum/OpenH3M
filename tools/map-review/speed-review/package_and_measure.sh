#!/usr/bin/env bash
# Package a converted Sky Bridge/Reactor map as a map-named LIVE container and measure it at the pain spots
# in the PC port (one game instance, hidden desktop). Usage: package_and_measure.sh <sky-bridge|reactor> <label>
set -u
MAP=$1; LABEL=$2
REPO=/c/Programming/GitHub/OpenH3M; PY=/c/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe
T=$REPO/tools/warlock-conversion/snapshot/tools; O=$REPO/.local/$MAP-kit
case $MAP in
  sky-bridge) NAME=sky_bridge; POINTS=sky-bridge-points.txt; PKG=Sky_Bridge_${LABEL//-/_} ;;
  reactor)    NAME=reactor; POINTS=reactor-points.txt; PKG=Reactor_${LABEL//-/_} ;;
esac
cd "$REPO" || exit 1
rm -rf "$O/payload-$LABEL" "$O/pkg-$LABEL"
$PY -B $T/build_dlc_payload.py --converted "$O" --stock .local/xenia-canary/game-local/maps --output "$O/payload-$LABEL" \
  --report "$O/payload-$LABEL.json" --map $NAME --source-map "$O/zanzibar-$LABEL.map" > "$O/payload-$LABEL.log" 2>&1 || { echo payload failed; tail -3 "$O/payload-$LABEL.log"; exit 1; }
$PY -B $T/build_dlc_previews.py --workshop D:/SteamLibrary/steamapps/workshop/content/976730 --payload "$O/payload-$LABEL" \
  --report "$O/previews-$LABEL.json" --map $NAME > /dev/null 2>&1 || { echo previews failed; exit 1; }
mkdir -p "$O/pkg-$LABEL"
$PY -B $T/build_dlc_live.py --payload "$O/payload-$LABEL" --output "$O/pkg-$LABEL/p.pending" --report "$O/package-$LABEL.json" > /dev/null 2>&1 || { echo package failed; exit 1; }
rm -rf ".local/pc-port/packages/$PKG"; mv "$O"/pkg-$LABEL/* ".local/pc-port/packages/$PKG"; rm -rf "$O/pkg-$LABEL" "$O/payload-$LABEL"
echo "packaged $PKG"
bash .local/pc-port/pain.sh "pain-$MAP-$LABEL" "$PKG" $NAME $POINTS 2>/dev/null
grep RESULT ".local/pc-port/pain-$MAP-$LABEL/result.json" | sed -E 's/.*point=([0-9]).*fps=([0-9.]+).*/  spot \1: \2 fps/'
for log in ".local/pc-port/pain-$MAP-$LABEL"/runtime*.log; do grep -a "\[workload\]" "$log"; done | sed -E 's/.*draws_per_frame=([0-9]+) indices_per_frame=([0-9]+).*/\1 \2/' | sort -n | awk '{d[NR]=$1; t[NR]=$2} END {print "  draws/frame range", d[1], "-", d[NR]}'
