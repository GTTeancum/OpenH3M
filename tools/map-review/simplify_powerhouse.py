"""Conservative opaque rigid-mesh reduction; original vertices/collision retained."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build', action='store_true')
p.add_argument('--error', type=float, default=.002)
p.add_argument('--ratio', type=float, default=.8)
p.add_argument('--overdraw-only', action='store_true', help='Retain every triangle; reorder opaque subparts to reduce hidden-pixel shading')
p.add_argument('--report', type=Path, help='Repository-local report destination')
p.add_argument('--replace-candidate', action='store_true', help='Replace only the prior generated candidate whose recorded hash matches')
a = p.parse_args()
assert 0 < a.error <= .01 and .5 <= a.ratio < 1
source = ROOT/'work/map-review-20261105/powerhouse-cache-order.map'
c = Cache(source)
sc = next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
lm = c.tags[c.u(sc+0x6fc)&65535]['offset']; lb = c.block(lm+4,436)[0]
datum = c.u(lb+0x1ac); r = Resource(c,datum)
bsp = next(t['offset'] for t in c.tags.values() if t['group']=='sbsp')
cr = Resource(c,c.u(bsp+0x37c)); definitions = cr.ptr(cr.root+16)
compression_by_mesh = {}
for i in range(cr.unpack('I',cr.root+12)[0]):
    mesh, comp = cr.unpack('2H',definitions+i*184+0xb0)
    assert mesh not in compression_by_mesh or compression_by_mesh[mesh]==comp
    compression_by_mesh[mesh]=comp
compressions=c.block(bsp+0x2f0,44)
meshes=c.block(bsp+0x2e4,76); light_meshes=c.block(lb+0x134,76)
assert len(meshes)==len(light_meshes)
vb,ib=r.buffers('vertex'),r.buffers('index')
lib=C.CDLL(str(ROOT/'.local/map-review-deps/meshoptimizer-build/Release/meshoptimizer.dll'))
U=C.POINTER(C.c_uint); F=C.POINTER(C.c_float)
lib.meshopt_simplifyWithAttributes.argtypes=[U,U,C.c_size_t,F,C.c_size_t,C.c_size_t,F,C.c_size_t,F,C.c_size_t,C.c_void_p,C.c_size_t,C.c_float,C.c_uint,F]
lib.meshopt_simplifyWithAttributes.restype=C.c_size_t
lib.meshopt_optimizeVertexCache.argtypes=[U,U,C.c_size_t,C.c_size_t]
lib.meshopt_optimizeOverdraw.argtypes=[U,U,C.c_size_t,F,C.c_size_t,C.c_size_t,C.c_float]
weights=(C.c_float*5)(.5,.5,.5,10,10)
patched={}; writes={}; rows=[]; seen=set(); total=0
def payload(at):
    ptr=r.fix[at]; return {0x40000000:0,0x60000000:1}[ptr&0xe0000000],ptr&0x1fffffff
def record(at,fmt,values):
    data=struct.pack('>'+fmt,*values)
    assert at not in writes or writes[at]==data
    writes[at]=data
for mi,(m,lm) in enumerate(zip(meshes,light_meshes)):
    parts=c.block(m,16); total+=sum(c.unpack('H',p+6)[0]//3 for p in parts)
    vi,ii=c.unpack('h',m+24)[0],c.unpack('h',m+40)[0]
    if vi<0 or ii<0 or mi not in compression_by_mesh: continue
    n,fmt,stride=r.unpack('IHH',vb[vi])
    if (fmt,stride)!=(2,24): continue
    assert c.unpack('B',m+0x30)[0]==3
    seg,offset=payload(vb[vi]+20); raw=r.raw[seg]
    bounds=np.array(c.unpack('6f',compressions[compression_by_mesh[mi]]+4)).reshape(3,2)
    xyz=np.ascontiguousarray(np.ndarray((n,3),'>u2',raw,offset,(stride,2))/65535*(bounds[:,1]-bounds[:,0])+bounds[:,0],dtype=np.float32)
    packed=np.ndarray((n,),'>u4',raw,offset+12,(stride,)).astype(np.uint32)
    normals=[]
    for shift,bits in ((0,10),(10,11),(21,11)):
        val=((packed>>shift)&((1<<bits)-1)).astype(np.int32)
        val=np.where(val&(1<<(bits-1)),val-(1<<bits),val)
        normals.append(np.maximum(-1,val/((1<<(bits-1))-1)))
    uv=np.ndarray((n,2),'>u2',raw,offset+8,(stride,2))/65535
    attrs=np.ascontiguousarray(np.column_stack((*normals,uv)),dtype=np.float32)
    iseg,ioff=payload(ib[ii]+16); length=r.unpack('I',ib[ii]+4)[0]
    indices=np.frombuffer(r.raw[iseg],'>u2',length//2,ioff)
    lparts=c.block(lm,16); subs=c.block(m+12,8); lsubs=c.block(lm+12,8)
    assert len(parts)==len(lparts) and len(subs)==len(lsubs)
    for pi,part in enumerate(parts):
        start,count,first,num=c.unpack('4H',part+4)
        if c.unpack('B',part+12)[0] not in (1,2,3) or count<30:continue
        assert c.unpack('4H',lparts[pi]+4)==(start,count,first,num)
        key=(ii,start,count)
        assert key not in seen, 'Shared index ranges require explicit handling'
        seen.add(key); new=[]; changes=[]; before=0; worst=0
        for si in range(first,first+num):
            old_start,size=c.unpack('2H',subs[si]); assert old_start==start+before and size%3==0
            assert c.unpack('2H',lsubs[si])==(old_start,size)
            if not size:
                changes.append((si,start+len(new),0));continue
            src=np.ascontiguousarray(indices[old_start:old_start+size],dtype=np.uint32)
            assert max(src,default=0)<n
            dest=np.empty_like(src); error=C.c_float()
            if a.overdraw_only:
                lib.meshopt_optimizeOverdraw(dest.ctypes.data_as(U),src.ctypes.data_as(U),size,
                    xyz.ctypes.data_as(F),n,12,1.05)
                import collections
                assert collections.Counter(map(tuple,src.reshape(-1,3)))==collections.Counter(map(tuple,dest.reshape(-1,3)))
                kept=size
            else:
                kept=lib.meshopt_simplifyWithAttributes(dest.ctypes.data_as(U),src.ctypes.data_as(U),size,
                    xyz.ctypes.data_as(F),n,12,attrs.ctypes.data_as(F),20,weights,5,None,
                    int(size*a.ratio)//3*3,a.error,1,C.byref(error))
            if kept==0:
                kept=size;dest[:]=src;error.value=0
            assert 0<kept<=size and kept%3==0, (mi,pi,si,size,kept)
            cache=np.empty(kept,dtype=np.uint32)
            if a.overdraw_only:cache[:]=dest[:kept]
            else:lib.meshopt_optimizeVertexCache(cache.ctypes.data_as(U),dest.ctypes.data_as(U),kept,n)
            changes.append((si,start+len(new),kept));new.extend(cache.tolist());before+=size;worst=max(worst,error.value)
        assert before==count
        if len(new)==count and (not a.overdraw_only or np.array_equal(new,indices[start:start+count])):continue
        data=patched.setdefault(iseg,bytearray(r.raw[iseg]))
        # Keep allocation/range start stable; unused tail is never drawn.
        data[ioff+start*2:ioff+(start+count)*2]=np.array(new+[0]*(count-len(new)),dtype='>u2').tobytes()
        for at in (part,lparts[pi]):record(at+6,'H',(len(new),))
        for si,new_start,kept in changes:
            for at in (subs[si],lsubs[si]):record(at,'2H',(new_start,kept))
        rows.append(dict(mesh=mi,part=pi,before=count//3,after=len(new)//3,max_relative_error=worst))
removed=sum(x['before']-x['after'] for x in rows)
report=dict(source=str(source),triangles_before=total,triangles_after=total-removed,reduction_percent=removed/total*100,
    target_ratio=a.ratio,error_limit=a.error,changed_parts=len(rows),rows=rows,
    preserved='Original vertex/UV/normal/lightmap payloads, material boundaries (locked borders), collision, transparent/water parts, instance transforms, lights and camera settings',
    scope='Private candidate; simplification changes interpolation. Requires native visual and performance review.')
out=ROOT/'work/map-review-20261105'/('powerhouse-overdraw.map' if a.overdraw_only else 'powerhouse-simplified.map')
if a.overdraw_only:
    report.update(mode='Topology-preserving overdraw ordering',preserved='All triangle tuples/winding, all vertex/lighting data, collision, transparent/water ordering and settings',scope='Private candidate; runtime performance and appearance unverified')
if a.build:
    if out.exists():
        assert a.replace_candidate
        previous=ROOT/'work/map-review-20261105'/('powerhouse-overdraw.json' if a.overdraw_only else 'powerhouse-simplification.json')
        assert hashlib.sha256(out.read_bytes()).hexdigest()==json.loads(previous.read_text())['sha256'], 'Unrecognized candidate; refusing overwrite'
    b=MapBuilder(source,0);salt=resource_salt(ROOT/'../../default.xex')
    for at,data in writes.items():b.put(at-c.start+c.base,str(len(data))+'s',data)
    zone=next(t['offset'] for t in c.tags.values() if t['group']=='zone');play=next(t['offset'] for t in c.tags.values() if t['group']=='play')
    resource=c.block(zone+88,64)[datum&65535];location=c.block(play+48,16)[c.unpack('h',resource+34)[0]]
    pages=c.block(play+24,88);page_ids=c.unpack('2h',location);offsets=c.unpack('2I',location+4)
    for segment,data in patched.items():
        assert offsets[segment]==0
        page=pages[page_ids[segment]];assert c.unpack('h',page+4)[0]==-1 and c.u(page+16)==len(data)
        compressed=zlib.compress(data)[2:-4];new_offset=b.append_raw(compressed);address=page-c.start+c.base
        b.put(address+3,'B',0);b.put(address+8,'4I',new_offset,len(compressed),len(data),zlib.crc32(data)^0xffffffff)
        hashes=b''.join(hashlib.sha1(salt+x).digest() for x in (data,data[:1024],data[-1024:]))
        b.put(address+24,str(len(hashes))+'s',hashes)
    out.write_bytes(b.finish(salt));b.close()
    check=Cache(out);rr=Resource(check,datum)
    assert rr.data==r.data and rr.fix==r.fix
    for segment,original in enumerate(r.raw):assert rr.raw[segment]==patched.get(segment,original)
    for at,data in writes.items():
        new_at=at-c.start+check.start;assert check.data[new_at:new_at+len(data)]==data
    check.close();report.update(candidate=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest())
report_path=a.report.resolve() if a.report else ROOT/'work/map-review-20261105'/('powerhouse-overdraw.json' if a.overdraw_only else 'powerhouse-simplification.json')
assert report_path.is_relative_to(ROOT)
report_path.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));c.close()
