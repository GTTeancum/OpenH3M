"""Compare a retained stock Battle Rifle graph with original-disc Zanzibar."""
import hashlib
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

BR = 0xee850d0f

def audit(c):
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

    report=dict(donor=str(donor_path.resolve()),donor_sha256=hashlib.sha256(donor.data).hexdigest(),native_dependency_tags=len(dependencies),native_metadata_bytes_compared=compared,native_resources_compared=len(resources),inherited_stripped_default_resources=differences)
    donor.close()
    return report
