"""Private causal control only: mute two electric_02 light parts, preserve arcs.

This intentionally removes authored behavior and MUST NOT be promoted as a fix.
"""
import hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[5];assert Path.cwd().resolve()==REPO
sys.path.insert(0,str(REPO/'tools/warlock-conversion/snapshot/tools'))
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
basis=REPO/'work/sky-bridge/payload-36';out=REPO/'work/sky-bridge/payload-39'
assert not out.exists();shutil.copytree(basis,out)
b=MapBuilder(basis/'sky_bridge.map',0);c=b.cache
assert hashlib.sha256(b.original).hexdigest()=='39873291ea89a3225a53ecda3f9811f7429ab46c8760ebc07a9938fcf8dd0245'
changes=[]
for i,event in enumerate(c.block(c.tags[10419]['offset']+0x2c,68)):
    part,=c.block(event+0x20,96)
    assert c.u(part+0x1c)&65535==10420 and c.tags[10420]['group']=='ligh'
    # Candidate38's debug flag did not suppress runtime lights. A zero part
    # count removes their creation path; particle-system blocks remain intact.
    assert c.u(event+0x20)==1
    b.put(event+0x20-c.start+c.base,'I',0)
    changes.append(dict(event=i,offset=event+0x20,before=1,after=0))
assert len(changes)==2
data=b.finish(resource_salt('C:/X360/ISOs/H3M/default.xex'))
allowed={x for row in changes for x in range(row['offset'],row['offset']+4)}|set(range(0x2c4,0x2c8))|set(range(0x330,0x344))
diff=np.flatnonzero(np.frombuffer(data,dtype=np.uint8)!=np.frombuffer(b.original,dtype=np.uint8)).tolist();assert set(diff)<=allowed
(out/'sky_bridge.map').write_bytes(data)
report=dict(candidate=39,sha256=hashlib.sha256(data).hexdigest(),changes=changes,changed_offsets=diff,
    status='Diagnostic light-muting control only; not a correction and never install or release.',
    credit=json.loads((Path(__file__).parent/'candidate36-visual-review-result.json').read_text())['credit'])
(REPO/'work/sky-bridge/marked-object-review/candidate39-build.json').write_text(json.dumps(report,indent=2)+'\n');b.close();print(json.dumps(report,indent=2))
