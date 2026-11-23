# usage: merge_build.sh <sb|re> <package name> <merge.py options...>   builds a merged test map and its package
PY=/c/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe
cd /c/Programming/GitHub/OpenH3M/work/speed-review
T=../../tools/warlock-conversion/snapshot/tools; X=/c/X360/ISOs/H3M/.local/test-game/default.xex
if [ "$1" = sb ]; then S=sky-bridge-360; M=sky_bridge; else S=reactor-360; M=reactor; fi
D=merge/$1; NAME=$2; shift 2
rm -rf $D && mkdir -p $D/payload $D/pkg && cp $S/*.blf $S/*.mapinfo $D/payload/ || exit 1
$PY -B ../../tools/map-review/speed-review/merge.py $S/$M.map --xex $X --out $D/payload/$M.map --report $D/merge-report.json "$@" 2>&1 | tail -2 | cut -c1-420 || exit 1
[ -f $D/payload/$M.map ] || exit 1
$PY -B $T/build_dlc_live.py --payload $D/payload --output $D/pkg/p.pending --report $D/package-report.json > /dev/null || exit 1
rm -rf ../../.local/pc-port/packages/$NAME && mv $D/pkg/* ../../.local/pc-port/packages/$NAME && echo built $NAME
