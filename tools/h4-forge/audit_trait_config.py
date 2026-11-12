"""Static provenance for the four saved Forge trait-zone configurations."""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'work/h4-forge-research'
SCHEMA = ROOT / 'work/stock-h3-audit/TagTool/TagTool/Tags/Definitions/Gen4/MultiplayerVariantSettingsInterfaceDefinition.cs'
schema = SCHEMA.read_text()
enum = schema.split('public enum GameEngineSettings : int', 1)[1].split('{', 1)[1].split('}', 1)[0]
names = [s.strip() for s in enum.split(',') if s.strip()]
assert all(name.isidentifier() for name in names), 'Explicit enum values require parser update'
expected = ['TraitZoneAlphaPlayerTraits', 'TraitZoneBravoPlayerTraits',
            'TraitZoneCharliePlayerTraits', 'TraitZoneDeltaPlayerTraits']
assert names[180:184] == expected

def body(address, file):
    source = (RESEARCH / f'generated/halo4_recomp.{file}.cpp').read_text()
    return source.split(f'DEFINE_REX_FUNC(sub_{address}) {{', 1)[1].split('DEFINE_REX_FUNC(', 1)[0]

resolver = body('825B16B0', 147)
producer = body('82714570', 43)
initialize = body('8244C210', 217)
for instruction in ['addi r11,r4,-152', 'cmplwi cr6,r11,31', 'addi r12,r12,5844']:
    assert '// ' + instruction in resolver
for instruction in ['cmpwi cr6,r11,180', 'cmpwi cr6,r11,183', 'addi r11,r11,-180',
                    'addi r31,r10,12788', 'li r9,19', 'bl 0x825812d0']:
    assert '// ' + instruction in producer
for instruction in ['ori r27,r11,55724', 'addi r30,r11,12788', 'addi r31,r31,256',
                    'cmplwi cr6,r31,1024', 'bl 0x822ef3d8', 'bl 0x822d5908']:
    assert '// ' + instruction in initialize
image = (RESEARCH / 'h4-image.bin').read_bytes()
rows = []
for i, name in enumerate(expected):
    target = struct.unpack_from('>I', image, 0x825B16D4 - 0x82000000 + (180+i-152)*4)[0]
    assert target == 0x825B1820 + i*20
    block = resolver.split(f'loc_{target:08X}:', 1)[1].split('// blr', 1)[0]
    offset = 12788 + i*256
    for instruction in ['lwz r11,0(r13)', 'li r10,28', 'lwzx r11,r10,r11', f'addi r3,r11,{offset}']:
        assert '// ' + instruction in block
    rows.append(dict(setting=180+i, schema_name=name, branch=hex(target),
                     live_offset=offset, variant_offset=55724+i*256))
zones = body('8246BBC0', 74)
caller = body('8246B290', 171)
for instruction in ['li r31,0', 'stb r31,0(r9)', 'stb r31,1(r9)',
                    'stb r31,2(r9)', 'stb r31,3(r9)', 'lbz r11,47(r28)',
                    'cmplwi cr6,r11,4', 'stbx r20,r11,r10',
                    'bl 0x8298fcb8', 'bl 0x8298fa30', 'bl 0x823c2020',
                    'addi r30,r30,-9812', 'lbzx r11,r31,r11', 'li r5,0',
                    'bl 0x822d5908', 'addi r31,r31,1', 'addi r30,r30,256',
                    'cmpwi cr6,r31,4']:
    assert '// ' + instruction in zones
assert zones.index('// stbx r20,r11,r10') < zones.index('// bl 0x823c2020') < zones.index('// bl 0x822d5908')
assert caller.index('// lwz r10,132(r11)') < caller.index('// bl 0x8246bbc0') < caller.index('// lwz r10,136(r11)')
assert caller.index('// bl 0x8246bbc0') < caller.index('// bl 0x8246b628') < caller.index('// bl 0x8246b8f0')
merge = body('822D5BB0', 100)
for offset in range(20, 26):
    assert f'// lbz r' in merge and f',{offset}(r31)' in merge and f',{offset}(r30)' in merge
