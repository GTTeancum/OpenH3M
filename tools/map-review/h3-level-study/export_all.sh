#!/bin/bash
# Export each map's structure bsp with the kit's own exporter, summarise, delete the big XML.
K=/c/Programming/GitHub/OpenH3M/.local/h3ek-source
W=/c/Programming/GitHub/OpenH3M/.local/h3-study
B=$(printf "\\\\")
KK='C:\Programming\GitHub\OpenH3M\.local\h3ek-source'
WW='C:\Programming\GitHub\OpenH3M\.local\h3-study'
for m in "$@"; do
  [ -f $W/$m.json ] && continue
  (cd $K && ./tool.exe export-tag-to-xml "$KK${B}tags${B}levels${B}multi${B}$m${B}$m.scenario_structure_bsp" "$WW${B}${m}_bsp.xml" > $W/$m.export.log 2>&1)
  python $W/summarize_bsp.py $W/${m}_bsp.xml $W/$m.json >> $W/$m.export.log 2>&1
  rm -f $W/${m}_bsp.xml
done
echo done
