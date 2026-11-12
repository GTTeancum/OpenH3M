"""Record placement-path provenance and verify original constants/call ordering."""
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'work/h4-forge-research'
locations = {'8244A8D8':194, '8244B860':147, '82451FC0':241,
             '82452930':2, '8249B418':222, '82452B48':130,
             '82451BA8':182, '8221CA38':51, '82282580':52, '8244EED8':70,
             '8244D0E0':196, '8244A7D0':105, '8244AF48':201, '8244B338':167,
             '822ED938':91, '8244B518':127, '8244A6A8':262,
             '824BEA10':62, '824BEAD0':101, '824BE840':259,
             '821D6D90':93, '822410D0':44, '8225EA20':30,
             '8244B758':146, '822E15E0':165, '822C8040':99,
             '824BEB50':56, '8221B258':289, '82260CF0':237, '82417550':265, '824F5E28':204, '824F5F78':239,
             '824169F8':87, '82416DF8':206, '82416AD0':286}
records = {}
bodies = {}
for address, number in locations.items():
    path = R / f'generated/halo4_recomp.{number}.cpp'
    text = path.read_text()
    marker = f'DEFINE_REX_FUNC(sub_{address}) {{'
    start = text.index(marker)
    body = (marker + text[start + len(marker):].split('DEFINE_REX_FUNC(', 1)[0]).strip()
    bodies[address] = body
    records[address] = dict(file=path.name, line=text.count('\n', 0, start)+1,
        sha256=hashlib.sha256(body.encode()).hexdigest(),
        calls=re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)', body))
for address, terminal in [('8244A8D8','82452930'), ('8244B860','8249B418')]:
    body=bodies[address]
    assert body.index('sub_82451A38(ctx, base)') < body.index('sub_8244EED8(ctx, base)') < body.index(f'sub_{terminal}(ctx, base)')
    assert body.count('sub_82282580(ctx, base)') == 2
    assert 'sub_8221CA38(ctx, base)' in body
assert '// lfs f1,76(r3)' in bodies['82452B48']
constants = {}
switches = {}
with (R/'h4-image.bin').open('rb') as image:
    for offset, expected in [(0,0),(4,1),(276,.05),(556,.001),(12,.1),(16,3),(20,2),(32,15),(40,.5),(60,.3),(88,4),(256,.2),(292,.4)]:
        image.seek(0x1289e0+offset)
        raw=image.read(4)
        value=struct.unpack('>f',raw)[0]
        assert abs(value-expected)<1e-6
        constants[hex(0x821289e0+offset)] = dict(bytes=raw.hex(), value=value)
    for address in [0x8407effa,0x8407effb]:
        image.seek(address-0x82000000)
        switches[hex(address)]=image.read(1)[0]
assert switches=={'0x8407effa':0,'0x8407effb':0}
dispatcher=bodies['8244D0E0']
assert '// lbz r10,-4102(r11)' in dispatcher
assert '// bne cr6,0x8244d620' in dispatcher
assert dispatcher.index('sub_8244A7D0(ctx, base)') < dispatcher.index('sub_82452738(ctx, base)') < dispatcher.index('sub_8244A8D8(ctx, base)') < dispatcher.index('sub_8244AF48(ctx, base)')
held_dispatch = dispatcher.split('loc_8244D514:',1)[1].split('loc_8244D628:',1)[0]
for instruction in ['bl 0x822ed938', 'beq cr6,0x8244d670', 'lwz r11,36(r31)',
                    'lwz r9,240(r31)', 'mulli r10,r10,176', 'lwz r9,16(r11)',
                    'rlwinm r7,r9,30,31,31', 'bne cr6,0x8244d584',
                    'bne cr6,0x8244d5a4', 'beq cr6,0x8244d628']:
    assert '// '+instruction in held_dispatch
ownership = bodies['822ED938']
for instruction in ['li r11,140','lbz r7,104(r11)','li r9,6','bl 0x822714e0',
                    'addi r11,r3,20','addi r8,r11,6','subf. r9,r7,r9']:
    assert '// '+instruction in ownership
report=dict(scope='Static original-code evidence; does not execute physics or prove native placement parity.',
    functions=records, constants=constants, image_switch_defaults=switches,
    ordering=['bounds clamp','movement projection/length limit','bounds clamp','rotation quantization','magnet gate/alignment','physics target update'],
    dispatcher_gates=dict(function='8244D0E0',
        main_path='Editor eligible; held datum valid; player ownership matches; parent36=-1; physics240 valid; instance16 bit0x4 set',
        ownership='822ED938: TLS140 enabled byte104 and six-byte identity105..110 match valid player20..25',
        sequence='rotation; editor36=max(editor36-editor40,0); distance clamp; held update; monitor update; refresh held cached point8..16',
        caveat='Static evidence; preview, remote/session, attachment and callback effects require connected execution'),
    open=['Runtime writers/names of placement switches','Grab-offset producer and reset lifecycle',
          'World query and physics helper equivalence','H3 adapter','Native full interaction evidence'])
