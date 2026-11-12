"""Read authored Reach seam connectivity without flattening BSP identities.

H3 sub_820ABE50 consumes per-cluster seam indices and paired BSP/cluster
records in runtime seam mappings. The installer verifies collision edge numbering and serializes native records.
Native seam initialization still requires runtime validation.
"""
import itertools
import math

# Original H3 sub_821C66A0 compares squared centroid distance against the
# float at 0x820596EC. Equal identifiers alone do not establish connectivity.
NATIVE_SEAM_DISTANCE_SQUARED = 0.04000000283122063


def read_seams(cache,bsp):
    rows=[]
    for at in cache.block(bsp+0x40,40):
        refs=[cache.unpack('I3f',p) for p in cache.block(at+28,16)]
        if any(not all(math.isfinite(v) for v in ref[1:]) for ref in refs):
            raise ValueError('Invalid seam centroid')
        rows.append(dict(identifier=list(cache.unpack('4I',at)),
            edges=[cache.u(p) for p in cache.block(at+16,4)],
            clusters=[dict(index=r[0],center=list(r[1:])) for r in refs]))
    return rows


def paired_connections(bsps):
    if len({len(b) for b in bsps})!=1:
        raise ValueError('Seam ordinal coverage differs between BSPs')
    edges=set()
    for index in range(len(bsps[0])):
        occupied=[(bi,b[index]) for bi,b in enumerate(bsps) if b[index]['clusters']]
        if len(occupied)>2:raise ValueError('Native seam has more than two occupied BSPs')
        for (a,x),(b,y) in itertools.combinations(occupied,2):
            if x['identifier']!=y['identifier']:
                raise ValueError('Paired seam identifiers differ')
            if len(x['clusters'])!=1 or len(y['clusters'])!=1:
                raise ValueError('Multi-cluster seam pairing needs explicit centroid matching')
            px=x['clusters'][0];py=y['clusters'][0]
            if sum((a-b)**2 for a,b in zip(px['center'],py['center'])) >= NATIVE_SEAM_DISTANCE_SQUARED:
                raise ValueError('Paired seam centroids fail original H3 matching tolerance')
            ca=px['index'];cb=py['index']
            edges.update(((a,ca,b,cb),(b,cb,a,ca)))
    return sorted(edges)


def split_seam_clusters(bsps,bsp,parent,child,axis,plane):
    import copy
    out=copy.deepcopy(bsps);changes=[]
    for si,row in enumerate(out[bsp]):
        for ref in row['clusters']:
            if ref['index']!=parent:continue
            distance=ref['center'][axis]-plane
            if abs(distance)<1e-5:
                raise ValueError('Seam centroid lies on split; geometry review required')
            if distance>0:
                ref['index']=child
                changes.append(dict(seam=si,source_cluster=parent,target_cluster=child))
    return out,changes


def install_bsp_seams(registry,bsp_address,seams,source_geometry,native_collision):
    import struct
    b=registry.builder
    if any(b.read(bsp_address+12,12)):
        raise ValueError('BSP seam identifiers already installed')
    fixes=dict(native_collision['fixups'])
    geometry=fixes[native_collision['root']+4]&0x1fffffff
    # Both the collision converter and this consumer must agree on numbering.
    # Compare actual converted bytes, not just matching element counts.
    for name,offset,fmt in (('edges',72,'6H'),('vertices',84,'3I2H')):
        count,raw=source_geometry[name]
        expected=b''.join(struct.pack('>'+fmt,*row) for row in struct.iter_unpack('<'+fmt,raw))
        header=geometry+offset
        actual_count=struct.unpack_from('>I',native_collision['control'],header)[0]
        pointer=fixes.get(header+4,0)
        data=native_collision['control'] if pointer>>29==1 else native_collision['raw']
        start=pointer&0x1fffffff
        if actual_count!=count or data[start:start+len(expected)]!=expected:
            raise ValueError('Seam collision numbering/geometry changed: '+name)
    cluster_count,cluster_address,_=struct.unpack('>III',b.read(bsp_address+0xb4,12))
    incidence=[[] for _ in range(cluster_count)]
    if len(seams)>128:raise ValueError('Seam index exceeds original signed-byte range')
    def block(data,count):return struct.pack('>III',count,b.alloc(data) if data else 0,0)
    payload=bytearray()
    for si,row in enumerate(seams):
        if any(e!=0xffffffff and e>=source_geometry['edges'][0] for e in row['edges']):
            raise ValueError('Seam edge outside collision')
        refs=bytearray()
        for ref in row['clusters']:
            ci=ref['index']
            if not 0<=ci<cluster_count:raise ValueError('Seam cluster outside native BSP')
            incidence[ci].append(si)
            refs.extend(struct.pack('>I3f',ci,*ref['center']))
        payload.extend(struct.pack('>4I',*row['identifier']))
        payload.extend(block(b''.join(struct.pack('>I',e) for e in row['edges']),len(row['edges'])))
        payload.extend(block(refs,len(row['clusters'])))
    header=block(payload,len(seams));b.put(bsp_address+12,'III',*struct.unpack('>III',header))
    for ci,indices in enumerate(incidence):
        descriptor=block(bytes(indices),len(indices))
        b.put(cluster_address+ci*220+160,'III',*struct.unpack('>III',descriptor))
    count,address,_=struct.unpack('>III',b.read(bsp_address+12,12))
    if count!=len(seams) or b.read(address,len(payload))!=payload:
        raise ValueError('Native seam record readback failed')
    for ci,indices in enumerate(incidence):
        n,p,_=struct.unpack('>III',b.read(cluster_address+ci*220+160,12))
        if n!=len(indices) or (n and b.read(p,n)!=bytes(indices)):
            raise ValueError('Native cluster seam incidence readback failed')
    return dict(seam_count=len(seams),cluster_incidence=incidence,
        collision_edges_vertices_read_back=True,records_read_back=True,
        runtime_seam_initialization_verified=False)
