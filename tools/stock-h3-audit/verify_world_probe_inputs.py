"""Read both diagnostic ASS files through the unchanged reader; compare geometry."""
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.file_ass.process_file import process_file

def canonical(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if hasattr(value,'__dict__'):return {k:canonical(v) for k,v in vars(value).items()}
    if isinstance(value,dict):return {k:canonical(v) for k,v in value.items()}
    return [canonical(v) for v in value]
reports=[json.loads((OUT/('world-collision-'+kind+'-probe.json')).read_text()) for kind in ('baseline','precise')]
assert reports[0]['source_sha256']==reports[1]['source_sha256']
assets=[]
for r in reports:
    assert hashlib.sha256(Path(r['ass']).read_bytes()).hexdigest()==r['ass_sha256']
    assets.append(process_file(r['ass']))
assert canonical(assets[0].objects)==canonical(assets[1].objects)
# Exporter-generated unique IDs vary between Blender processes. ASS parenting
# uses array indices; compare every transform and reference without those IDs.
instances=[canonical(a.instances) for a in assets]
ids=[[i.pop('unique_id') for i in rows] for rows in instances]
assert instances[0]==instances[1],'Instance transforms/references differ'
assert len(assets[0].materials)==len(assets[1].materials)
report=dict(source_sha256=reports[0]['source_sha256'],ass_sha256=[r['ass_sha256'] for r in reports],
    identical_geometry_and_instance_transforms=True,exporter_instance_ids=ids,
    triangles=sum(len(o.triangles) for o in assets[0].objects),
    limitation='Exact ASS geometry/instance equality between baseline and Precise diagnostic; not compiled geometry or gameplay validation.')
(OUT/'world-collision-input-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_PROBE_INPUTS_VERIFIED',json.dumps(report),flush=True)
