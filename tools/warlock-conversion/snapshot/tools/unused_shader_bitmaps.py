"""Retire only unreferenced, newly cloned shader-prototype donor bitmaps.

No source files or payload bytes change. Unknown metadata is conservative: a
candidate handles in live or unmapped metadata prevent retirement. Exact
allocator provenance permits only demonstrably unreachable ranges to be ignored.
"""
import struct
import bisect
import hashlib
import numpy as np
import xml.etree.ElementTree as ET


def _allocation_reachability(builder,tags):
    """Conservative pointer closure over exact allocations, including interiors.

    Missing or invalid ledgers disable this refinement, retaining the original
    whole-metadata raw-handle guard. No unknown bytes are assumed unreachable.
    """
    ranges=getattr(builder,'allocations',None)
    if ranges is None:return None
    ranges=[(int(a),int(n)) for a,n in ranges if n]
    end=builder.base
    for at,size in ranges:
        if size<0 or at<end or at<builder.base or at+size>builder.base+builder.used:
            raise ValueError('Invalid staged allocation ledger')
        end=at+size
    starts=[a for a,n in ranges]
    def containing(address):
        n=bisect.bisect_right(starts,address)-1
        return n if n>=0 and address<ranges[n][0]+ranges[n][1] else None
    def targets(data):
        found=set()
        for shift in range(4):
            count=(len(data)-shift)//4
            if count<=0:continue
            words=np.frombuffer(data,dtype='>u4',count=count,offset=shift)
            words=words[(words>=builder.base)&(words<builder.base+builder.used)]
            for value in np.unique(words):
                index=containing(int(value))
                if index is not None:found.add(index)
        return found
    # All original bytes are conservative roots, even retired basis metadata.
    roots=targets(bytes(builder.meta[builder.reserve:]))
    for group,address in tags.values():
        n=containing(address)
        if n is not None:roots.add(n)
    # Treat unmapped padding/extra staging bytes as opaque roots as well.
    cursor=0
    for at,size in ranges:
        offset=at-builder.base
        roots|=targets(bytes(builder.meta[cursor:offset]));cursor=offset+size
    roots|=targets(bytes(builder.meta[cursor:builder.reserve]))
    # A word crossing allocation boundaries has no single proven owner.
    # Conservatively root every possible pointer in these boundary windows.
    for at,size in ranges:
        for boundary in (at-builder.base,at-builder.base+size):
            roots|=targets(bytes(builder.meta[max(0,boundary-3):boundary+3]))
    edges=[targets(bytes(builder.meta[a-builder.base:a-builder.base+n])) for a,n in ranges]
    live=set(roots);pending=list(roots)
    while pending:
        n=pending.pop()
        for target in edges[n]-live:live.add(target);pending.append(target)
    digest=hashlib.sha256(b''.join(struct.pack('>II',a,n) for a,n in ranges)).hexdigest()
    return dict(ranges=ranges,containing=containing,live=live,report=dict(allocation_count=len(ranges),root_allocations=len(roots),live_allocations=len(live),ledger_sha256=digest,pointer_scan='All byte alignments; exact and interior pointers; all active tag allocations, original metadata and unmapped staging bytes are roots'))


