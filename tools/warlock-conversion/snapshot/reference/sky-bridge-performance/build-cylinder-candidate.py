"""Private cylinder experiment: exclude proven redundant render references only.

All instance records, collision, render meshes, shaders and resource bytes stay
unchanged. This is intentionally limited to five geometrically audited instances;
it does not infer native flag semantics or suppress every source flag64 instance.
"""
from pathlib import Path
import hashlib,json,shutil,sys
import numpy as np
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
assert Path.cwd().resolve()==REPO
sys.path.insert(0,str(REPO/'tools/warlock-conversion/snapshot/tools'))
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
basis=REPO/'work/sky-bridge/payload-36';out=REPO/'work/sky-bridge/payload-37'
expected='39873291ea89a3225a53ecda3f9811f7429ab46c8760ebc07a9938fcf8dd0245'
assert hashlib.sha256((basis/'sky_bridge.map').read_bytes()).hexdigest()==expected
audit=json.loads((REPO/'work/sky-bridge/marked-object-review/cylinder-overlap.json').read_text())
exclude={637,638,639,640,1073};keep={1032,1071}
for i in exclude:
    assert any(v['original']==i and v['merged'] in keep and v['material_equal'] and v['maximum_triangle_corner_distance']<.0021 for v in audit['geometry_comparisons'])
assert not out.exists();shutil.copytree(basis,out)
b=MapBuilder(basis/'sky_bridge.map',reserve=0);c=b.cache
changes=[];allowed=set(range(0x2c4,0x2c8))|set(range(0x330,0x344))
for tid,tag in c.tags.items():
    roots=[(tag['offset'],0x2e4)] if tag['group']=='sbsp' else [(r,0x134) for r in c.block(tag['offset']+4,436)] if tag['group']=='sLdT' else []
    for root,field in roots:
        for mi,mesh in enumerate(c.block(root+field,76)):
            for bucket in c.block(mesh+52,16):
                rows=c.block(bucket+4,2);before=[c.unpack('h',r)[0] for r in rows]
                after=[i for i in before if i not in exclude]
                if before==after:continue
                address=bucket+4-c.start+c.base;b.put(address,'I',len(after));allowed.update(range(bucket+4,bucket+8))
                for row,value in zip(rows,after):
                    b.put(row-c.start+c.base,'h',value);allowed.update(range(row,row+2))
                changes.append(dict(owner=tid,cluster_mesh=mi,bucket_mesh=c.unpack('h',bucket)[0],
                    offset=bucket+4,before=before,after=after))
assert {i for row in changes for i in row['before'] if i in exclude}==exclude
data=b.finish(resource_salt('C:/X360/ISOs/H3M/default.xex'))
assert len(data)==len(b.original)
different=np.flatnonzero(np.frombuffer(data,dtype=np.uint8)!=np.frombuffer(b.original,dtype=np.uint8)).tolist()
assert set(different)<=allowed
assert all(c.data[row:row+120]==data[row:row+120] for row in c.block(c.tags[9225]['offset']+0x1b0,120))
(out/'sky_bridge.map').write_bytes(data)
result=dict(candidate=37,basis_sha256=expected,sha256=hashlib.sha256(data).hexdigest(),
    excluded_instances=sorted(exclude),retained_visible_instances=sorted(keep),changes=changes,
    changed_byte_count=len(different),changed_offsets=different,
    invariant='Entire map byte comparison allows only render-reference counts/list entries and checksum/header digest. All collision, instance records, geometry and resources unchanged.',
    status='Private experiment, not yet runtime verified or installed.',
    credit=json.loads((REF/'candidate36-visual-review-result.json').read_text())['credit'])
(REPO/'work/sky-bridge/marked-object-review/candidate37-build.json').write_text(json.dumps(result,indent=2)+'\n');b.close()
print(json.dumps(result,indent=2))
