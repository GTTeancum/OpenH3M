"""Extract the original magnet movement predicate and record its producer chain."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'work/h4-forge-research'
locations = {'82582178': 101, '822562A8': 180, '823619F8': 276,
             '82361880': 56, '82221B08': 93, '822B3FF0':132, '8225CE30': 259, '82357E90':285, '8235DC98':121, '822D6EE8':98, '821F35F0':42, '82309638':56, '822C5470':204}
bodies = {}
records = {}
for address, number in locations.items():
    path = RESEARCH / f'generated/halo4_recomp.{number}.cpp'
    source = path.read_text()
    marker = f'DEFINE_REX_FUNC(sub_{address}) {{'
    start = source.index(marker)
    body = (marker + source[start + len(marker):].split('DEFINE_REX_FUNC(', 1)[0]).strip()
    bodies[address] = body
    records[address] = dict(file=path.name, line=source.count('\n', 0, start) + 1,
                            sha256=hashlib.sha256(body.encode()).hexdigest(),
                            calls=sorted(set(re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)', body))))
for instruction in ['lfs f13,1352(r31)', 'lfs f11,1348(r31)',
                    'lfs f10,1356(r31)', 'fcmpu cr6,f0,f7', 'blt cr6,0x82582234']:
    assert '// ' + instruction in bodies['82582178']
# Correlate selector array offset and order with the installed Gen4 tag schema.
schema=ROOT/'work/stock-h3-audit/TagTool/TagTool/Tags/Definitions/Gen4'
obj=(schema/'Object.cs').read_text();unit=(schema/'Unit.cs').read_text();vehicle=(schema/'Vehicle.cs').read_text()
assert 'Size = 0x204' in obj and 'Size = 0x40C' in unit
assert 0x204+0x40C+4==1556
physics=vehicle.split('class VehiclePhysicsTypesStruct : TagStructure',1)[1].split('[TagStructure',1)[0]
fields=re.findall(r'public List<[^>]+> (Type\w+);',physics)
assert len(fields)==15 and fields[8]=='TypeVtol'
for instruction in ['addi r10,r10,1556','addi r10,r10,12','cmpwi cr6,r11,15','lbz r11,3856(r3)','lbz r11,3857(r3)']:
    assert '// '+instruction in bodies['822B3FF0']
# Player assignment establishes which filtering branch applies to human control.
for instruction in ['stw r26,1180(r9)','stw r28,36(r31)','stw r23,1180(r27)']:
    assert '// '+instruction in bodies['82357E90']
p=ROOT/'halo3mp/generated/default/halo3mp_recomp.20.cpp'
t=p.read_text();marker='DEFINE_REX_FUNC(sub_821E9028) {';start=t.index(marker)
b=(marker+t[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]).strip()
for instruction in ['mulli r10,r10,880','stw r29,380(r26)','stw r30,40(r31)','stw r25,380(r27)']:
    assert '// '+instruction in b
records['H3_821E9028']=dict(file=str(p.relative_to(ROOT)),line=t.count('\n',0,start)+1,
    sha256=hashlib.sha256(b.encode()).hexdigest(),calls=sorted(set(re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',b))))
for address,number in {'820B8608':51,'821EC0E0':95,'820B6EA0':91}.items():
    p=ROOT/f'halo3mp/generated/default/halo3mp_recomp.{number}.cpp'
    t=p.read_text();marker=f'DEFINE_REX_FUNC(sub_{address}) {{';start=t.index(marker)
    b=(marker+t[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]).strip()
    records['H3_'+address]=dict(file=str(p.relative_to(ROOT)),line=t.count('\n',0,start)+1,
        sha256=hashlib.sha256(b.encode()).hexdigest(),calls=sorted(set(re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',b))))
    if address=='820B8608':
        assert all('// '+i in b for i in ['addi r8,r4,20','addi r10,r11,496','stw r9,0(r10)','stw r9,4(r10)','stw r9,8(r10)'])
    if address=='821EC0E0':
        assert all('// '+i in b for i in ['ld r11,20(r31)','lhz r8,40(r31)','addi r4,r1,128','bl 0x820b8608'])
# Packet float fields are not rewritten by these two intervening functions.
filter_body=bodies['8235DC98']; history=bodies['822D6EE8']
assert '// mr r5,r4' in filter_body
packet_stores=re.findall(r'// (?:stw|std|stb|sth) [^,]+,([0-9]+)\(r5\)',filter_body)
assert set(packet_stores)=={'8','64'}
assert not re.search(r'// stf[sd] ',filter_body)
assert '// mr r27,r4' in history
assert not re.search(r'// st(?:w|d|b|h|fs|fd) [^,]+,[^\n]*\(r27\)',history)
for instruction in ['addi r3,r31,424','mr r4,r29','mr r4,r27','mr r3,r29','li r5,256']:
    assert '// '+instruction in history
reset=bodies['822C5470']
for instruction in ['li r5,256','li r4,0','bl 0x8224a558','stb r9,4(r31)','sth r10,68(r31)','stw r10,80(r31)']:
    assert '// '+instruction in reset
parent=bodies['8225CE30']
assert parent.count('sub_822C5470(ctx, base)')==2
assert parent.index('sub_82368CE0(ctx, base)') < parent.index('sub_822C5470(ctx, base)') < parent.index('sub_8235DC98(ctx, base)') < parent.index('sub_822D6EE8(ctx, base)')
out = RESEARCH / 'isolated'  
(out / 'movement_gate_original.cpp').write_text(
    '#include "forge_original.h"\n'
    '#undef DEFINE_REX_FUNC\n#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)\n'
    'namespace h4_forge_original {\n'
    'void sub_82340E60(PPCContext&,uint8_t*);\n'
    + bodies['82582178'] + '\n}\n')
(out / 'full-re-movement.json').write_text(json.dumps(dict(
    scope='Original predicate extraction and static producer trace; not native detachment parity.',
    functions=records, vehicle_selector=dict(offset=1556, stride=12, fields=fields, default=16, runtime_override_flag=3856, runtime_override_value=3857),
    producer_chain=['8225CE30', '823619F8', '82361880', '822562A8', '82582178'],
    intervening_filters={
        '8235DC98':'Packet alias r5 writes only8 and64 (action bits); player120/128 retain state. No float stores. Object resolver branch exists.',
        '822D6EE8':'Packet alias r27 is read-only; copies previous256-byte history168->424 and current packet->168, updates auxiliary local-player state.',
        'frame_preparation':'821F35F0 acquires frame/session data and dispatches through821E8018;82309638 handles session-dependent processing/recording and publishes packet pointer. Neither is established as a direct device-axis producer.',
        'reset':'822C5470 clears256 bytes and sets invalid references; two8225CE30 paths restore packet0/4/16/20/24; second also restores64 and96..128. Analog28/32 remain cleared. Original reset executes in grab fixture.',
        'scope':'Static source/data-flow evidence; called service effects and context gates require separate coverage.'},
    open=['Upstream device-axis mapping and frame packet production', 'Intervening context/reset paths',
          'Complete native selection/alignment/detachment sequence']), indent=2) + '\n')
print(f'Recorded {len(bodies)} H4 functions, H3 assignment/input chain, packet filters and vehicle-control selector layout; extracted unchanged magnet movement predicate.')