assert '// addi r11,r11,376' in bodies['824BE840']
assert '// lfs f11,6552(r11)' in bodies['824BE840'] # editor+36
assert '// lfs f10,6572(r11)' in bodies['824BE840'] # editor+56
assert '// lfs f0,6920(r9)' in bodies['824BE840'] # editor+28
assert '// fneg f0,f1' in bodies['824BEA10']
assert '// lwz r10,100(r11)' in bodies['8225EA20']
report['camera_observations'] = {
    'held_based_point': 'held queried position + editor36 * editor56/60/64',
    'view_direction': 'controlled unit1212/1216/1220',
    'offset': '8244B758 -> 821D6D90 basis-relative application',
    'distance_backoff': '824BEA10 subtracts direction * editor28 after offset;824BEAD0 does not',
    'root_position': '822410D0 ->8225EA20 copies object100/104/108 for unattached fallback',
    'open': 'view curves, parent/alternate position paths, real collision/world integration; see executed controller suite separately'
}
prediction=bodies['824BEB50']
for call in ['82260CF0','8225EA20','82243068','8249B1F8','8232F708']:
    assert f'sub_{call}(ctx, base)' in prediction
assert prediction.index('sub_82260CF0(ctx, base)') < prediction.index('sub_8249B1F8(ctx, base)') < prediction.index('sub_8232F708(ctx, base)')
monitor=bodies['8244AF48']
assert monitor.index('sub_824BEA10(ctx, base)') < monitor.index('sub_82452930(ctx, base)')
assert '// lfs f1,276(r28)' in monitor
assert '// stfs f3,32(r11)' in monitor
report['camera_observations']['prediction'] = {
    'mode1': '824BE840 invokes824BEB50 before basis offset and distance backoff',
    'linear': 'speed*time threshold, bounded by cached editor8/12/16 versus current root position',
    'angular': 'valid physics instance/body count enables relative-transform correction via8249B1F8 and8232F708',
    'monitor': '8244AF48 caps desired displacement at2, optionally removes inward normal component, builds orientation then82452930',
    'state_writeback': 'editor32=min(resulting separation,retained distance);editor276 directional history conditionally updated',
    'velocity_source': '82260CF0 selects forced global vector, valid physics body queries, or object136/140/144 linear and148/152/156 angular fallback',
    'status': 'static audit only; controller suite separately executes prediction and monitor branches with synthetic world data'
}
collision=bodies['82417550']
assert collision.index('sub_824AA580(ctx, base)') < collision.index('sub_82416438(ctx, base)') < collision.index('sub_824A9D68(ctx, base)') < collision.index('sub_82416DF8(ctx, base)')
assert collision.count('// lwarx r11,0,r9') == 2
assert collision.count('// addi r11,r11,-1') == 2
assert '// lwz r11,9136(r29)' in collision
ray=bodies['824F5E28']
for instruction in ['li r8,27','stw r8,176(r1)','std r3,180(r1)','stw r6,212(r1)','stb r11,468(r1)','lfs f0,3312(r10)']:
    assert '// '+instruction in ray
report['collision_boundary']={
 'entry':'82417550', 'request_wrapper':'824F5E28',
 'request_layout':{'type':0,'mask64':4,'start':12,'end':24,'excluded_objects':36,'excluded_count':292},
 'world_path':'824AA580 shared-world acquisition; readiness flag;82416438 builds query context;824A9D68 dispatches;82416DF8 converts result; optional82416AD0; atomic reference decrement on both exits',
 'result':'fraction+4,point+8; wrapper preserves fraction on miss and defaults point to endpoint',
 'h3_mapping':'82281268 ->820AD3E0 ->820AEA78; H3 takes start plus displacement, three excluded identities and a different mask. This is an identified candidate service, not established semantic equivalence.',
 'open':'world ownership/readiness semantics, native H3 request/callback mapping, actual geometry and concurrency verification'}
initialize=bodies['824169F8']
merge=bodies['82416AD0']
objects=bodies['82416DF8']
for instruction in ['stfs f0,4(r3)', 'stw r10,8(r3)', 'stw r4,16(r3)', 'stw r30,40(r3)']:
    assert '// '+instruction in initialize
for instruction in ['lfs f13,4(r6)', 'lfs f0,16(r5)', 'ble cr6,0x82416dec',
                    'stfs f0,4(r6)', 'stw r26,0(r31)', 'stw r28,40(r31)',
                    'li r11,3', 'stw r11,0(r31)', 'lbz r10,296(r25)', 'lbz r11,297(r25)']:
    assert '// '+instruction in merge
assert 'sub_82416120(ctx, base)' in objects
assert 'sub_82415178(ctx, base)' in objects
assert 'sub_82416948(ctx, base)' in objects
report['collision_boundary']['result_merge']={
 'initialize':'824169F8 initializes fraction and endpoint, clears metadata and uses invalid object identity',
 'object_processing':'82416DF8 processes sorted candidates and retains nearer results; includes82416120 and82415178 filters and shape virtual queries',
 'geometry_merge':'82416AD0 replaces current result only when its fraction is strictly larger than incoming fraction; equal fraction preserves previous result',
 'geometry_fields':'interpolated point+8, normal+20, plane+60/+72; type0 and invalid object+40 initially; metadata8199 value1 changes type to3',
 'optional_metadata':'request296/297 gate additional material/geometry information; camera wrapper initializes both to0',
 'status':'static source audit only; native traversal, complete flags and result equivalence remain open'
}
(R/'isolated/full-re-placement.json').write_text(json.dumps(report,indent=2)+'\n')
(R/'isolated/rotation_gate_original.cpp').write_text(
    '#include "forge_original.h"\n#undef DEFINE_REX_FUNC\n'
    '#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)\n'
    'namespace h4_forge_original {\n'+bodies['8244A6A8']+'\n}\n')
print(f'Verified placement orders/constants and camera field expressions; recorded {len(records)} original functions and extracted rotation gate.')
