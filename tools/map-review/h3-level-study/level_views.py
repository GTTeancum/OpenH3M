"""Console script for one halo3_tag_test run: for each camera, dump the official DIP profiler with
(a) everything, (b) objects/first-person off, (b2) also the kit's import-error markers hidden (level only), (c) also instanced geometry off (structure + sky etc.).
Cameras: a points file of 'x y z yaw' (eye = z + 0.62) or a cam text file 'x y z fx fy fz ux uy uz fov'.
Usage: level_views.py <label> <start> <camfile> [<camfile> ...]"""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).parent
label, t = sys.argv[1], float(sys.argv[2])
cams = []
for p in sys.argv[3:]:
    txt = open(p).read().strip().strip('"')
    if p.endswith("points.txt"):
        for l in txt.splitlines():
            x, y, z, yaw = map(float, l.split())
            cams.append(f"{x:.4f} {y:.4f} {z + 0.62:.4f} {math.cos(yaw):.4f} {math.sin(yaw):.4f} 0 0 0 1 70")
    else:
        cams.append(txt)
s = []
def at(dt, text):
    global t
    t += dt; s.append([round(t, 1), text])
def dump(name):
    at(3, "dip_stats_dump\n"); at(3, f"!mv debug_dip_stats.txt {HERE / ('dip_' + label + '_' + name + '.txt')}")
for i, cam in enumerate(cams, 1):
    at(2, "`"); at(1, f'debug_camera_load_text "{cam}"\n'); at(1, "`"); at(6, "`")
    dump(f"v{i}_all")
    at(1, "render_objects 0\n"); at(1, "render_first_person 0\n"); dump(f"v{i}_noobj")
    at(1, "error_geometry_hide_all\n"); dump(f"v{i}_level")   # the kit's import-error markers (test game only)
    at(1, "render_instanced_geometry 0\n"); dump(f"v{i}_noinst")
    for g in ("render_objects 1", "render_first_person 1", "render_instanced_geometry 1"): at(1, g + "\n")
    at(1, f'screenshot "{label}_v{i}"\n'); at(5, "")
print(json.dumps([v for v in s if v[1]]))
