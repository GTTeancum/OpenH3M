"""Extract unchanged controller bodies; redirect only external motion dispatch."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'work/h4-forge-research'
parts = ['#include "forge_original.h"',
         '#undef DEFINE_REX_FUNC',
         '#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)',
         '#undef REX_CALL_INDIRECT_FUNC',
         '#define REX_CALL_INDIRECT_FUNC(address) controller_dispatch(ctx,base,address)',
         'namespace h4_forge_original {',
         'void controller_dispatch(PPCContext&,uint8_t*,uint32_t);',
         'void sub_82CD40A8(PPCContext&,uint8_t*);',
         'void sub_82CD55F0(PPCContext&,uint8_t*);',
         'void sub_822AAB18(PPCContext&,uint8_t*);']
bodies = {}
text = (R/'isolated/forge_original.cpp').read_text()
for match in re.finditer(r'DEFINE_REX_FUNC\((\w+)\) \{', text):
    start = match.start()
    end = text.find('DEFINE_REX_FUNC(', start+1)
    bodies[match[1]] = text[start:end if end>=0 else text.rfind('\n}')].strip()
for name, number in [('sub_822528D8',200),('sub_82D824C8',126),('sub_82415E10',226),('sub_82259C00',161),('sub_824150C8',263),('sub_82416640',233),('sub_83292E30',1),('sub_83292E50',271),('sub_82C01FB8',239),('sub_82C023E8',34),
                     ('sub_8249B418',222),('sub_82452930',2),('sub_82301320',54),
                     ('sub_82C95448',26),('sub_82C01E90',218),
                     ('sub_8257FB98',108),('sub_8229D390',288),
                     ('sub_8244A8D8',194),('sub_82282580',52),('sub_8221CA38',51),('sub_8228ACE8',175),
                     ('sub_82260CF0',237),('sub_82260C98',93),('sub_82260E80',290),('sub_82260AF8',239),('sub_822302F8',93),
                     ('sub_822410D0',44),('sub_8225EA20',30),('__savegprlr_26',260),('__restgprlr_26',10),
                     ('sub_8228CBC8',35),('sub_824F5E28',204),('__savegprlr_21',18),('__restgprlr_21',110),('sub_824F5F78',239),('__savegprlr_19', 131),('__restfpr_22', 132),('__restgprlr_19', 174),('__savefpr_22', 237),('sub_8228CCE0', 270),('sub_8229C9F0', 97),('sub_824F5CF0',13),('sub_8244AF48',201),('sub_8221B258',289),('sub_8221B030',263),('__savefpr_25',69),('__restfpr_25',213),('sub_82243068',123),('sub_8229D4E0',118),('sub_8249B1F8',6),('sub_8232F708',226),('sub_824BEB50',56),('sub_8244B338',167),('sub_824BEA10',62),('sub_824BEAD0',101),('sub_824BE840',259),
                     ('sub_821D6D90',93),('sub_8244B758',146),('sub_822E15E0',165),
                     ('sub_822C8040',99),('sub_8229FAD8',157),
                     ('sub_8244EED8',70),('sub_8244A118',49),('sub_82582178',101),('sub_82282728',163),
                     ('__savegprlr_24',177),('__restgprlr_24',123),('__savefpr_19',244),('__restfpr_19',177),
                     ('__savegprlr_28',162),('__restgprlr_28',55),
                     ('__savegprlr_29',65),('__restgprlr_29',54)]:
    text = (R / f'generated/halo4_recomp.{number}.cpp').read_text()
    marker = f'DEFINE_REX_FUNC({name}) {{'
    bodies[name] = marker + text.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
selected = set()
pending = ['sub_822528D8','sub_82416640','sub_83292E30','sub_83292E50','sub_82C01FB8','sub_82C023E8','sub_8249B418','sub_82452930','sub_8244A8D8','sub_824BEA10','sub_824BEAD0','sub_8244B338','sub_8244AF48']
external = {'sub_82CD40A8','sub_82CD55F0','sub_822AAB18',
 'sub_82235650','sub_82260F08','sub_82260F70','sub_822AD348','sub_823C2020','sub_8281F450','sub_822633F0',
 'sub_82451A38','sub_82451BA8',
 'sub_821F2050','sub_82582A68','sub_82937F50','sub_8293A3B0','sub_82582610',
 'sub_822ED938','sub_825826B0','sub_82340E60','sub_8226CD10','sub_8281F4E0','sub_82415970','sub_82417550','sub_823FC348','sub_822B83C0','sub_82271460','sub_8224DED0'}
parts += [f'void {name}(PPCContext&,uint8_t*);' for name in sorted(external)]
while pending:
    name = pending.pop()
    if name in selected or name in external: continue
    if name not in bodies: raise ValueError('Unresolved original dependency '+name)
    selected.add(name)
    pending += re.findall(r'\b((?:sub_|__save|__rest)\w+)\(ctx, base\)',bodies[name])
parts += [f'void {name}(PPCContext&,uint8_t*);' for name in sorted(selected)]
parts += [bodies[name] for name in sorted(selected)]
parts.append('}')
# Keep the H3 filter in its own namespace; execute unchanged original body/helpers.
h3_names = {'sub_820AF170','__savegprlr_24','__restgprlr_24',
            'sub_82629000','sub_82662340','sub_82662350','__savegprlr_28','__restgprlr_28'}
h3_bodies = {}
for path in (ROOT/'halo3mp/generated/default').glob('*.cpp'):
    source = path.read_text()
    for name in h3_names - h3_bodies.keys():
        marker = f'DEFINE_REX_FUNC({name}) {{'
        if marker in source:
            h3_bodies[name] = marker + source.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
assert h3_bodies.keys() == h3_names
parts.append('namespace h3_collision {')
parts += ['void controller_dispatch(PPCContext&,uint8_t*,uint32_t);',
          'void sub_82651968(PPCContext&,uint8_t*);','void sub_8265FD48(PPCContext&,uint8_t*);']
parts += [f'void {name}(PPCContext&,uint8_t*);' for name in sorted(h3_names)]
parts += [h3_bodies[name] for name in sorted(h3_names)]
parts.append('}')
for namespace, path, name in [
    ('h4_ownership', R/'generated/halo4_recomp.91.cpp', 'sub_822ED938'),
    ('h3_ownership', ROOT/'halo3mp/generated/default/halo3mp_recomp.94.cpp', 'sub_821F0688'),
]:
    source=path.read_text();marker=f'DEFINE_REX_FUNC({name}) {{'
    original=marker+source.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
    parts += [f'namespace {namespace} {{', 'void sub_822714E0(PPCContext&,uint8_t*);', original, '}']
(R/'isolated/controller_original.cpp').write_text('\n'.join(parts)+'\n')
print(f'Extracted {len(selected)} original controller/target-builder functions; external callbacks are test adapters.')
activation = ['#include "forge_original.h"', '#undef DEFINE_REX_FUNC',
              '#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)']
for namespace, path, name, wake, setup in [
    ('h4_activation',R/'generated/halo4_recomp.93.cpp','sub_82CD55F0','sub_82CE1B98','sub_824A5118'),
    ('h3_activation',ROOT/'halo3mp/generated/default/halo3mp_recomp.65.cpp','sub_82651968','sub_8265B720','sub_8226B190'),
]:
    text=path.read_text();marker=f'DEFINE_REX_FUNC({name}) {{'
    body=marker+text.split(marker,1)[1].split('DEFINE_REX_FUNC(',1)[0].rstrip()
    activation += [f'namespace {namespace} {{',f'void {wake}(PPCContext&,uint8_t*);',
                   f'void {setup}(PPCContext&,uint8_t*);',body,'}']
(R/'isolated/activation_original.cpp').write_text('\n'.join(activation)+'\n')
