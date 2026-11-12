"""Retire unreachable named basis assets, preserving all unnamed imports.

Leaves installation unchanged. Requires the conservative graph audit and
checks every retained compressed page and every other metadata byte.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

from audit_console_unused_tags import audit, ROOT, SCHEMAS
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from build_scenario_checkpoint import resource_salt
from cache_reader import Cache
from map_builder import MapBuilder
from build_dlc_live import build
from verify_dlc_stfs import verify_payload
from console_cache_limits import inspect_map


def main():
    current=json.loads((ROOT/'.local/releases/current-live/manifest.json').read_text())
    bundle=next(b for b in current['packages'] if 'forge_gulch' in b['maps'])
    source=Path(bundle['installed_source'])/'forge_gulch.map'
    out=ROOT/'.local/releases/console-repair-candidate/maps/forge_gulch'
    if out.exists():
        raise ValueError('Inspect existing candidate before replacement')
    report=audit(source,protect_unnamed=True)
    if report['schema_errors']:
        raise ValueError('Resolve schema errors before compaction')
    dead={t['index'] for t in report['tags_for_review']}
    assert len(dead)==309 and all(t['name'] for t in report['tags_for_review'])
    b=MapBuilder(source,0);c=b.cache
    allowed=set()
    def put(at,fmt,*values):
        size=struct.calcsize('>'+fmt)
        allowed.update(range(at-c.start,at-c.start+size))
        b.put(at-c.start+c.base,fmt,*values)
    index=c.pointer(c.u(16));tags=c.pointer(c.u(index+12))
    for i in dead:
        put(tags+i*8,'HHI',65535,65535,0)
    zone=next(t['offset'] for t in c.tags.values() if t['group']=='zone')
    play=next(t['offset'] for t in c.tags.values() if t['group']=='play')
    locations,pages=c.block(play+48,16),c.block(play+24,88)
    used,retired=set(),set()
    handles={(t['salt']<<16)|i:i for i,t in c.tags.items()}
    for i,r in enumerate(c.block(zone+88,64)):
        li=c.unpack('h',r+34)[0]
        if handles.get(c.u(r+12)) in dead:
            retired.add(i)
            put(r+34,'h',-1)
        elif li>=0:
            used.update(p for p in c.unpack('2h',locations[li]) if p>=0)
    schema=ET.parse(SCHEMAS/'zone.xml').getroot()
    for field in schema:
        if field.tag.lower()!='tagblock' or 'Manifest' not in field.get('name',''):
            continue
        for at in c.block(zone+int(field.get('offset'),0),120):
            for block in field:
                name=block.get('name','')
                if block.tag.lower()!='tagblock' or 'Bits' not in name:
                    continue
                rows=c.block(at+int(block.get('offset'),0),4)
                ids=retired if 'Resource' in name else dead if 'Owner' in name else set()
                masks={}
                for i in ids:
                    if i//32<len(rows):
                        masks[i//32]=masks.get(i//32,0)|(1<<(i%32))
                for i,mask in masks.items():
                    put(rows[i],'I',c.u(rows[i])&~mask)
    raw_base=(c.u(0x484)+c.u(0x470))&0xffffffff
    packed=bytearray();moved={};retained=[]
    for i,p in enumerate(pages):
        if c.unpack('h',p+4)[0]!=-1:
            continue
        offset,size=c.unpack('II',p+8)
        if i not in used:
            put(p+8,'III',0,0,0)
            continue
        blob=c.data[raw_base+offset:raw_base+offset+size]
        assert len(blob)==size
        key=hashlib.sha256(blob).digest()
        if key not in moved:
            moved[key]=len(packed)
            packed.extend(blob);packed.extend(bytes((-len(packed))%4096))
        put(p+8,'I',moved[key]);retained.append(i)
    original_meta=c.data[c.start:c.start+c.u(0x490)]
    differences=[i for i,(x,y) in enumerate(zip(original_meta,b.meta)) if x!=y]
    assert set(differences)<=allowed
    b.compacted_raw=packed
    data=b.finish(resource_salt(ROOT/'../../default.xex'))
    assert len(data)<=157286400
    payload=out/'payload';payload.mkdir(parents=True)
    target=payload/source.name;target.write_bytes(data)
    check=Cache(target)
    assert check.base==c.base and check.u(0x490)==c.u(0x490)
    assert set(check.tags)==set(c.tags)-dead
    cp=next(t['offset'] for t in check.tags.values() if t['group']=='play')
    checkpages=check.block(cp+24,88)
    new_raw=(check.u(0x484)+check.u(0x470))&0xffffffff
    for i in retained:
        old,new=pages[i],checkpages[i]
        off,size=c.unpack('II',old+8);new_off,new_size=check.unpack('II',new+8)
        assert size==new_size
        assert c.data[raw_base+off:raw_base+off+size]==check.data[new_raw+new_off:new_raw+new_off+size]
    assert check.data[check.start:check.start+check.u(0x490)]==b.meta
    gate=inspect_map(target)
    check.close()
    info=source.with_suffix('.mapinfo').read_bytes()
    title=info[0x44:0x84].decode('utf-16-be').split('\0')[0]
    preview=info[0xF44:0x1044].split(b'\0')[0].decode('ascii')
    names=[source.with_suffix('.mapinfo').name]+[preview+s+'.blf' for s in ('','_sm','_clip','_film','_variant')]
    assert preview and not any(x in preview for x in '/\\:')
    for name in names:
        os.link(source.parent/name,payload/name)
    result=build(payload,out/'Content/0000000000000000/4D5307E6/00000002/building')
    result['payload_verification']=verify_payload(Path(result['package']),payload)
    result.update(map='forge_gulch',title=title,source_map=str(source),
        original_map_sha256=hashlib.sha256(c.data).hexdigest(),
        corrected_map_sha256=hashlib.sha256(data).hexdigest(),cache_size_gate=gate,
        retired_tag_indices=sorted(dead),retired_resource_indices=sorted(retired),
        retained_local_pages_compared=len(retained),all_retained_page_bytes_identical=True,
        metadata_difference_bytes=len(differences),metadata_edits_bounded=True,
        protected_all_unnamed_imports=True,body_unchanged=False,xex_changes='None',
        console_status='Hardware unverified compaction candidate; host regression pending',
        correction='Retire unreachable named basis tags/resources; lossless raw-page deduplication; disable stale optimized header',
        attribution='Forge World, Halo Reach; Ryno, Forge World - Halo 3, Workshop3597611181 https://steamcommunity.com/sharedfiles/filedetails/?id=3597611181 . Gulch partition and Xbox360/OpenH3M adaptation by this project.')
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'retired-tag-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('package','cache_size_gate','retained_local_pages_compared','metadata_edits_bounded')},indent=2))
    b.close()


if __name__=='__main__':
    main()
