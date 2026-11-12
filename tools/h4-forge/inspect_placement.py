"""Compare original H4 placement results with the native H3 saved pose."""
import argparse
import csv
import json
import math
import struct
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("trace", type=Path, help="forge-scene.bin path")
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
trace = a.trace.resolve()
trace.relative_to(root)
rows = list(csv.reader(Path(str(trace)+".placement.csv").open()))
variant = Path(str(trace)+".variant").read_bytes()
results = []
for row in rows:
    check, datum, slot, snapped = map(int, row[:4])
    if not snapped:
        continue
    values = list(map(float, row[4:]))
    requested, basis, output, q = values[:3], values[3:12], values[12:15], values[15:19]
    x,y,z,w = q
    rotation = [1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),
                2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),
                2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)]
    at = 0x130 + slot*0x54
    native = struct.unpack_from(">9f",variant,at+0x10)
    results.append(dict(check=check,datum=hex(datum),slot=slot,
        requested=requested,h4_position=output,h4_quaternion=q,
        h4_rotation_difference=max(abs(a-b) for a,b in zip(basis,rotation)),
        saved_position=native[:3],saved_forward=native[3:6],saved_up=native[6:9],
        saved_position_difference=math.dist(output,native[:3]),
        saved_axis_difference=max(abs(a-b) for a,b in zip(basis[:3]+basis[6:9],native[3:9]))))
# Measure original H4 anchors in the actual saved H3 transforms.
scene=trace.read_bytes()
objects={};off=60
for _ in range(struct.unpack_from('<I',scene,4)[0]):
    datum=struct.unpack_from('<I',scene,off)[0]
    count=struct.unpack_from('<I',scene,off+20)[0]
    objects[datum]=[struct.unpack_from('>3f',scene,off+24+i*112+0x2c) for i in range(count)]
    off+=24+count*112
world={}
for slot in range(640):
    at=0x130+slot*0x54
    datum=struct.unpack_from('>I',variant,at+4)[0]
    if datum not in objects:continue
    pos,f,u=[struct.unpack_from('>3f',variant,at+n) for n in (16,28,40)]
    left=(u[1]*f[2]-u[2]*f[1],u[2]*f[0]-u[0]*f[2],u[0]*f[1]-u[1]*f[0])
    world[datum]=[[pos[i]+a[0]*f[i]+a[1]*left[i]+a[2]*u[i] for i in range(3)] for a in objects[datum]]
residual=None
if results:
    held=int(results[-1]['datum'],16)
    pairs=[math.dist(a,b) for a in world.get(held,[]) for datum,points in world.items()
           if datum!=held for b in points]
    if pairs:residual=min(pairs)
print(json.dumps(dict(records=len(rows),snaps=results,saved_marker_residual=residual,
    limitation="Saved snapshot is latest placement, not necessarily the instant of each event."),indent=2))
