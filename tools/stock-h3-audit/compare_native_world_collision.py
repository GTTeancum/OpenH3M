"""Compare original and official-H3 collision geometry using native API evidence."""
import collections
import hashlib
import json
from pathlib import Path
from mathutils import Vector,kdtree
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
source=json.loads((OUT/'original-world-collision.json').read_text())
native=json.loads((OUT/'world-collision-source-native-api.json').read_text())
compiled=json.loads((OUT/'world-collision-source-native.json').read_text())
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(source['source'])==source['sha256']
assert sha(native['source'])==native['sha256']==compiled['native_tag_sha256']
a=source['collision']['large collision bsp'][0]
b=native['collision']['large collision bsp'][0]

def polygons(raw):
    result=[]
    for index,surface in enumerate(raw['surfaces']):
        first=edge_index=surface['first edge'];vertices=[]
        while True:
            edge=raw['edges'][edge_index]
            if edge['left surface']==index:
                vertices.append(edge['start vertex']);edge_index=edge['forward edge']
            else:
                assert edge['right surface']==index
                vertices.append(edge['end vertex']);edge_index=edge['reverse edge']
            if edge_index==first:break
            assert len(vertices)<1000
        result.append(vertices)
    return result

av=[Vector(v['point']) for v in a['vertices']];bv=[Vector(v['point']) for v in b['vertices']]
ap=polygons(a);bp=polygons(b)
trees=[]
for vertices in (av,bv):
    tree=kdtree.KDTree(len(vertices))
    for i,v in enumerate(vertices):tree.insert(v,i)
    tree.balance();trees.append(tree)
vertex_distance=[max(trees[1].find(v)[2] for v in av),max(trees[0].find(v)[2] for v in bv)]
expected=[Vector(tuple(c*.01 for c in v*100)) for v in av]
roundtrip_tree=kdtree.KDTree(len(expected))
for i,v in enumerate(expected):roundtrip_tree.insert(v,i)
roundtrip_tree.balance()
roundtrip_distance=max(roundtrip_tree.find(v)[2] for v in bv)
geometries=[BVHTree.FromPolygons(av,ap,all_triangles=False),BVHTree.FromPolygons(bv,bp,all_triangles=False)]

def normalized(path):return path.replace('\\\\','\\').lower()
def identity(surface,materials,is_source):
    index=surface['material']
    if index<0:shader='+sky'
    else:
        shader=materials[index]['render method']
        if is_source:
            target=bindings['bindings'][shader]['export_tag']
            shader=str(Path(target).relative_to(ROOT/'work/editing-kits/h3ek/tags'))
        shader=normalized(shader)
    return shader,tuple(surface['flags'][k] for k in ('two sided','invisible','climbable','breakable','invalid','slip'))
identities=[[identity(s,source['material_names'],True) for s in a['surfaces']],
    [identity(s,native['materials'],False) for s in b['surfaces']]]
directions=[]
for label,vertices,faces,target,target_vertices,target_faces,expected,actual in (
    ('source_to_h3',av,ap,geometries[1],bv,bp,identities[0],identities[1]),
    ('h3_to_source',bv,bp,geometries[0],av,ap,identities[1],identities[0])):
    maximum=0;worst=[];mismatches=[]
    identity_trees={}
    for i,face in enumerate(faces):
        center=sum((vertices[j] for j in face),Vector())/len(face)
        _,_,nearest,distance=target.find_nearest(center)
        assert nearest is not None
        maximum=max(maximum,distance)
        if distance>1e-4:worst.append(dict(surface=i,nearest_surface=nearest,distance=distance))
        if expected[i]!=actual[nearest]:
            wanted=expected[i]
            if wanted not in identity_trees:
                subset=[p for p,kind in zip(target_faces,actual) if kind==wanted]
                identity_trees[wanted]=BVHTree.FromPolygons(target_vertices,subset,all_triangles=False) if subset else None
            matching=identity_trees[wanted]
            same_identity_distance=matching.find_nearest(center)[3] if matching else None
            mismatches.append(dict(surface=i,nearest_surface=nearest,distance=distance,
                expected=expected[i],actual=actual[nearest],nearest_matching_identity_distance=same_identity_distance))
    directions.append(dict(direction=label,centroids_checked=len(faces),maximum_distance=maximum,
        over_strict_distance_threshold=worst,material_or_flag_mismatches=mismatches))
report=dict(original_tag_sha256=source['sha256'],native_tag_sha256=native['sha256'],
    source_vertices=len(av),native_vertices=len(bv),maximum_vertex_distances=vertex_distance,
    maximum_native_vertex_distance_from_float32_unit_roundtrip=roundtrip_distance,
    source_surfaces=len(ap),native_surfaces=len(bp),native_boundary_edges=sum(e['left surface']<0 or e['right surface']<0 for e in b['edges']),
    directions=directions,strict_distance_threshold_world_units=1e-4,
    limitation='All vertices and polygon centroids compared in both directions. This is sampled geometric/material evidence, not continuous-surface equivalence, traversal or MCC acceptance.')
(OUT/'world-collision-source-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_COLLISION_COMPARISON',json.dumps(dict(vertex_distances=vertex_distance,unit_roundtrip_distance=roundtrip_distance,
    directions=[dict(direction=d['direction'],centroids=d['centroids_checked'],maximum=d['maximum_distance'],
        over_threshold=len(d['over_strict_distance_threshold']),identity_mismatches=len(d['material_or_flag_mismatches'])) for d in directions])),flush=True)