assert '// bl 0x82432290' in merge
boundary_sources = {address: body(address, number) for address, number in
                    [('8298FCB8', 4), ('8298FD50', 83), ('8298FA30', 164),
                     ('8298F920', 77), ('8258BAB8', 240), ('8258BB20', 65), ('8258BCB8', 55),
                     ('82990070', 106), ('822C9EB0', 144), ('82260B58', 54),
                     ('82260C98', 93), ('822E9E08', 112)]}
membership = boundary_sources['8298FA30']
for instruction in ['cmpwi cr6,r3,-1', 'li r29,1', 'li r29,2', 'bl 0x822e9e08',
                    'lfs f10,3884(r31)', 'bl 0x82260b58', 'bl 0x8298f920',
                    'addi r30,r30,12', 'beq cr6,0x8298fb24']:
    assert '// ' + instruction in membership
shape = boundary_sources['8298F920']
for instruction in ['cmpwi cr6,r11,1', 'cmpwi cr6,r11,2', 'cmpwi cr6,r11,3',
                    'bl 0x8258bab8', 'bl 0x8258bb20', 'bl 0x8258bcb8']:
    assert '// ' + instruction in shape
epsilon = struct.unpack_from('>f', image, 0x82128A54-0x82000000)[0]
assert 0.00009999 < epsilon < 0.00010001
assert struct.unpack_from('>f', image, 0x82128A08-0x82000000)[0] == 0.5
assert '// ble cr6,0x8258bb10' in boundary_sources['8258BAB8']
assert '// bgt cr6,0x8258bca0' in boundary_sources['8258BB20']
assert '// ble cr6,0x8258be7c' in boundary_sources['8258BCB8']
box_builder = boundary_sources['82990070']
for instruction in ['fabs f12,f0', 'fabs f11,f13', 'fadds f10,f11,f12',
                    'fmuls f28,f10,f31', 'fsubs f27,f12,f28', 'bl 0x822c9eb0',
                    'stfs f28,8(r8)', 'stfs f28,12(r8)', 'stfs f9,76(r8)']:
    assert '// ' + instruction in box_builder
parent_resolver = boundary_sources['82260C98']
for instruction in ['ld r8,256(r10)', 'rlwinm r7,r8,0,23,23',
                    'lwz r11,36(r10)', 'cmpwi cr6,r11,-1', 'mr r3,r11', 'b 0x82260ca8']:
    assert '// ' + instruction in parent_resolver
report = dict(scope='Static original-code/data linkage; schema supplies names, not live verification.',
              configurations=rows, schema_sha256=hashlib.sha256(schema.encode()).hexdigest(),
              originals={name: hashlib.sha256(value.encode()).hexdigest() for name, value in
                         [('825B16B0', resolver), ('82714570', producer), ('8244C210', initialize),
                          ('8246BBC0', zones), ('8246B290', caller), ('822D5BB0', merge),
                          *boundary_sources.items()]},
              boundary=dict(shapes={1:'sphere', 2:'cylinder', 3:'box'},
                  minimum_dimension_exclusive=epsilon, edge='Inclusive for finite valid dimensions',
                  biped='Either of two sample points; not a complete body/volume intersection',
                  other_object='Single point from 82260B58',
                  other_object_parent='82260C98 follows parent36 until flag0x100 or no parent; physics-derived position or resolved object64..72 fallback',
                  box_recentering='h=(abs(top)+abs(bottom))/2; center += transformed_up*(abs(top)-h); bounding radius=sqrt((width/2)^2+(length/2)^2+h^2)',
                  invalid_object='Returns false',
                  unverified='Executed cases, sample producer semantics, attachment/vehicle behavior'),
              zone_application=dict(function='8246BBC0', caller='8246B290',
                  source='variant+55724+256*channel', channel_field='object multiplayer block+47',
                  order='Ascending channels 0..3, once per active channel; not object traversal order',
                  membership='Team eligibility callback and 8298FCB8/8298FA30 boundary helpers; not yet executed',
                  precedence='Field-selective merge with force=false; subsequent caller stages can still override'),
              open=['Actual localized menu labels and reachability', 'Executed zone membership/overlap validation',
                    'Complete trait field semantics', 'Native H3 integration and save compatibility'])
(RESEARCH / 'isolated/full-re-trait-config.json').write_text(json.dumps(report, indent=2)+'\n')
print('Verified four settings branches, event19, initialization, zone application order and caller linkage (static).')
for row in rows:
    print(row)
