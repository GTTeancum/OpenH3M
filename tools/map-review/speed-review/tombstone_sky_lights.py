"""Write Tombstone's sky-light list (the lights Halo 3's lighting pass uses) from Halo 2 Tombstone's sky settings.

Halo 2's highplains.sky lights the level with one sun (heading 110, pitch 40, warm colour) plus a flat warm
"outdoor ambient" base. Halo 3 takes sky lighting from the sky render model's sky-light list, so this writes:
  - one sun light: Halo 2 direction and colour, with Last Resort's sun strength (Halo 3 exposure reference);
  - 199 sky-glow lights spread evenly over the upper hemisphere in Halo 2's ambient colour, scaled so their
    total light on a level floor is AMBIENT_RATIO of the sun's.
Usage: tombstone_sky_lights.py <Last Resort sky render_model dump> [ambient ratio]"""
import math, re, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')
import te

H2_SUN_HEADING, H2_SUN_PITCH = 110.0, 40.0            # highplains.sky lights[0] direction
H2_SUN_COLOR = (0.874510, 0.788235, 0.690196)         # lights[0] radiosity colour
# Shade tint measured from Halo 2's own baked Tombstone lightmap (mid-dark texels, R:G:B); the sky tag's
# outdoor ambient colour (0.486, 0.376, 0.271) is far more orange than the shade Halo 2 actually renders.
H2_AMBIENT = (1.0, 0.92, 0.80)
AMBIENT_RATIO = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
TAG = r'levels\test\tombstone\sky\sky.render_model'
COUNT = 200


def lum(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


ref = {}
for line in open(sys.argv[1], encoding='utf-8').read().split('\n'):
    m = re.match(r'Block:sky lights\[(\d+)\]/(direction|intensity|solid angle)\t\w+\t(.*)', line)
    if m: ref.setdefault(int(m.group(1)), {})[m.group(2)] = [float(x) for x in m.group(3).split(',')]
ref_sun = max(ref.values(), key=lambda x: lum(x['intensity']))
sun_sa = ref_sun['solid angle'][0]
sun_lum = lum(ref_sun['intensity'])
h, p = math.radians(H2_SUN_HEADING), math.radians(H2_SUN_PITCH)
sun_dir = (math.cos(p) * math.cos(h), math.cos(p) * math.sin(h), math.sin(p))
sun_rgb = [sun_lum * c / lum(H2_SUN_COLOR) for c in H2_SUN_COLOR]
sun_floor = sun_lum * sun_sa * sun_dir[2]

n = COUNT - 1; sa = 2 * math.pi / n; dirs = []
golden = math.pi * (3 - math.sqrt(5))
for i in range(n):                       # even spread over the upper hemisphere
    z = (i + 0.5) / n; r = math.sqrt(1 - z * z); a = i * golden
    dirs.append((r * math.cos(a), r * math.sin(a), z))
floor_per_unit = sum(d[2] * sa for d in dirs)          # floor light from radiance 1 in every direction (= pi)
amb_lum = AMBIENT_RATIO * sun_floor / floor_per_unit
amb_rgb = [amb_lum * c / lum(H2_AMBIENT) for c in H2_AMBIENT]

ops = [{'op': 'clear', 'tag': TAG, 'block': 'Block:sky lights'}, {'op': 'add', 'tag': TAG, 'block': 'Block:sky lights', 'count': COUNT}]
for i, (d, rgb, s) in enumerate([(sun_dir, sun_rgb, sun_sa)] + [(d, amb_rgb, sa) for d in dirs]):
    b = f'Block:sky lights[{i}]/'
    ops += [{'op': 'set', 'tag': TAG, 'field': b + 'direction', 'value': ','.join(f'{v:.6f}' for v in d)},
            {'op': 'set', 'tag': TAG, 'field': b + 'intensity', 'value': ','.join(f'{v:.6g}' for v in rgb)},
            {'op': 'set', 'tag': TAG, 'field': b + 'solid angle', 'value': f'{s:.6g}'}]
te.edit(ops)
print(f'sky lights written: {COUNT} (sun + {n} glow); glow on a floor = {AMBIENT_RATIO} x sun')
