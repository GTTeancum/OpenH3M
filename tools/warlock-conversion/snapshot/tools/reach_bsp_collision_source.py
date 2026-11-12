"""Bounded Reach MCC BSP collision resource reader; no physics is discarded.

Layouts follow pinned TagTool StructureBspTagResources, CollisionGeometry and
InstancedGeometryBlock. Supernodes and Reach physics still require conversion.
"""
class ReachBspCollisionSource:
    geometry_arrays = (('nodes',8),('supernodes',128),('planes',16),('leaves',8),
                       ('references',4),('nodes2d',16),('surfaces',12),('edges',12),('vertices',16))

    def __init__(self,resource):
        self.resource=resource

    def read(self,pointer,size):
        r=self.resource
        segment,offset=pointer>>29,pointer&0x1fffffff
        if segment==1:data=r.data
        elif segment in (2,3) and segment-2<len(r.raw):data=r.raw[segment-2]
        else:raise ValueError('Unknown Reach collision segment')
        if size<0 or offset+size>len(data):raise ValueError('Reach collision array outside segment')
        return memoryview(data)[offset:offset+size]

    def block(self,at,stride):
        r=self.resource
        if not 0<=at<=len(r.data)-12:raise ValueError('Reach collision header outside control')
        count=r.unpack('I',at)[0]
        if not count:return count,memoryview(b'')
        if at+4 not in r.fix:raise ValueError('Missing Reach collision pointer fixup')
        return count,self.read(r.fix[at+4],count*stride)

    def headers(self,at,stride):
        count,_=self.block(at,stride)
        if not count:return []
        pointer=self.resource.fix[at+4]
        if pointer>>29!=1:raise ValueError('Reach collision headers must be resident')
        start=pointer&0x1fffffff
        return [start+j*stride for j in range(count)]

    def geometry(self,at):
        return {name:self.block(at+j*12,stride) for j,(name,stride) in enumerate(self.geometry_arrays)}

    def inventory(self):
        r=self.resource
        rows=[]
        for index,at in enumerate(self.headers(r.root,108)):
            rows.append(dict(kind='bsp',index=index,counts={k:v[0] for k,v in self.geometry(at).items()}))
        large_count=r.unpack('I',r.root+12)[0]
        for index,at in enumerate(self.headers(r.root+24,324)):
            geometry=self.geometry(at+8)
            unused=self.geometry(at+116)
            extensions={name:self.block(at+offset,stride)[0] for name,offset,stride in
                (('render_bsp',224,108),('mopp',236,96),('breakable',248,4),
                 ('polyhedra',260,160),('polyhedron_vectors',272,48),('polyhedron_planes',284,16),
                 ('surface_planes',296,8),('surface_triangles',308,4))}
            rows.append(dict(kind='instance',index=index,flags=r.unpack('I',at+4)[0],
                counts={k:v[0] for k,v in geometry.items()},unused_counts={k:v[0] for k,v in unused.items()},
                extensions=extensions,mesh=r.unpack('h',at+320)[0]))
        return dict(large_bsps=large_count,geometries=rows,
            width_excess=[dict(kind=x['kind'],index=x['index'],counts=x['counts']) for x in rows
                if any(x['counts'][k]>limit for k,limit in
                       (('planes',32768),('surfaces',32768),('edges',65535),('vertices',65535),('nodes2d',32768)))])
