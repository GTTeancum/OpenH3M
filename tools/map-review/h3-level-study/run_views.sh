#!/bin/bash
# For each stock map: one long open view (camera placed from text), DIP dump + screenshot.
cd /c/Programming/GitHub/OpenH3M/.local/h3-study
for m in "$@"; do
  if tasklist | grep -i -E "spartan|halo3_|sapien" >/dev/null; then echo "another game running, stop"; exit 1; fi
  s=$(python -c "import json;print(json.load(open('cam_$m.txt')))")
  python run_tag_test.py init_$m.txt 100 "[[60,\"\`\"],[62,\"debug_camera_load_text \\\"$s\\\"\n\"],[64,\"\`\"],[78,\"\`\"],[80,\"dip_stats_dump\n\"],[83,\"screenshot \\\"h3s_${m}_open\\\"\n\"],[90,\"\`\"]]"
  sleep 1
  mv ../h3ek-source/debug_dip_stats.txt dip_${m}_open.txt 2>/dev/null
  mv ../h3ek-source/h3s_${m}_* . 2>/dev/null
  sed -n 5p dip_${m}_open.txt
done
