"""Set Tombstone's light-emitting materials in its lighting info (re-run after every structure import, which resets
them). The lighting info's material-info block has one slot per material of the ASS level source, in ASS order
(its count equals the ASS material count; the compiled BSP material list is ordered and split differently), so slots
are found by name in the ASS material list. All slots are cleared first.

Strengths: Halo 2 emissive_power (lights 0.75, dim strips 0.1, screens 0.05) mapped onto stock Halo 3 emitter values
(power 4-20, quality 1, falloff 10 / cutoff 20 as on Chill). The flickering strip uses the dim strength."""
import os, re, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')
import te
BSP = r'levels\test\tombstone\tombstone.scenario_structure_bsp'
LI = r'levels\test\tombstone\tombstone.scenario_structure_lighting_info'
EMIT = {'highplains_lights': (10, '1,0.95,0.85'), 'highplains_lights_dim': (3, '1,0.95,0.85'),
        'highplains_lights_flicker': (3, '1,0.95,0.85'), 'highplains_console_top': (1, '0.6,1,0.6'),
        'highplains_viewscreen': (1, '1,0.3,0.3'), 'highplains_soda': (1, '1,1,1')}
ASS = r'C:\Programming\GitHub\OpenH3M\.local\h3ek-source\data\levels\test\tombstone\structure\tombstone.ass'
te.edit([{'op': 'dump', 'tag': LI, 'out': os.path.join(te.D, 'tli.txt')}], timeout=900)
A = open(ASS, encoding='latin-1').read().split(chr(10))
mats = [A[k + 1].strip().strip('"').rstrip('%!*@#=?^&-+<>|() 0123456789') for k in range(len(A)) if A[k].startswith(';MATERIAL ')]
n_info = sum(1 for l in open(os.path.join(te.D, 'tli.txt'), encoding='utf-8') if re.match(r'Block:material info\[\d+\]/emissive power\t', l))
if n_info != len(mats): raise SystemExit(f'lighting slots {n_info} != ASS materials {len(mats)}')
ops = []
for i in range(n_info):
    ops += [{'op': 'set', 'tag': LI, 'field': f'Block:material info[{i}]/emissive power', 'value': '0'}]
for i, name in enumerate(mats):
    if name in EMIT:
        pw, c = EMIT[name]; b = f'Block:material info[{i}]/'
        ops += [{'op': 'set', 'tag': LI, 'field': b + 'emissive power', 'value': str(pw)}, {'op': 'set', 'tag': LI, 'field': b + 'emissive color', 'value': c},
                {'op': 'set', 'tag': LI, 'field': b + 'emissive quality', 'value': '1'}, {'op': 'set', 'tag': LI, 'field': b + 'attenuation falloff', 'value': '10'},
                {'op': 'set', 'tag': LI, 'field': b + 'attenuation cutoff', 'value': '20'}]
        print('emitter', i, name, pw)
te.edit(ops)
print('ASS materials / lighting slots', n_info)
