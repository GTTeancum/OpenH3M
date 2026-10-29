"""Repair the identified padded ambient-PRT layout in accepted imported models."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
from map_builder import MapBuilder
from cache_registry import CacheRegistry
from resource_reader import Resource
from build_scenario_checkpoint import resource_salt
from restore_authored_mips import compact_pages

ROOT = Path(__file__).resolve().parents[4]


def repair(basis, xex, output, report):
    if any(not p.resolve().is_relative_to(ROOT) or p.exists() for p in (output,report)):
        raise ValueError('Outputs must be new repository-local files')
    b = MapBuilder(basis,0x200000)
    c, r = b.cache, CacheRegistry(b,resource_salt(xex))
    schema = ET.parse(Path(__file__).resolve().parents[1]/'reference/plugins/mode.xml').getroot()
    field = next(x for x in schema if x.get('name')=='Meshes')
    offset,stride = int(field.get('offset'),0),int(field.get('elementSize'),0)
    repaired,seen = [],set()
    try:
        for tag_index,tag in c.tags.items():
            if tag['group']!='mode' or c.name(tag_index) is not None:
                continue
            meshes=c.block(tag['offset']+offset,stride)
            if not any(c.data[m+47]==1 for m in meshes):continue
            datum=c.u(tag['offset']+224);rid=datum&65535
            res=Resource(c,datum,{'maps\\shared.map':Path('C:/X360/ISOs/H3M/maps/shared.map')})
            buffers=res.buffers('vertex');changes={}
            for mesh in meshes:
                if c.data[mesh+47]!=1:continue
                indices=c.unpack('8h',mesh+24);main,prt=indices[0],indices[3]
                if min(main,prt)<0:continue
                count=res.unpack('I',buffers[main])[0]
                n,fmt,st=res.unpack('IHH',buffers[prt])
                if fmt!=9 or count<=3 or n!=count:continue
                if st!=4 or res.unpack('I',buffers[prt]+8)[0]!=count*4:
                    raise ValueError('Unrecognized ambient buffer layout')
                pointer=res.ptr(buffers[prt]+20)
                if res.fix[buffers[prt]+20]&0xe0000000 != 0x40000000:
                    raise ValueError('Ambient buffer is not in the primary resource')
                data=res.raw[0][pointer:pointer+count*4]
                if len(data)!=count*4 or any(data[j] for j in range(len(data)) if j%4):
                    raise ValueError('Ambient bytes do not match the known padded conversion')
                if prt in changes and changes[prt][0]!=count:raise ValueError('Conflicting mesh counts')
                changes[prt]=(count,pointer,data)
            if not changes:continue
            if rid in seen:raise ValueError('Shared model resource requires explicit review')
            seen.add(rid)
            if len(res.raw)>1 and res.raw[1]:raise ValueError('Secondary model resource requires explicit review')
            end=0
            for kind,sz,ptr in (('vertex',8,20),('index',4,16)):
                for at in res.buffers(kind):
                    if res.fix[at+ptr]&0xe0000000 != 0x40000000:raise ValueError('Non-primary model buffer')
                    end=max(end,res.ptr(at+ptr)+res.unpack('I',at+sz)[0])
            raw=bytearray(res.raw[0][:end]);control=bytearray(res.data)
            for prt,(count,pointer,data) in changes.items():
                packed=data[::4]+bytes((-count)%4)
                raw[pointer:pointer+len(data)]=packed+bytes(len(data)-len(packed))
                struct.pack_into('>I',control,buffers[prt],(count+3)//4)
                struct.pack_into('>I',control,buffers[prt]+8,len(packed))
                repaired.append(dict(tag=tag_index,resource=rid,buffer=prt,vertices=count,
                    native_elements=(count+3)//4,packed_sha256=hashlib.sha256(packed).hexdigest()))
            row=c.block(r.zone+88,64)[rid]
            interops=[c.unpack('II',at) for at in c.block(row+52,8)]
            owner=c.u(row+12);old_salt=r.resources[rid*64+16:rid*64+18]
            r.add_resource(owner,'render_geometry_api_resource_definition',dict(control=bytes(control),
                raw=bytes(raw),root=res.root,fixups=list(res.fix.items()),interops=interops))
            replacement=r.resources[-64:];replacement[16:18]=old_salt
            del r.resources[-64:];r.resources[rid*64:(rid+1)*64]=replacement
        if not repaired:
            raise ValueError('No padded ambient buffers found; refusing an unnecessary map copy')
        r.added_bytes=0
        compact_pages(r);r.finalize()
        payload=b.finish(r.salt);output.write_bytes(payload)
        report.write_text(json.dumps(dict(basis=str(basis),repaired=repaired,bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),resource_slots_preserved=True,
            resource_allocations='Existing allocations retained; only coefficient packing and descriptors corrected'),indent=2)+'\n')
        print(f'{output.name}: repaired {len(repaired)} ambient buffers; {len(payload)} bytes')
    finally:b.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('basis','xex','output','report'):p.add_argument('--'+name,type=Path,required=True)
    repair(**vars(p.parse_args()))
