"""Stage exact authored polygon geometry without narrowing the source BSP tree.

The existing full rebuild creates new native trees and overlays source visibility.
No source-tree index or plane limit is relaxed by this geometry-only intermediate.
"""
import struct
import numpy as np
from forge_collision_mesh import surface_loops
from rebuild_forge_collision import FORMATS


def stage_geometry(source, keep):
    if len(keep) != len(source[5]) or not any(keep):
        raise ValueError('Invalid/empty surface selection')
    loops = surface_loops(source)
    selected={'surfaces':list(map(int,np.flatnonzero(keep)))}
    selected['edges']=[n for n,e in enumerate(source[6]) if (e[4]>=0 and keep[e[4]]) or (e[5]>=0 and keep[e[5]])]
    selected['vertices']=sorted({v for n in selected['edges'] for v in source[6][n][:2]})
    maps={name:{old:new for new,old in enumerate(order)} for name,order in selected.items()}
    maps.update(nodes={},leaves={},nodes2={})
    target=[[] for _ in FORMATS];unique={};pm={}
    for old in sorted({source[5][n][0]&0x7fffffff for n in selected['surfaces']}):
        p=source[1][old];key=struct.pack('<4f',*p)
        if key not in unique:unique[key]=len(target[1]);target[1].append(p)
        pm[old]=unique[key]
    maps['planes']=pm
    if len(target[1])>32768 or len(selected['surfaces'])>=32767 or len(selected['edges'])>=65535 or len(selected['vertices'])>=65535:
        raise ValueError('Retained polygon geometry exceeds native format')
    for n in selected['surfaces']:
        p,e,mat,bs,bi,flags,best=source[5][n]
        if flags&128:raise ValueError('Ambiguous source orientation')
        target[5].append((pm[p&0x7fffffff]|(32768 if p<0 else 0),maps['edges'][e],mat,bs,bi,flags,best&255))
    incident={}
    for n in selected['edges']:
        start,end,forward,reverse,left,right=source[6][n]
        for v in (start,end):incident.setdefault(v,maps['edges'][n])
        target[6].append((maps['vertices'][start],maps['vertices'][end],
            maps['edges'][forward] if left in maps['surfaces'] else 65535,
            maps['edges'][reverse] if right in maps['surfaces'] else 65535,
            maps['surfaces'].get(left,65535),maps['surfaces'].get(right,65535)))
    for n in selected['vertices']:
        x,y,z,e,sink=source[7][n]
        target[7].append((x,y,z,maps['edges'].get(e,incident[n]),sink))
    payloads=[b''.join(struct.pack('>'+fmt,*r) for r in rows) for fmt,rows in zip(FORMATS,target)]
    decoded=[list(struct.iter_unpack('>'+fmt,p)) for fmt,p in zip(FORMATS,payloads)]
    verify_polygons(source, decoded, maps, loops)
    return payloads, maps, {
        'status': 'Offline collision tables; NOT a complete map',
        'tree_staging': 'Only exact selected polygon geometry encoded before mandatory rebuild',
        'surface_loops_roundtrip_verified': len(selected['surfaces']),
    }


def verify_polygons(source, target, maps, loops=None):
    loops = surface_loops(source) if loops is None else loops
    for old, new in maps['surfaces'].items():
        src, dst = source[5][old], target[5][new]
        if (target[1][dst[0]&32767] != source[1][src[0]&0x7fffffff]
                or bool(dst[0]&32768) != (src[0]<0)
                or dst[2:6] != src[2:6] or dst[6] != src[6]&255):
            raise ValueError('Serialized polygon material/orientation changed')
        first = edge = dst[1]
        seen, points = set(), []
        while edge not in seen:
            if not 0 <= edge < len(target[6]):
                raise ValueError('Serialized polygon has dangling edge')
            seen.add(edge)
            row = target[6][edge]
            if row[4] == new:
                vertex, edge = row[0], row[2]
            elif row[5] == new:
                vertex, edge = row[1], row[3]
            else:
                raise ValueError('Serialized polygon edge ownership changed')
            if not 0 <= vertex < len(target[7]):
                raise ValueError('Serialized polygon has dangling vertex')
            points.append(target[7][vertex][:3])
        if edge != first or points != [source[7][v][:3] for v in loops[old]]:
            raise ValueError('Serialized polygon vertex cycle changed')
