"""Decode the bounded native snapshot and compare portable state with the human run."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import struct


def decode(path):
    raw=path.read_bytes()
    magic,version=struct.unpack_from('<II',raw)
    if len(raw)>17*1024*1024 or magic!=0x534e4b53 or version not in [1,2]:
        raise ValueError('Unexpected native-state header')
    magic,valid,records,total=struct.unpack_from('<4I',raw,len(raw)-16)
    if magic!=0x444e4553 or valid!=1 or records>4096:
        raise ValueError('Snapshot is incomplete')
    timestamp=struct.unpack_from('<Q',raw,8)[0]/1e9
    site,tls=struct.unpack_from('<II',raw,16) if version==2 else (0,0)
    blobs={};offset=24 if version==2 else 16;actual=0
    while offset<len(raw)-16:
        name=raw[offset:offset+32].split(b'\0')[0].decode('ascii')
        address,size=struct.unpack_from('<II',raw,offset+32);offset+=40
        if not name or name in blobs or not size or size>2*1024*1024 or offset+size>len(raw)-16:
            raise ValueError('Invalid native-state record')
        blobs[name]={'guest_address':hex(address),'bytes':raw[offset:offset+size].hex()}
        offset+=size;actual+=size
    if offset!=len(raw)-16 or len(blobs)!=records or actual!=total:
        raise ValueError('Snapshot trailer does not match payload')
    return {'captured_unix_time':timestamp,'guest_frame_hook':hex(site),'tls':hex(tls),'blobs':blobs}


def summarize(snapshot):
    blobs={k:bytes.fromhex(v['bytes']) for k,v in snapshot['blobs'].items()}
    def u(raw,at):return struct.unpack_from('>I',raw,at)[0]
    clock=blobs['tls_block_0xbc'];rate=struct.unpack_from('>h',clock,4)[0]
    if clock[0]!=1 or rate!=30 or abs(struct.unpack_from('>f',clock,8)[0]-1/30)>1e-7:
        raise ValueError('Unexpected native game-time layout')
    ticks=struct.unpack_from('>i',clock,12)[0]
    tables=[]
    for name,raw in blobs.items():
        if not name.startswith('tls_block_'):continue
        label=raw[:32].split(b'\0')[0]
        if label and all(32<=c<127 for c in label):
            tables.append({'tls_offset':name.removeprefix('tls_block_'),'label':label.decode(),
              'capacity':u(raw,0x20),'stride':u(raw,0x24),
              'header_counters_38_40':[u(raw,at) for at in [0x38,0x3c,0x40]]})
    objects=[]
    for name,raw in blobs.items():
        if name.startswith('object_0x'):
            handle=int(name.removeprefix('object_'),16);index=handle&65535
            head=blobs['object'][index*16:index*16+16]
            if len(head)!=16 or struct.unpack_from('>H',head)[0]!=(handle>>16):continue
            objects.append({'index':index,'tag':hex(u(raw,0)), 'type':head[3],
              'parent_index':None if u(raw,0x10)==0xffffffff else u(raw,0x10)&65535,
              'position':list(struct.unpack_from('>3f',raw,0x54)),
              'forward':list(struct.unpack_from('>3f',raw,0x60)),
              'up':list(struct.unpack_from('>3f',raw,0x6c))})
    return {'captured_unix_time':snapshot['captured_unix_time'],
      'local_time':datetime.datetime.fromtimestamp(snapshot['captured_unix_time']).isoformat(),
      'game_ticks':ticks,'tick_rate':rate,'game_seconds':ticks/rate,
      'game_speed':struct.unpack_from('>f',clock,16)[0],
      'map_id':u(blobs['map_variant'],0x100),
      'map_variant_sha256':hashlib.sha256(blobs['map_variant']).hexdigest(),
      'map_variant_counts':list(struct.unpack_from('>4H',blobs['map_variant'],0xf8)),
      'tables':tables,'objects':objects}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args();repo=Path(__file__).resolve().parents[5]
    args.run.resolve().relative_to(repo)
    human_path=repo/'work/sky-bridge/pixel-probe-20261103-203123/reproduction-view-full/guest-snapshot.json'
    human_raw=json.loads(human_path.read_text());replay_raw=decode(args.run/'native-state.bin')
    a,b=summarize(human_raw),summarize(replay_raw)
    different=[];ao={o['index']:o for o in a['objects']};bo={o['index']:o for o in b['objects']}
    for index in sorted(ao.keys()|bo.keys()):
        if ao.get(index)!=bo.get(index):different.append({'index':index,'human':ao.get(index),'replay':bo.get(index)})
    tables=[];at={t['tls_offset']:t for t in a['tables']};bt={t['tls_offset']:t for t in b['tables']}
    for offset in sorted(at.keys()|bt.keys(),key=lambda s:int(s,16)):
        if at.get(offset)!=bt.get(offset):tables.append({'human':at.get(offset),'replay':bt.get(offset)})
    report={'human':{k:v for k,v in a.items() if k!='objects'},'replay':{k:v for k,v in b.items() if k!='objects'},
      'capture_sites':{'human':human_raw['guest_frame_hook'],'replay':replay_raw['guest_frame_hook'],
                       'same_native_entry':human_raw['guest_frame_hook']==replay_raw['guest_frame_hook']},
      'object_counts':[len(ao),len(bo)],'different_objects':different,'different_table_headers':tables,
      'limitation':'The human snapshot was captured after its flicker recording, not on a bad frame. Elapsed time and effect/object states may have changed in between. Raw pointers and handles are never restored; table header counter names are intentionally not inferred.',
      'credit':json.loads((Path(__file__).parent/'sky-pixel-probe-build.json').read_text())['credit']}
    (args.run/'native-state-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.run/'guest-snapshot.json').write_text(json.dumps(replay_raw,indent=2)+'\n')
    print(json.dumps({'human_game_seconds':a['game_seconds'],'replay_game_seconds':b['game_seconds'],
      'object_counts':report['object_counts'],'different_objects':len(different),
      'different_table_headers':len(tables),'variant_equal':a['map_variant_sha256']==b['map_variant_sha256']}))
