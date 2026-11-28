#!/bin/bash
# run_levels.sh <label> <init file> <seconds> <camfiles...> : wait for a free slot, run, collect, print summary
cd /c/Programming/GitHub/OpenH3M/.local/h3-study
L=$1; I=$2; S=$3; shift 3
n=0; until ! tasklist | grep -qi -E "spartan|halo3|sapien"; do sleep 15; n=$((n+1)); [ $n -gt 240 ] && exit 1; done
python run_tag_test.py $I $S "$(python level_views.py $L 90 "$@")" 2>&1 | grep -E "failed|ended|exited"
mv ../h3ek-source/${L}_v* . 2>/dev/null
for f in dip_${L}_*.txt; do echo "$f $(sed -n 5p $f)"; done
