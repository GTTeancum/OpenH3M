"""Assemble native clusters/portals using explicit post-split bindings.

Environment indices and cubemap indices are remapped by the caller. The native
version-2 collision path uses mesh buckets; empty cluster physics matches the
original armory.map record, not Reach's incompatible group-key MOPPs.
"""
import math
import struct
from reach_cluster_cubemaps import convert_cluster_cubemaps


def install_unsplit_clusters(cache, bsp, root, environment, cubemap_remap, allocate):
    """Use the authored graph directly for BSPs needing no spatial partition.

    Decorated BSPs use the explicit group/resource path instead; this helper
    rejects them so an absent payload cannot silently remove foliage.
    """
    clusters = cache.block(bsp+0x138, 140)
    if any(cache.u(at+80) for at in clusters):
        raise ValueError('Decorated clusters require explicit converted groups')
    portals = []
    for at in cache.block(bsp+0x120, 80):
        back, front, plane = cache.unpack('hhi', at+40)
        portals.append(dict(back=back, front=front, plane=plane,
            centroid=list(cache.unpack('3f', at+48)), radius=cache.unpack('f', at+60)[0],
            flags=cache.u(at+64), vertices=[list(cache.unpack('3f',p)) for p in cache.block(at+68,12)]))
    incidence = [[cache.unpack('h',p)[0] for p in cache.block(at+52,2)] for at in clusters]
    destinations = [dict(source=i,mesh=cache.unpack('h',at+64)[0],bounds=list(cache.unpack('6f',at)))
                    for i,at in enumerate(clusters)]
    return install_clusters(cache,bsp,root,destinations,portals,incidence,
                            [b'']*len(clusters),environment,cubemap_remap,allocate)


def install_decorator_geometry(cache,bsp,root,registry,owner,source_resource):
    """Install buffer-only decorator geometry; palette tags are caller-owned."""
    from render_resource import convert_render_resource
    source=bsp+0x280
    if len(root)!=0x388 or any(root[0x1c8:0x24c]):
        raise ValueError('Decorator geometry already populated or invalid root')
    if cache.u(source)&~7 or any(any(cache.data[source+o:source+o+12]) for o in range(4,148,12)):
        raise ValueError('Decorator geometry has unsupported metadata tables')
    native=convert_render_resource(source_resource)
    datum=registry.add_resource(owner,'render_geometry_api_resource_definition',native)
    struct.pack_into('>I',root,0x1c8,cache.u(source))
    struct.pack_into('>II',root,0x244,datum,0)
    return dict(resource_datum=datum,raw_bytes=len(native['raw']),
                palette_installed=False,runtime_verified=False)


def install_clusters(cache,bsp,root,destinations,portals,incidence,decorators,
                     environment,cubemap_remap,allocate):
    if len(root)!=0x388 or struct.unpack_from('>I',root,4)[0]!=2:
        raise ValueError('Expected native version-2 BSP')
    if any(root[0x6c:0x78]) or any(root[0xb4:0xc0]):
        raise ValueError('Native cluster/portal arrays already populated')
    source=cache.block(bsp+0x138,140)
    if len(destinations)!=len(incidence) or len(destinations)!=len(decorators):
        raise ValueError('Destination cluster dependencies disagree')
    if {d['source'] for d in destinations}!=set(range(len(source))):
        raise ValueError('Cluster assembly drops source clusters')
    def block(data,stride):
        if len(data)%stride:raise ValueError('Misaligned cluster data')
        return struct.pack('>III',len(data)//stride,allocate(data) if data else 0,0)
    portal_data=bytearray()
    expected=[set() for _ in destinations]
    for i,p in enumerate(portals):
        if not all(0<=p[k]<len(destinations) for k in ('back','front')):
            raise ValueError('Portal has invalid adjacent cluster')
        for key in ('back','front'):expected[p[key]].add(i)
        vertices=b''.join(struct.pack('>3f',*v) for v in p['vertices'])
        portal_data.extend(struct.pack('>hhi4fI',p['back'],p['front'],p['plane'],
            *p['centroid'],p['radius'],p['flags'])+block(vertices,12))
    output=bytearray()
    for index,d in enumerate(destinations):
        at=source[d['source']]
        if any(cache.data[at+38:at+52]) or any(cache.u(at+o) for o in (92,104,116)):
            raise ValueError('Cluster needs cheap-light/PVS/predicted-resource adaptation')
        if set(incidence[index])!=expected[index] or len(set(incidence[index]))!=len(incidence[index]):
            raise ValueError('Cluster portal incidence does not match portal graph')
        bounds=d.get('bounds',cache.unpack('6f',at))
        if any(not math.isfinite(x) for x in bounds) or any(bounds[i]>bounds[i+1] for i in (0,2,4)):
            raise ValueError('Invalid native cluster bounds')
        row=bytearray(220)
        struct.pack_into('>6f',row,0,*bounds)
        struct.pack_into('>4b2h',row,24,*environment(d['source'],cache.unpack('4b2h',at+24)))
        # H3-only background sound/weather slots: native absence/default values.
        struct.pack_into('>5h',row,32,-1,-1,-1,0,0)
        flags=cache.unpack('H',at+36)[0]
        if flags&~31:raise ValueError('Unknown cluster flags')
        struct.pack_into('>2hH',row,42,*cache.unpack('2h',at+32),flags)
        row[60:72]=block(b''.join(struct.pack('>h',p) for p in incidence[index]),2)
        struct.pack_into('>HHI',row,76,0,128,0)
        struct.pack_into('>I',row,84,2)
        struct.pack_into('>4sIII',row,96,b'sbsp',0,0,0xffffffff)
        struct.pack_into('>h',row,156,d['mesh'])
        row[160:172]=block(bytes(cache.data[p] for p in cache.block(at+68,1)),1)
        row[172:184]=block(decorators[index],48)
        cubes,_=convert_cluster_cubemaps(cache,at,cubemap_remap)
        row[208:220]=block(cubes,16)
        output.extend(row)
    root[0x6c:0x78]=block(portal_data,40)
    root[0xb4:0xc0]=block(output,220)
    return dict(clusters=len(destinations),portals=len(portals),
                decorator_groups=sum(len(p)//48 for p in decorators),
                native_cluster_arrays_installed=True,runtime_verified=False)
