"""Conservative graph audit, not authorization to delete assets.

Reports potential unreachable owners under known schema semantics. Unknown
groups remain roots; residency catalogs are not treated as gameplay roots.
"""
import collections
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT/'tools/warlock-conversion/snapshot/reference/plugins'
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache


def audit(path, protect_unnamed=False):
    c = Cache(path)
    handles = {(t['salt']<<16)|i:i for i,t in c.tags.items()}
    schemas, graph, opaque = {}, {}, set()
    relevant = {}
    def has_references(schema):
        key = id(schema)
        if key not in relevant:
            relevant[key] = any(f.tag.lower() in ('tagref','datum') or
                               (f.tag.lower()=='tagblock' and has_references(f)) for f in schema)
        return relevant[key]
    errors = []
    for i,t in c.tags.items():
        group = t['group']
        graph[i] = set()
        if group in ('zone','play'):
            continue
        schema_path = SCHEMAS/(group.strip()+'.xml')
        if not schema_path.exists():
            opaque.add(i)
            continue
        if group not in schemas:
            schemas[group] = ET.parse(schema_path).getroot()
        visited = set()
        def record(at,schema):
            if not has_references(schema):
                return
            key = at,id(schema)
            if key in visited:
                return
            visited.add(key)
            for f in schema:
                if 'offset' not in f.attrib or f.get('name')=='Simulation Definition Table':
                    continue
                pos = at+int(f.get('offset'),0)
                kind = f.tag.lower()
                if kind=='tagblock':
                    if not has_references(f):
                        continue
                    count,pointer = c.unpack('II',pos)
                    if count:
                        stride = int(f.get('elementSize'),0)
                        start = c.pointer(pointer)
                        if stride<=0 or start<c.start or start+count*stride>c.start+c.u(0x490):
                            raise ValueError(f"Block {f.get('name')} at {pos:#x}: count={count}, pointer={pointer:#x}, stride={stride}; outside metadata")
                        for j in range(count):
                            record(start+j*stride,f)
                elif kind in ('tagref','datum'):
                    value = c.u(pos+(12 if kind=='tagref' and f.get('withGroup','true')!='false' else 0))
                    if value in handles:
                        graph[i].add(handles[value])
        try:
            record(t['offset'],schemas[group])
        except (ValueError,struct.error,AssertionError) as exc:
            opaque.add(i)
            errors.append(dict(tag=i,group=group,error=str(exc)))
    # Unsupported tags may contain references absent from their root allocation.
    # Retain every exact salted handle appearing anywhere in an opaque root's
    # conservative physical span. This is a planning approximation only.
    order = sorted((t['offset'],i) for i,t in c.tags.items())
    for n,(start,i) in enumerate(order):
        if i not in opaque:
            continue
        end = order[n+1][0] if n+1<len(order) else c.start+c.u(0x490)
        for off in range(start,end-3,4):
            value = c.u(off)
            if value in handles:
                graph[i].add(handles[value])
    index = c.pointer(c.u(16))
    globals_at = c.pointer(c.u(index+20))
    keep = set(opaque)
    if protect_unnamed:
        keep.update(i for i in c.tags if c.name(i) is None)
    keep.update(c.u(globals_at+j*8+4)&65535 for j in range(c.u(index+16)))
    pending = list(keep)
    while pending:
        i = pending.pop()
        for j in graph.get(i,set())-keep:
            keep.add(j);pending.append(j)
    dead = set(c.tags)-keep
    z = next(t['offset'] for t in c.tags.values() if t['group']=='zone')
    p = next(t['offset'] for t in c.tags.values() if t['group']=='play')
    locations,pages = c.block(p+48,16),c.block(p+24,88)
    live_pages,dead_pages = set(),set()
    for r in c.block(z+88,64):
        li = c.unpack('h',r+34)[0]
        if li<0:
            continue
        owner = handles.get(c.u(r+12))
        target = dead_pages if owner in dead else live_pages
        target.update(pi for pi in c.unpack('2h',locations[li]) if pi>=0)
    reclaim = {}
    for pi in dead_pages-live_pages:
        at = pages[pi]
        if c.unpack('h',at+4)[0]==-1:
            off,size = c.unpack('II',at+8)
            reclaim[(off,size)] = (size+4095)&~4095
    result = dict(map=path.name,tags=len(c.tags),reachable=len(keep),opaque_roots=len(opaque),protect_unnamed=protect_unnamed,
                  schema_errors=errors,potential_unused_tags=len(dead),
                  potential_unused_local_page_bytes=sum(reclaim.values()),
                  groups=dict(collections.Counter(c.tags[i]['group'] for i in dead)),
                  tags_for_review=[dict(index=i,group=c.tags[i]['group'],name=c.name(i)) for i in sorted(dead)],
                  scope='Planning graph only; native dynamic references, opaque allocations and residency require review before any removal.')
    c.close()
    return result


if __name__=='__main__':
    manifest=json.loads((ROOT/'.local/releases/current-live/manifest.json').read_text())
    reports=[]
    for bundle in manifest['packages']:
        for name in bundle['maps']:
            path=Path(bundle['installed_source'])/(name+'.map')
            if path.stat().st_size<=157286400:
                continue
            report=audit(path);reports.append(report)
            print(json.dumps({k:v for k,v in report.items() if k not in ('tags_for_review','schema_errors')}),flush=True)
            (ROOT/'work/elongation-console-diagnostic/unused-tag-audit.json').write_text(json.dumps(reports,indent=2)+'\n')
