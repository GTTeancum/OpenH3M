"""Rebuild an oversized Gulch tree to original H3's signed plane-index limit."""
import hashlib,json,os,shutil,struct,subprocess
from pathlib import Path
from forge_visibility_partition import preserve_clusters
from forge_visibility_overlay import overlay

FORMATS=('Q','4f','BBHI','2H','3f2H','2H3h2B','6H','3fHh')
ARCHIVE_SHA='1862575ec3453aef2dcc9d5ae544db8e6d54fafce1a621e4554c1b58d02175f2'
DLL_SHA='0080eb49cc22dae4d0854c33db42863539b784776aea2124543fc90c96f68623'


def read_result(path):
    data=path.read_bytes();offset=4;result=[]
    if data[:4]!=b'FGC1':raise ValueError('Invalid collision rebuild result')
    for fmt in FORMATS:
        count=struct.unpack_from('<I',data,offset)[0];offset+=4
        size=count*struct.calcsize('<'+fmt)
        result.append(list(struct.iter_unpack('<'+fmt,data[offset:offset+size])));offset+=size
    if offset!=len(data):raise ValueError('Collision rebuild trailing data')
    return result


def write_result(path,arrays):
    with path.open('wb') as f:
        f.write(b'FGC1')
        for fmt,rows in zip(FORMATS,arrays):
            f.write(struct.pack('<I',len(rows)))
            for row in rows:f.write(struct.pack('<'+fmt,*row))


