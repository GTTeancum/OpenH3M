"""Read native compiled prop physics; do not substitute for MCC collision tests."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
def xml(path):return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def field(e,key):return e.find(f'./field[@name="{key}"]').get('value')
def source_blocks(t):
    blocks={};current=None
    for e in t:
        if e.tag=='field':
            current=e.get('name') if e.get('type')=='block' else None
            if current:blocks[current]=[]
        elif e.tag=='element' and current:blocks[current].append(e)
    return blocks
def vertices(rows):
    result=[]
    for e in rows:
        columns=[]
        for axis in 'xyz':
            columns.append([float(v) for v in field(e,'four vectors '+axis).split(',')]+[float(field(e,'havok w four vectors '+axis))])
        result.extend(zip(*columns))
    return result
reports=[]
for name in ('frunner_wheel','cex_health_cabinet','ff_redbase_rocks02'):
    export=json.loads((OUT/f'h3-prop-{name}-physics-export.json').read_text())
    assert hashlib.sha256(Path(export['jms']).read_bytes()).hexdigest()==export['jms_sha256']
    log=(OUT/f'h3-prop-{name}-physics-compile.log').read_text(errors='replace')
    assert not re.search(r'\b(ERROR|FATAL)\b',log)
    warnings=[line.strip() for line in log.splitlines() if 'WARNING' in line]
    target=KIT/f'tags/levels/custom/battle_canyon_fresh/props/{name}/{name}.physics_model'
    before=hashlib.sha256(target.read_bytes()).hexdigest();dest=OUT/f'h3-prop-{name}-physics.xml'
    with (OUT/f'h3-prop-{name}-physics-read.log').open('wb') as stream:
        result=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(target),str(dest)],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
    assert result.returncode==0 and dest.stat().st_size>1000 and hashlib.sha256(target.read_bytes()).hexdigest()==before
    t=xml(dest);blocks={b.get('name'):list(b) for b in t.findall('block')}
    source=source_blocks(xml(OUT/f'original-prop-{name}-physics.xml'))
    assert len(blocks['polyhedra'])==len(blocks['rigid bodies'])==len(blocks['materials'])==1
    assert field(blocks['materials'][0],'name')==export['material']
    assert field(blocks['materials'][0],'global material name')==field(source['materials'][0],'global material name')
    assert field(blocks['rigid bodies'][0],'motion type')==export['source_motion_type']
    source_names=[field(n,'name') for n in source['nodes']];native_names=[field(n,'name') for n in blocks['nodes']]
    # The unchanged Halo exporter removes authoring bone prefixes. This exact
    # wheel mapping also occurs in its previously compiled render/collision.
    expected=['pedestal','dummy001'] if name=='frunner_wheel' else source_names
    if name=='frunner_wheel':assert source_names==['b_pedestal','dummy001']
    assert native_names==expected
    for extension in ('render','collision'):
        other=xml(OUT/f'h3-prop-{name}-{extension}.xml')
        assert [field(n,'name') for n in other.find('./block[@name="nodes"]')]==native_names
    for old,new in zip(source['nodes'],blocks['nodes']):
        for relation in ('parent','sibling','child'):
            wanted=field(old,relation);index=-1 if wanted=='NONE' else source_names.index(wanted)
            assert int(field(new,relation).rsplit(',',1)[-1])==index
    node=int(field(blocks['rigid bodies'][0],'node').rsplit(',',1)[-1]);assert field(blocks['nodes'][node],'name')==export['source_body_node']
    poly=blocks['polyhedra'][0];assert int(field(poly,'num vertices'))==export['vertices']==int(field(source['polyhedra'][0],'num vertices'))
    a=vertices(source['polyhedron four vectors'])[:export['vertices']];b=vertices(blocks['polyhedron four vectors'])[:export['vertices']]
    # Exporters may reorder the unchanged source points; compare the sets.
    distance=lambda p,q:sum((x-y)**2 for x,y in zip(p,q))**.5
    deviation=max(max(min(distance(p,q) for q in b) for p in a),max(min(distance(p,q) for q in a) for p in b))
    geometry_matches=deviation<.00002
    differences={}
    for key in ('aabb half extents','aabb center','radius'):
        old=field(source['polyhedra'][0],key);new=field(poly,key)
        if old!=new:differences[key]=dict(reach=old,h3=new)
    reports.append(dict(name=name,physics_sha256=before,vertices=len(b),motion=export['source_motion_type'],
        material=export['material'],warnings=warnings,native_error_categories=len(blocks['errors']),source_to_native_nodes=list(zip(source_names,native_names)),maximum_xml_vertex_deviation=deviation,native_points_match_source=geometry_matches,native_bounds_differences=differences,
        limitation='Native compilation, vertex count, node hierarchy, shared motion and source material identifiers checked. Point/bounds differences are recorded, not waived or called exact preservation. Object/model material resolution and in-game collision remain unverified.'))
    print('PROP_PHYSICS_CHECK',name,len(b),'vertices',export['source_motion_type'],'source points match',geometry_matches,'max XML vertex deviation',deviation,'warnings',len(warnings),flush=True)
(OUT/'h3-prop-physics-verification.json').write_text(json.dumps(reports,indent=2)+'\n')