def prune_unused_shader_bitmaps(importer):
    r,b=importer.registry,importer.builder
    c=r.cache
    tags={}
    for index in range(len(r.tags)//8):
        group,salt,address=struct.unpack_from('>HHI',r.tags,index*8)
        if group!=65535 and address:
            tags[(salt<<16)|index]=(c.groups[group],address)
    candidates={}
    for row in importer.added:
        if row.get('group')!='bitm' or row.get('native_shader_donor') is not True:continue
        datum=int(row['datum'],16) if isinstance(row['datum'],str) else row['datum']
        if (datum & 65535) < r.first_tag or tags.get(datum,(None,))[0]!='bitm':continue
        if not row.get('native_shader_donor_file'):continue
        candidates[datum]=row
    incoming={d:[] for d in candidates};opaque=[];schemas={}
    def word(address):
        offset=address-b.base
        if not 0<=offset<=len(b.meta)-4:raise ValueError('Shader pruning reference outside metadata')
        return struct.unpack_from('>I',b.meta,offset)[0]
    for owner,(group,address) in tags.items():
        # These are ownership/residency manifests, not semantic dependencies.
        if group in ('zone','play'):continue
        path=importer.reference/'plugins'/(group.strip()+'.xml')
        if not path.is_file():opaque.append(dict(owner=hex(owner),group=group));continue
        if group not in schemas:schemas[group]=ET.parse(path).getroot()
        visited=set()
        def walk(at,node,label):
            key=(at,id(node))
            if key in visited:return
            visited.add(key)
            for f in node:
                if 'offset' not in f.attrib:continue
                pos=at+int(f.get('offset'),0);kind=f.tag.lower();name=label+'/'+f.get('name','')
                if kind=='tagblock':
                    if not any(v.tag.lower() in ('tagref','datum') for v in f.iter()):continue
                    count,pointer=word(pos),word(pos+4);stride=int(f.get('elementSize'),0)
                    if count and (stride<=0 or count>1000000 or not b.base<=pointer<=pointer+count*stride<=b.base+len(b.meta)):
                        raise ValueError('Shader pruning reference block outside metadata')
                    for j in range(count):walk(pointer+j*stride,f,name)
                elif kind in ('tagref','datum'):
                    value=word(pos+(12 if kind=='tagref' and f.get('withGroup','true')!='false' else 0))
                    if value in incoming:incoming[value].append(dict(owner=hex(owner),field=name))
        walk(address,schemas[group],group)
    # Includes original and newly allocated metadata, unknown layouts, script
    # expressions, headers/globals staged in metadata, and unused allocations.
    # Incidental matches in live/unmapped ranges deliberately retain a donor.
    metadata=bytes(b.meta)
    reachability=_allocation_reachability(b,tags)
    matches={};dead=set()
    for datum in candidates:
        needle=struct.pack('>I',datum);offset=0;hits=[]
        while True:
            offset=metadata.find(needle,offset)
            if offset<0:break
            index=reachability['containing'](b.base+offset) if reachability else None
            live=index is None or index in reachability['live']
            if index is not None:
                at,size=reachability['ranges'][index]
                live=live or b.base+offset+4>at+size
            hit=dict(address=hex(b.base+offset),allocation=index,live_or_unmapped=live)
            if index is not None:
                at,size=reachability['ranges'][index]
                hit.update(allocation_start=hex(at),allocation_bytes=size,allocation_sha256=hashlib.sha256(metadata[at-b.base:at-b.base+size]).hexdigest())
            hits.append(hit);offset+=1
        matches[datum]=hits
        if not incoming[datum] and not any(x['live_or_unmapped'] for x in hits):dead.add(datum)
    retired=[];dead_resources=set();retired_tags=set()
    for datum in sorted(dead):
        resources=[]
        for ri in range(len(r.resources)//64):
            at=ri*64
            if struct.unpack_from('>I',r.resources,at+12)[0]!=datum:continue
            if ri<r.first_resource:raise ValueError('Imported donor owns original resource')
            li=struct.unpack_from('>h',r.resources,at+34)[0];pages=[]
            if li>=0:
                if (li+1)*16>len(r.locations):raise ValueError('Shader donor location outside table')
                for pi in struct.unpack_from('>hh',r.locations,li*16):
                    if pi<0:continue
                    if (pi+1)*88>len(r.pages):raise ValueError('Shader donor page outside table')
                    pa=pi*88
                    offset,compressed,raw=struct.unpack_from('>III',r.pages,pa+8)
                    pages.append(dict(index=pi,shared_index=struct.unpack_from('>h',r.pages,pa+4)[0],offset=offset,compressed_bytes=compressed,uncompressed_bytes=raw))
            resources.append(dict(index=ri,location=li,pages=pages))
        retired.append(dict(datum=hex(datum),index=datum&65535,source=candidates[datum]['source'],provenance=dict(candidates[datum]),donor=candidates[datum]['native_shader_donor_file'],resources=resources,semantic_incoming=0,staged_metadata_handle_occurrences=len(matches[datum]),unreachable_handle_allocations=matches[datum]))
    added_bytes_before=getattr(r,'added_bytes',0)
    ledger=getattr(r,'added_resource_bytes',{})
    retired_contributions={q['index']:ledger[q['index']] for row in retired for q in row['resources'] if q['index'] in ledger}
    decrement=sum(retired_contributions.values())
    if decrement>getattr(r,'added_bytes',0):raise ValueError('Shader donor raw accounting exceeds added bytes')
    # Apply only after every candidate/resource has passed validation. A shared
    # location row may belong to a live owner: detach the dead resource, never
    # mutate that shared location's page indices.
    for row in retired:
        index=row['index'];struct.pack_into('>HHI',r.tags,index*8,65535,65535,0);retired_tags.add(index)
        for resource in row['resources']:
            ri=resource['index'];struct.pack_into('>h',r.resources,ri*64+34,-1);dead_resources.add(ri)
    if retired_contributions:
        r.added_bytes-=decrement
        for ri in retired_contributions:del ledger[ri]
    importer.added[:]=[row for row in importer.added if (int(row['datum'],16) if isinstance(row.get('datum'),str) else row.get('datum')) not in dead]
    r.retired_tags=set(getattr(r,'retired_tags',set()))|retired_tags
    r.retired_resources=set(getattr(r,'retired_resources',set()))|dead_resources
    return dict(added_bytes_before=added_bytes_before,added_bytes_after=getattr(r,'added_bytes',0),allocation_proof=reachability['report'] if reachability else None,retired_added_raw_bytes=decrement,retired_raw_contributions={str(k):v for k,v in retired_contributions.items()},policy='New NativeShader donor bitmaps only; zero semantic incoming and every raw handle absent or confined to proven unreachable exact allocation ranges',candidates=len(candidates),retired_tags=len(retired_tags),retired_resources=len(dead_resources),retired=retired,opaque_layouts_conservatively_scanned=opaque,retained_candidates=[dict(datum=hex(d),semantic_incoming=len(incoming[d]),metadata_handle_present=bool(matches[d]),live_or_unmapped_handle_occurrences=sum(x['live_or_unmapped'] for x in matches[d])) for d in sorted(candidates.keys()-dead)])
