"""Beaver Creek lower-room fill lights (user 2026-11-24: "Yes, add and re-bake").
Halo 2 put 8 faint white glow markers (light volumes, scenarios\\objects\\lights\\multi\\mp_sphere_white_darker) in
the bases' lower rooms; they are sprites with no Halo 3 equivalent and were not ported, and the final bake left one of
those rooms nearly black. Halo 3 lights such rooms with baked generic lights in the structure lighting info, so one
faint white omni light goes at each marker position. Values follow stock Halo 3 small interior fills (omni,
intensity 2..12, far attenuation 2.5..8 on the disc lighting infos). The two teleporter markers are left out: the
teleporters are stock Halo 3 objects with their own effects.
Run once (it appends) before the bake. Usage: beavercreek_fill_lights.py [intensity] [far attenuation]"""
import json, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')
import te
T = r'levels\test\beavercreek\beavercreek.scenario_structure_lighting_info'
H2 = r'C:\Programming\GitHub\OpenH3M\.local\beavercreek\h2-placements.json'
INTENSITY = sys.argv[1] if len(sys.argv) > 1 else '4'
FAR = sys.argv[2] if len(sys.argv) > 2 else '5'
spots = [e['position'] for e in json.load(open(H2))['light volumes'] if e['palette'].endswith('mp_sphere_white_darker')]
d = 'Block:generic light definitions[0]/'
ops = [{'op': 'add', 'tag': T, 'block': 'Block:generic light definitions', 'count': 1},
       {'op': 'set', 'tag': T, 'field': d + 'type', 'value': 'omni'},
       {'op': 'set', 'tag': T, 'field': d + 'flags', 'value': 'use far attenuation'},
       {'op': 'set', 'tag': T, 'field': d + 'shape', 'value': 'circle'},
       {'op': 'set', 'tag': T, 'field': d + 'color', 'value': '0.85,0.85,0.85'},
       {'op': 'set', 'tag': T, 'field': d + 'intensity', 'value': INTENSITY},
       {'op': 'set', 'tag': T, 'field': d + 'far attenuation bounds', 'value': '0,' + FAR},
       {'op': 'set', 'tag': T, 'field': d + 'aspect', 'value': '1'}]
for i, p in enumerate(spots):
    b = 'Block:generic light instances[%d]/' % i
    ops += [{'op': 'add', 'tag': T, 'block': 'Block:generic light instances', 'count': 1},
            {'op': 'set', 'tag': T, 'field': b + 'definition index', 'value': '0'},
            {'op': 'set', 'tag': T, 'field': b + 'origin', 'value': p},
            {'op': 'set', 'tag': T, 'field': b + 'forward', 'value': '1,0,0'},
            {'op': 'set', 'tag': T, 'field': b + 'up', 'value': '0,0,1'}]
print(len(spots), 'lights')
print(te.edit(ops)[-300:])
