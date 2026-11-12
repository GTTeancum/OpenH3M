"""Rebuild only large-cache 2D references, preserving authored 3D/visibility."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from cache_reader import Cache
from forge_collision_mesh import read_mesh
from rebuild_forge_collision import compiler, read_result, FORMATS
from rebuild_whole_collision import ROOT


def prepare(cache, work, scenario):
    work = work.resolve()
    if not work.is_relative_to(ROOT):
        raise ValueError('Output outside repository')
    report = json.loads((work/'references-rebuild.json').read_text())
    out = work/'references.output'
    if (report['status'] != 'accepted' or report['source_sha256'] != hashlib.sha256(cache.data).hexdigest()
            or report['output_sha256'] != hashlib.sha256(out.read_bytes()).hexdigest()):
        raise ValueError('Missing or mismatched 2D rebuild proof')
    tag, original = read_mesh(cache, scenario)
    result = read_result(out)
    def child(n):
        if n == -1:
            return 0xffffff
        index = n & 0x7fffffff
        if index >= 0x7fffff:
            raise ValueError('3D index overflow')
        return index | (0x800000 if n < 0 else 0)
    result[0] = [(p | child(back)<<16 | child(front)<<40,) for p,back,front in original[0]]
    result[2] = original[2]
    if result[1] != original[1] or len(result[3]) != len(original[3]):
        raise ValueError('2D rebuild changed original planes/reference count')
    if any(p<0 or p>=32768 for p,_,_ in original[0]):
        raise ValueError('3D plane overflow')
    if len(result[4]) >= 32767 or len(result[2]) > 65535:
        raise ValueError('Collision index limits exceeded')
    clusters = bytes(cache.data[r] for r in cache.block(tag['offset']+0x34,1))
    if len(clusters) != len(original[2]):
        raise ValueError('Authored leaf/cluster counts disagree')
    maps = dict(leaves={n:n for n in range(len(original[2]))}, leaf_clusters=clusters,
                planes={n:n for n in range(len(original[1]))},
                edges={n:n for n in range(len(original[6]))},
                surfaces={n:n for n in range(len(original[5]))}, preserve_surface_indices=True)
    packed = [b''.join(struct.pack('>'+fmt,*r) for r in rows) for fmt,rows in zip(FORMATS,result)]
    return packed, maps, report


def reachable(nodes, root, large=True):
    stack, seen, leaves = [root], set(), set()
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n == (-1 if large else 65535):
            continue
        if (n < 0 if large else n & 32768):
            leaves.add(n & (0x7fffffff if large else 32767))
        else:
            stack.extend(nodes[n][3:])
    return sorted(leaves)


def build(source, scenario, work):
    work = work.resolve()
    if not work.is_relative_to(ROOT):
        raise ValueError('Output outside repository')
    work.mkdir(parents=True, exist_ok=True)
    c = Cache(source, True)
    try:
        _, a = read_mesh(c, scenario)
        def index(v):
            if v == -1:
                return 65535
            if not 0 <= v < 65535:
                raise ValueError('Topology exceeds native limits')
            return v
        def plane(v):
            p = v & 0x7fffffff
            if p >= 32768:
                raise ValueError('Plane exceeds native limits')
            return p | (32768 if v < 0 else 0)
        surfaces = [(plane(s[0]), index(s[1]), *s[2:6], s[6]&255) for s in a[5]]
        edges = [tuple(index(v) for v in row) for row in a[6]]
        vertices = [(*r[:3], index(r[3]), r[4]) for r in a[7]]
        inp, refs, out = [work/('references.'+ext) for ext in ('input','roots','output')]
        with inp.open('wb') as f:
            f.write(b'FGC1')
            for fmt, rows in zip(('4f','2H3h2B','6H','3fHh'),(a[1],surfaces,edges,vertices)):
                f.write(struct.pack('<I',len(rows)))
                for row in rows:
                    f.write(struct.pack('<'+fmt,*row))
        expected = [reachable(a[4], r[1]) for r in a[3]]
        with refs.open('wb') as f:
            f.write(struct.pack('<I',len(a[3])))
            for r, members in zip(a[3], expected):
                if not members:
                    raise ValueError('Empty source reference')
                f.write(struct.pack('<2I',plane(r[0]),len(members)))
                f.write(struct.pack('<'+'i'*len(members),*members))
        dotnet, binary, tool, env = compiler(ROOT,ROOT/'work/forge-world',memoize_2d=True)
        with (work/'references-builder.log').open('w') as log:
            subprocess.run([dotnet,str(binary),str(tool),str(inp),str(out),str(refs)],
                           cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        result = read_result(out)
        if result[5:] != [surfaces,edges,vertices]:
            raise ValueError('2D builder changed geometry')
        differences = []
        for n,(r,members) in enumerate(zip(result[3],expected)):
            actual=reachable(result[4],r[1],False)
            if members != actual:
                differences.append(dict(reference=n,missing=sorted(set(members)-set(actual)),
                                        added=sorted(set(actual)-set(members))))
        report=dict(references=len(expected),source_nodes=len(a[4]),rebuilt_nodes=len(result[4]),
                    source_sha256=hashlib.sha256(c.data).hexdigest(),
                    output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                    membership_differences=differences,status='accepted' if not differences else 'rejected')
        (work/'references-rebuild.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({**report,'membership_differences':len(differences)},indent=2))
        if differences:
            raise ValueError('Rebuilt reference changed its authored surface membership')
    finally:
        c.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--scenario',required=True)
    p.add_argument('--work',type=Path,required=True)
    build(**vars(p.parse_args()))
