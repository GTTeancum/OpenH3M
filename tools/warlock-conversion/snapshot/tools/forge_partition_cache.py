"""Source-fingerprinted per-side caches for serial offline Forge tree rebuilds."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
from rebuild_forge_collision import FORMATS, rebuild
from forge_collision_staging import verify_polygons

FILES=('collision-overlaid.output','collision-clusters.bin','rebuild-cache.json')

def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file,'sha256').hexdigest()


def fingerprint(cache, side):
    if side not in ('gulch','island'):
        raise ValueError('Unknown Forge partition')
    folder=Path(__file__).parent
    return {'source_sha256':hashlib.sha256(cache.data).hexdigest(), 'side':side,
        'preparation_sources':{name:digest(folder/name) for name in (
            'partition_forge_collision.py','forge_collision_staging.py',
            'forge_gulch_boundary.py','forge_gulch_hard_boundary.py')}}


def restore(folder, work, identity):
    manifest=folder/'partition-cache.json'
    if not manifest.exists():return False
    record=json.loads(manifest.read_text())
    if record.get('identity')!=identity:return False
    hashes=record.get('files',{})
    if set(hashes)!=set(FILES) or any(not (folder/name).is_file() or digest(folder/name)!=hashes[name] for name in FILES):
        return False
    # Validate the builder's own content-addressed artifact pair as well.
    inner=json.loads((folder/'rebuild-cache.json').read_text())
    if inner.get('result_sha256')!=hashes['collision-overlaid.output'] or inner.get('clusters_sha256')!=hashes['collision-clusters.bin']:
        return False
    for name in FILES:
        dest=work/name if name=='rebuild-cache.json' else work/'temp'/name
        shutil.copyfile(folder/name,dest)
    return True


def save(folder, work, identity):
    folder.mkdir(parents=True,exist_ok=True)
    for name in FILES:
        src=work/name if name=='rebuild-cache.json' else work/'temp'/name
        shutil.copyfile(src,folder/name)
    record={'identity':identity,'files':{name:digest(folder/name) for name in FILES}}
    path=folder/'partition-cache.json'
    temporary=folder/'partition-cache.json.tmp'
    temporary.write_text(json.dumps(record,indent=2)+'\n')
    temporary.replace(path)


def validate_native(arrays, clusters):
    nodes,planes,leaves,refs,nodes2,surfaces,edges,vertices=arrays
    if (len(planes)>32768 or len(leaves)>65535 or len(nodes)>=0x3fffff
            or len(nodes2)>=32767 or len(surfaces)>=32767
            or len(edges)>=65535 or len(vertices)>=65535):
        raise ValueError('Rebuilt collision exceeds original H3 index budgets')
    if len(clusters)!=len(leaves) or 255 in clusters:
        raise ValueError('Invalid rebuilt leaf-cluster assignments')
    def graph(rows, children, mask, empty, terminals):
        states=[0]*len(rows)
        for start in range(len(rows)):
            pending=[(start,False)]
            while pending:
                n,leaving=pending.pop()
                if leaving:states[n]=2;continue
                if states[n]==2:continue
                if states[n]:raise ValueError('Cyclic rebuilt collision tree')
                states[n]=1;pending.append((n,True))
                for ch in children(rows[n]):
                    if ch==empty:continue
                    if ch&mask:
                        if ch&(mask-1)>=terminals:raise ValueError('Rebuilt terminal outside table')
                    else:
                        if ch>=len(rows):raise ValueError('Rebuilt child outside table')
                        pending.append((ch,False))
    graph(nodes,lambda r:((r[0]>>16)&0xffffff,r[0]>>40),0x800000,0xffffff,len(leaves))
    graph(nodes2,lambda r:r[3:],0x8000,0xffff,len(surfaces))
    if any((r[0]&65535)>=len(planes) for r in nodes):raise ValueError('Rebuilt node plane outside table')
    for _,_,count,first in leaves:
        if count and first+count>len(refs):raise ValueError('Rebuilt leaf range outside table')
    for plane,child in refs:
        if plane&32767>=len(planes):raise ValueError('Rebuilt reference plane outside table')
        if child!=65535 and (child&32767>=len(surfaces) if child&32768 else child>=len(nodes2)):
            raise ValueError('Rebuilt reference child outside table')


def rebuild_cached(cache,tag,original,payloads,maps,report,portals,side):
    repo=Path(__file__).resolve().parents[4]
    work=repo/'work/forge-world';folder=work/(side+'-prepared')
    (work/'temp').mkdir(parents=True,exist_ok=True)
    lock=work/'partition-build.lock'
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError('Forge partition rebuild already active; serialize compiler/cache use') from error
    try:
        os.close(fd)
        identity=fingerprint(cache,side)
        restored=restore(folder,work,identity)
        payloads,maps,report=rebuild(cache,tag,original,payloads,maps,report,portals)
        arrays=[list(struct.iter_unpack('>'+fmt,p)) for fmt,p in zip(FORMATS,payloads)]
        validate_native(arrays,maps['leaf_clusters'])
        verify_polygons(original,arrays,maps)
        save(folder,work,identity)
        report['per_side_cache']={'source_sha256':identity['source_sha256'],'side':side,'verified_cache_restored':restored}
        report['final_native_tables_validated']=True
        return payloads,maps,report
    finally:
        lock.unlink()
