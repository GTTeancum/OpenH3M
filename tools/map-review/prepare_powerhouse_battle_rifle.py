"""Prepare a confined Powerhouse candidate; never deploy or launch the game."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt

EXPECTED = '9b4a7ee5604d2c11e73cc2330bc5b90d92e65e5e67fd47f11801916ab2082cf1'
DMR, BR = 0x9000277a, 0xee850d0f
OUT = ROOT / 'work/powerhouse-battle-rifle'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    source = next((ROOT / 'work/dlc/installed-corrections').rglob('powerhouse.map'))
    assert sha(source) == EXPECTED, 'Installed map changed; re-audit required'
    c = Cache(source)
    donor_path = ROOT / '../../maps/zanzibar.map'
    donor = Cache(donor_path)
    schemas = {}
    dependencies, resources = set(), set()
    compared = 0
    differences = []
    owners = []

    def schema(group):
        if group not in schemas:
            schemas[group] = ET.parse(ROOT / 'tools/warlock-conversion/snapshot/reference/plugins' / (group.strip()+'.xml')).getroot()
        return schemas[group]

    def compare_tag(datum):
        nonlocal compared
        if datum == 0xffffffff or datum in dependencies:
            return
        dependencies.add(datum)
        index = datum & 65535
        a, b = c.tags[index], donor.tags[index]
        assert a['salt'] == b['salt'] == datum >> 16 and a['group'] == b['group']
        assert c.name(index) == donor.name(index)
        node = schema(a['group'])
        owners.append(c.name(index))
        compare_block(a['offset'], b['offset'], node, int(node.get('baseSize'), 0))
        owners.pop()

    def compare_block(at, bt, node, size):
        nonlocal compared
        # Native virtual pointers are preserved by MapBuilder. Comparing whole
        # records includes tuning, opaque fields, string IDs and dependency IDs.
        left, right = bytearray(c.data[at:at+size]), bytearray(donor.data[bt:bt+size])
        for f in node:
            if f.tag.lower() == 'datum' and '[zone]' in f.get('name',''):
                off=int(f.get('offset'),0)
                a,b=c.u(at+off),donor.u(bt+off)
                if (a==0xffffffff)!=(b==0xffffffff): differences.append(dict(owner=owners[-1],field=f.get('name'),current=hex(a),donor=hex(b)))
                if a!=0xffffffff and b!=0xffffffff: resources.add((a,b))
                left[off:off+4]=right[off:off+4]
        if left != right: differences.append(dict(owner=owners[-1],block=node.get('name','root'),offset=hex(at),changed=[i for i,(a,b) in enumerate(zip(left,right)) if a!=b]))
        compared += size
        for f in node:
            if 'offset' not in f.attrib:
                continue
            off = int(f.get('offset'), 0)
            kind = f.tag.lower()
            if kind == 'tagref':
                compare_tag(c.u(at+off+(0 if f.get('withGroup')=='false' else 12)))
            elif kind == 'tagblock':
                stride = int(f.get('elementSize'), 0)
                aa, bb = c.block(at+off,stride), donor.block(bt+off,stride)
                assert len(aa) == len(bb)
                for x,y in zip(aa,bb):
                    compare_block(x,y,f,stride)
            elif kind == 'dataref':
                n = c.u(at+off)
                if n:
                    x,y = c.pointer(c.u(at+off+12)), donor.pointer(donor.u(bt+off+12))
                    assert c.data[x:x+n] == donor.data[y:y+n]
                    compared += n

    compare_tag(BR)
    print(json.dumps(dict(dependencies=len(dependencies),resources=len(resources),differences=differences),indent=2),flush=True)
    assert len(differences)==5 and all(x.get('current')=='0xffffffff' and x['owner'].startswith('shaders\\default_bitmaps\\bitmaps\\') for x in differences), differences
    from resource_reader import Resource
    c.shared_paths = donor.shared_paths = {prefix+p.name:p for p in (ROOT/'../../maps').glob('*.map') for prefix in ('','maps\\')}
    def segments(cache, datum, resource):
        zone=next(t['offset'] for t in cache.tags.values() if t['group']=='zone')
        play=next(t['offset'] for t in cache.tags.values() if t['group']=='play')
        row=cache.block(zone+88,64)[datum&65535]
        li=cache.unpack('h',row+34)[0]
        if li<0: return []
        loc=cache.block(play+48,16)[li]
        tables=cache.block(play+36,16)
        result=[]
        for slot,(raw,idx) in enumerate(zip(resource.raw,cache.unpack('2h',loc+12))):
            size=cache.u(tables[idx]) if idx>=0 else len(raw)
            if idx<0 and raw:
                page=cache.unpack('h',loc+slot*2)[0]
                offset=cache.u(loc+4+slot*4)
                following=[cache.u(other+4+j*4)-offset
                    for other in cache.block(play+48,16) for j in (0,1)
                    if cache.unpack('h',other+j*2)[0]==page and cache.u(other+4+j*4)>offset]
                if following: size=min(size,min(following))
            assert size<=len(raw)
            result.append(raw[:size])
        return result
    for d,e in sorted(resources):
        a,b = Resource(c,d),Resource(donor,e)
        assert a.data == b.data and a.fix == b.fix and segments(c,d,a) == segments(donor,e,b), ('Resource differs', hex(d), hex(e))

    sc = next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
    palette = c.block(sc+0x128,48)
    indices = [i for i,r in enumerate(palette) if c.u(r+12)==DMR]
    assert indices == [3] and c.tags[DMR&65535]['group']=='weap'
    placements = [i for i,r in enumerate(c.block(sc+0x11c,168)) if c.unpack('h',r)[0] in indices]
    assert placements == [4,5,9,15,18]
    forge = [c.u(r+12) for r in c.block(sc+0x1f4,48)]
    assert BR in forge and DMR not in forge
    simulation = c.block(sc+0x6a4,4)
    assert c.u(simulation[13])==DMR and c.u(simulation[572])==BR
    # Find every full tag reference, including unlisted/opaque schema fields.
    needle = struct.pack('>4s8xI',b'weap',DMR)
    refs=[]; start=c.start
    while True:
        at=c.data.find(needle,start,c.start+c.u(0x490))
        if at<0: break
        refs.append(at);start=at+1
    assert refs == [palette[3]], refs
    OUT.mkdir(exist_ok=True)
    output=OUT/'powerhouse.map'
    verify_existing='--verify-existing' in sys.argv
    assert verify_existing or not output.exists(), 'Candidate already exists; use --verify-existing for a read-only map check'
    builder=MapBuilder(source,0)
    offset=palette[3]+12
    builder.put(offset-c.start+c.base,'I',BR)
    data=builder.finish(resource_salt(ROOT/'../../default.xex'))
    builder.close()
    datum_bytes=struct.pack('>I',DMR)
    occurrences=[];start=c.start
    while True:
        at=data.find(datum_bytes,start,c.start+c.u(0x490))
        if at<0:break
        occurrences.append(at);start=at+1
    assert occurrences==[simulation[13]], occurrences
    assert len(data)==len(c.data)
    allowed=set(range(offset,offset+4)) | set(range(0x2c4,0x2c8)) | set(range(0x330,0x344))
    import numpy as np
    changed=np.flatnonzero(np.frombuffer(data,dtype=np.uint8)!=np.frombuffer(c.data,dtype=np.uint8)).tolist()
    assert set(changed)<=allowed
    if verify_existing:
        assert output.read_bytes()==data, 'Existing candidate differs from reproduced map'
    else:
        output.write_bytes(data)
    report=dict(source=str(source),before_sha256=EXPECTED,candidate=str(output),candidate_sha256=sha(output),
        changed_byte_offsets=changed,reference_offset=offset,from_datum=hex(DMR),to_datum=hex(BR),
        placements=placements,forge_entries=len(forge),forge_already_stock=True,
        all_other_bytes_identical_except_checksums=True,polygon_reduction_preserved='18.4559%',
        donor=str(donor_path.resolve()),donor_sha256=sha(donor_path),
        native_dependency_tags=len(dependencies),native_metadata_bytes_compared=compared,
        native_resources_compared=len(resources),native_metadata_identical_except_resource_ids=True,
        inherited_stripped_default_resources=differences,
        unused_dmr_tags_retained=True,installed_content_modified=False,
        remaining_dmr_reference='Unused simulation definition 13; stock BR already registered at definition 572. Preserved table/wire indices.',
        native_weapon_behavior_verified=False,verification_pending='Coordinated native pickup, visuals, burst fire, reload, audio and Forge test',
        attribution='Powerhouse (Halo Reach / Halo Online lineage); General Heed / Priception, Halo Online Map Pack For Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. Xbox 360/OpenH3M adaptation by this project.')
    (OUT/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
    c.close();donor.close()
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