def compiler(repo,work):
    tool=work/'tools/tagtool';dll=tool/'TagTool.dll'
    if not dll.exists():
        import urllib.request
        archive=work/'tools/tagtool.7z';archive.parent.mkdir(parents=True,exist_ok=True)
        data=urllib.request.urlopen('https://github.com/TheGuardians/TagTool/releases/download/ce2dc6a/release_x64.7z',timeout=60).read()
        if hashlib.sha256(data).hexdigest()!=ARCHIVE_SHA:raise ValueError('Unverified TagTool archive')
        archive.write_bytes(data)
        seven=shutil.which('7z') or 'C:/Program Files/7-Zip/7z.exe'
        subprocess.run([seven,'x',str(archive),'-o'+str(tool),'TagTool.dll','Tools/Newtonsoft.Json.dll','-y'],cwd=repo,check=True,stdout=subprocess.DEVNULL,timeout=60)
        archive.unlink()
    if hashlib.sha256(dll.read_bytes()).hexdigest()!=DLL_SHA:raise ValueError('Unverified collision builder assembly')
    dotnet=shutil.which('dotnet') or 'C:/Program Files/dotnet/dotnet.exe'
    temporary=repo/'.local/build-temp';temporary.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,TEMP=str(temporary),TMP=str(temporary),DOTNET_CLI_HOME=str(repo/'.local/dotnet'),NUGET_PACKAGES=str(repo/'.local/nuget'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    source=Path(__file__).parent/'rebuild_collision';out=work/'tools/rebuild';binary=out/'Rebuild.dll'
    if not binary.exists() or any(p.stat().st_mtime>binary.stat().st_mtime for p in source.iterdir() if p.is_file()):
        with (work/'temp/compiler.log').open('w') as log:
            subprocess.run([dotnet,'build',str(source/'Rebuild.csproj'),'-o',str(out),'-p:BaseIntermediateOutputPath='+str(temporary/'rebuild')+os.sep,'--nologo'],cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    return dotnet,binary,tool,env


def rebuild(cache,tag,original,payloads,maps,report,required_planes):
    repo=Path(__file__).resolve().parents[4];work=repo/'work/forge-world';temp=work/'temp';temp.mkdir(parents=True,exist_ok=True)
    old=[list(struct.iter_unpack('>'+fmt,data)) for fmt,data in zip(FORMATS,payloads)]
    ids=sorted({row[0]&32767 for row in old[5]});plane_ids={v:i for i,v in enumerate(ids)}
    source_leaves=cache.block(tag['offset']+0x34,1);source_clusters=[cache.data[r] for r in source_leaves]
    input_path=temp/'collision.input'
    with input_path.open('wb') as f:
        f.write(b'FGC1');f.write(struct.pack('<I',len(ids)))
        for n in ids:f.write(struct.pack('<4f',*old[1][n]))
        f.write(struct.pack('<I',len(old[5])))
        for s in old[5]:f.write(struct.pack('<2H3h2B',plane_ids[s[0]&32767]|(s[0]&32768),*s[1:]))
        for j in (6,7):
            f.write(struct.pack('<I',len(old[j])))
            for row in old[j]:f.write(struct.pack('<'+FORMATS[j],*row))
    signature=hashlib.sha256(input_path.read_bytes()+bytes(source_clusters)+str(original[0]).encode()+str(original[1]).encode())
    for file in (Path(__file__),Path(__file__).with_name('forge_visibility_overlay.py'),Path(__file__).parent/'rebuild_collision/Program.cs'):
        signature.update(file.read_bytes())
    key=signature.hexdigest();result_path=temp/'collision-overlaid.output';cluster_path=temp/'collision-clusters.bin';manifest=work/'rebuild-cache.json'
    cached=json.loads(manifest.read_text()) if manifest.exists() else {}
    valid=(cached.get('key')==key and result_path.exists() and cluster_path.exists()
           and hashlib.sha256(result_path.read_bytes()).hexdigest()==cached.get('result_sha256')
           and hashlib.sha256(cluster_path.read_bytes()).hexdigest()==cached.get('clusters_sha256'))
    if not valid:
        dotnet,binary,tool,env=compiler(repo,work)
        with (temp/'collision-builder.log').open('w') as log:
            subprocess.run([dotnet,str(binary),str(tool),str(input_path),str(temp/'collision.output')],cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        arrays=read_result(temp/'collision.output')
        if arrays[6:]!=old[6:] or len(arrays[5])!=len(old[5]) or any(a[1:]!=b[1:] or bool(a[0]&32768)!=bool(b[0]&32768) or arrays[1][a[0]&32767]!=old[1][b[0]&32767] for a,b in zip(arrays[5],old[5])):
            raise ValueError('Collision rebuild changed retained polygons')
        _,_,children,_=preserve_clusters(original[0],[False]*len(original[0]),[False]*len(original[2]),source_clusters)
        coords=[r[:3] for r in original[7]];bounds=([min(p[k] for p in coords)-100 for k in range(3)],[max(p[k] for p in coords)+100 for k in range(3)])
        nodes=[[v[0]&65535,v[0]>>16&0xffffff,v[0]>>40&0xffffff] for v in arrays[0]]
        print('Rebuilding authored visibility cells within retail plane budget',flush=True)
        nodes,arrays[1],arrays[2],clusters,details=overlay(nodes,arrays[1],arrays[2],original[0],original[1],children,source_clusters,bounds)
        arrays[0]=[(p|(a<<16)|(b<<40),) for p,a,b in nodes]
        write_result(result_path,arrays);cluster_path.write_bytes(clusters)
        cached={'key':key,'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest(),'clusters_sha256':hashlib.sha256(clusters).hexdigest(),'overlay':details,'retained_polygons_verified':len(old[5])}
        manifest.write_text(json.dumps(cached,indent=2))
    arrays=read_result(result_path);clusters=cluster_path.read_bytes()
    # Portals retain their authored planes even if the new collision tree does
    # not use a particular portal plane as a spatial divider.
    indices={tuple(p):i for i,p in enumerate(arrays[1])};remapped={}
    for old_index in required_planes:
        plane=tuple(original[1][old_index])
        if plane not in indices:indices[plane]=len(arrays[1]);arrays[1].append(plane)
        remapped[old_index]=indices[plane]
    maps['planes']=remapped;maps['leaf_clusters']=clusters
    if len(arrays[1])>32768 or len(clusters)>65535 or len(arrays[0])>=0x3fffff or len(arrays[4])>=32767:
        raise ValueError('Rebuilt collision exceeds original H3 index budgets')
    if len(clusters)!=len(arrays[2]):raise ValueError('Rebuilt leaf/cluster counts differ')
    report.update(counts=dict(zip(('nodes3d','planes','leaves','references2d','nodes2d','surfaces','edges','vertices'),map(len,arrays))),rebuild=cached,plane_index_limit=32768,original_leaf_cluster_assignments_preserved='Spatial overlay; original leaf indices replaced')
    packed=[b''.join(struct.pack('>'+fmt,*r) for r in rows) for fmt,rows in zip(FORMATS,arrays)]
    report['raw_bytes']=sum(map(len,packed));input_path.unlink(missing_ok=True)
    return packed,maps,report
