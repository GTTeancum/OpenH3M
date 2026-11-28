"""Elongation fixture lights (user 2026-11-27: Elongation must not stay dark; "keep at the pack as a whole").
Halo 2 lit Elongation from its light-fixture materials (hall fluorescents, halogen lamps 'lp:1'); the Halo 3 draft bake
left the level almost black. Halo 3 lights interiors with baked generic lights in the structure lighting info, so one
omni light goes just in front of each fixture cluster found in Bungie's elongation.ass (54: 46 fluorescent, 8 halogen),
coloured by its Halo 2 material's emissive colour. Values follow stock Halo 3 small interior fills (omni, intensity
2..12, far attenuation 2.5..8 on the disc lighting infos), as Beaver Creek's fills.
Run once (it appends) before the bake. Usage: elongation_fixture_lights.py [intensity] [far attenuation]"""
import json, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')
import te
T = r'levels\test\elongation\elongation.scenario_structure_lighting_info'
FIX = r'C:\Programming\GitHub\OpenH3M\.local\elongation\light-fixtures.json'
INTENSITY = sys.argv[1] if len(sys.argv) > 1 else '6'
FAR = sys.argv[2] if len(sys.argv) > 2 else '6'
COLOR = {'fluorescent': '0.74,0.79,0.78', 'halogen': '0.84,0.82,0.7'}   # Halo 2 emissive colours
fix = json.load(open(FIX))
ops = []
kinds = list(COLOR)
for k, kind in enumerate(kinds):
    d = 'Block:generic light definitions[%d]/' % k
    ops += [{'op': 'add', 'tag': T, 'block': 'Block:generic light definitions', 'count': 1},
            {'op': 'set', 'tag': T, 'field': d + 'type', 'value': 'omni'},
            {'op': 'set', 'tag': T, 'field': d + 'flags', 'value': 'use far attenuation'},
            {'op': 'set', 'tag': T, 'field': d + 'shape', 'value': 'circle'},
            {'op': 'set', 'tag': T, 'field': d + 'color', 'value': COLOR[kind]},
            {'op': 'set', 'tag': T, 'field': d + 'intensity', 'value': INTENSITY},
            {'op': 'set', 'tag': T, 'field': d + 'far attenuation bounds', 'value': '0,' + FAR},
            {'op': 'set', 'tag': T, 'field': d + 'aspect', 'value': '1'}]
for i, f in enumerate(fix):
    kind = 'halogen' if 'halogen' in f['mat'] else 'fluorescent'
    p = [f['pos'][j] + 0.15 * f['normal'][j] for j in range(3)]   # just in front of the lamp surface
    b = 'Block:generic light instances[%d]/' % i
    ops += [{'op': 'add', 'tag': T, 'block': 'Block:generic light instances', 'count': 1},
            {'op': 'set', 'tag': T, 'field': b + 'definition index', 'value': str(kinds.index(kind))},
            {'op': 'set', 'tag': T, 'field': b + 'origin', 'value': '%.4f,%.4f,%.4f' % tuple(p)},
            {'op': 'set', 'tag': T, 'field': b + 'forward', 'value': '1,0,0'},
            {'op': 'set', 'tag': T, 'field': b + 'up', 'value': '0,0,1'}]
print(len(fix), 'lights')
print(te.edit(ops)[-300:])
