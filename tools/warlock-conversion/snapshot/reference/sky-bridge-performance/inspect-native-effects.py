"""Summarize captured native effect references without claiming visible output."""
import argparse
import json
from pathlib import Path
import struct
import sys

ref=Path(__file__).resolve().parent;repo=ref.parents[4]
sys.path.insert(0,str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from string_ids import StringTable

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('run',type=Path)
args=parser.parse_args();args.run.resolve().relative_to(repo)
snapshot=json.loads((args.run/'guest-snapshot.json').read_text())
blobs={k:bytes.fromhex(v['bytes']) for k,v in snapshot['blobs'].items()}
cache=Cache(repo/'work/sky-bridge/payload-32/sky_bridge.map')
strings=StringTable(cache)
assert strings.strings[strings.index_for_id(0x231)]=='driver_seat_power'
assert any(cache.u(at+12)==0xebde0a68 and cache.u(at+24)==0x231
           for at in cache.block(cache.tags[0xa08]['offset']+0xbc,32))
def u(raw,at):return struct.unpack_from('>I',raw,at)[0]
def tag(datum):
    index=datum&65535;t=cache.tags.get(index)
    return {'datum':hex(datum),'index':index,'group':t['group'],'name':cache.name(index)} if t and t['salt']==datum>>16 else None
tables=[]
for offset,field,group in [(0x88,8,'effe'),(0xe8,4,'ligh'),(0x154,12,'effe')]:
    header=blobs['tls_block_'+hex(offset)];data=blobs['table_'+hex(offset)]
    capacity,stride=struct.unpack_from('>II',header,0x20)
    assert len(data)==capacity*stride
    rows=[]
    for index in range(capacity):
        row=data[index*stride:(index+1)*stride];salt=struct.unpack_from('>H',row)[0]
        if salt in [0,65535]:continue
        reference=tag(u(row,field))
        if reference is None or reference['group']!=group:raise ValueError('Unexpected tag reference in occupied row')
        rows.append({'index':index,'datum':hex((salt<<16)|index),'reference':reference})
    count=u(header,0x3c)
    assert len(rows)==count
    tables.append({'tls_offset':hex(offset),'record_stride':stride,'tag_reference_offset':hex(field),
      'nonzero_salt_rows':len(rows),'header_counter_0x3c':count,'rows':rows})
vehicle=blobs['object_0xe2780009'];human=json.loads((repo/'work/sky-bridge/pixel-probe-20261103-203123/reproduction-view-full/guest-snapshot.json').read_text())
human_vehicle=bytes.fromhex(human['blobs']['object_0xe2780009']['bytes'])
handle=u(vehicle,0x788)
headlight=next(r for r in tables[1]['rows'] if int(r['datum'],16)==handle)
assert headlight['reference']['name']=='objects\\vehicles\\mongoose\\fx\\running\\headlights'
report={'capture_site':snapshot['guest_frame_hook'],'tables':tables,
 'weather_references':{t['tls_offset']:[r for r in t['rows'] if r['reference']['index']==10701] for t in tables if t['tls_offset']!='0xe8'},
 'mongoose':{'human_light_handle':hex(u(human_vehicle,0x788)),'replay_light_handle':hex(handle),
   'light_record':headlight,'driver_seat_power':{
    'human_enabled':bool(human_vehicle[683]&1),'human_value':struct.unpack_from('>f',human_vehicle,684)[0],
    'replay_enabled':bool(vehicle[683]&1),'replay_value':struct.unpack_from('>f',vehicle,684)[0],
    'field_evidence':'Native sub_820F99E0 string-ID 561 branch at 820F9AB4 reads bit 0 of byte +683 and float +684; actual retail StringTable resolves 0x231 to driver_seat_power. vehi Attachments +0xBC uses this primary scale for headlights.'}},
 'limitations':['Nonzero salt rows match the captured table count; this is allocated state, not proof of visible light or particle contribution.',
   'Weather effect 10701 is instantiated and referenced by two particle systems. GPU particle emission, draw contribution and visibility are not established by these references.',
   'Human light payload coverage ends after four complete records and one partial record. The two additional light entries in that later snapshot cannot be identified from it.',
   'The human snapshot was captured after its flicker recording. Count differences do not attribute the flash.'],
 'credit':json.loads((ref/'sky-pixel-probe-build.json').read_text())['credit']}
cache.close()
(args.run/'native-effects-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'allocated_effects':tables[0]['nonzero_salt_rows'],'allocated_lights':tables[1]['nonzero_salt_rows'],
 'allocated_particle_systems':tables[2]['nonzero_salt_rows'],'weather_effect_rows':len(report['weather_references']['0x88']),
 'weather_particle_system_rows':len(report['weather_references']['0x154']),'mongoose_driver_power_equal':report['mongoose']['driver_seat_power']['human_value']==report['mongoose']['driver_seat_power']['replay_value']}))
