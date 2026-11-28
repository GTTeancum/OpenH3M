"""One camera view; dump the DIP profiler with each render category switched off in turn (restored after),
with a screenshot at the end of the objects-off state. Usage: probe_views.py <label> <start> <points file> <view#>"""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).parent
label, t, PTS, vi = sys.argv[1], float(sys.argv[2]), sys.argv[3], int(sys.argv[4])
x, y, z, yaw = [list(map(float, l.split())) for l in open(PTS) if l.strip()][vi - 1]
s = []
def at(dt, text):
    global t
    t += dt; s.append([round(t, 1), text])
def dump(name):
    at(3, "dip_stats_dump\n"); at(3, f"!mv debug_dip_stats.txt {HERE / ('dip_' + label + '_' + name + '.txt')}")
cam = f"{x:.4f} {y:.4f} {z + 0.62:.4f} {math.cos(yaw):.4f} {math.sin(yaw):.4f} 0 0 0 1 70"
at(0, "`"); at(1, f'debug_camera_load_text "{cam}"\n'); at(1, "`"); at(6, "`")
dump("all")
for g in ("render_objects", "render_transparents", "render_effects", "render_decorators", "render_weather",
          "render_sky", "render_water", "render_structure", "render_instanced_geometry", "render_lightmap_shadows",
          "render_patchy_fog", "render_first_person"):
    at(1, g + " 0\n"); dump("no_" + g[7:]); at(1, g + " 1\n")
at(1, "render_objects 0\n"); at(3, f'screenshot "{label}_noobjects"\n'); at(5, "")
print(json.dumps([v for v in s if v[1]]))
