"""Replace Sky Bridge DMR placements; remove its redundant Forge selection."""
import hashlib,json,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
from audit_stock_battle_rifle import audit

OUT=ROOT/'work/sky-bridge-battle-rifle'
EXPECTED='548eb730c63289b1c9ce1509673433cd51db9ee094df28cc3f4d2b52c9160d4f'
DMR,BR=0x90002735,0xee850d0f
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

source=next((ROOT/'work/dlc/installed-corrections').rglob('sky_bridge.map'))
assert sha(source)==EXPECTED
builder=MapBuilder(source,0);c=builder.cache
donor=audit(c)
sc=next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
palette=c.block(sc+0x128,48);forge=c.block(sc+0x1f4,48)
assert c.u(palette[10]+12)==DMR
assert len(forge)==29 and c.u(forge[-1]+12)==DMR and c.u(forge[1]+12)==BR
assert sum(c.u(r+12)==BR for r in forge)==1
positions=[dict(index=i,position=c.unpack('3f',r+8)) for i,r in enumerate(c.block(sc+0x11c,168)) if c.unpack('h',r)[0]==10]
assert [p['index'] for p in positions]==[14,15,27,29]
simulation=c.block(sc+0x6a4,4)
assert c.u(simulation[19])==DMR and c.u(simulation[879])==BR
writes={palette[10]+12:BR,sc+0x1f4:28}
for offset,value in writes.items():builder.put(offset-c.start+c.base,'I',value)
data=builder.finish(resource_salt(ROOT/'../../default.xex'))
allowed=set(range(0x2c4,0x2c8))|set(range(0x330,0x344))
for off in writes:allowed.update(range(off,off+4))
assert len(data)==len(c.data)
changed=np.flatnonzero(np.frombuffer(data,dtype=np.uint8)!=np.frombuffer(c.data,dtype=np.uint8)).tolist()
assert set(changed)<=allowed
OUT.mkdir(exist_ok=True);target=OUT/'sky_bridge.map'
assert not target.exists();target.write_bytes(data)
report=dict(source=str(source),before_sha256=EXPECTED,candidate=str(target),candidate_sha256=sha(target),
    replacements=positions,from_datum=hex(DMR),to_datum=hex(BR),changed_byte_offsets=changed,
    forge_before=29,forge_after=28,forge_decision='Remove final DMR row; preserve existing stock BR row and all other rows/budgets/labels exactly.',
    all_other_bytes_identical_except_checksums=True,accepted_geometry_weather_effect_corrections_preserved=True,
    unused_dmr_data_retained='Unselected tag, unused final palette allocation and simulation registration retained; wire indices unchanged.',
    donor_audit=donor,installed_content_modified=False,native_verified=False,
    attribution='Sky Bridge (Halo Online), General Heed / Priception, Halo Online Map Pack For Halo 3: https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. Xbox360/OpenH3M adaptation by this project.')
(OUT/'proof.json').write_text(json.dumps(report,indent=2)+'\n')
builder.close();print(json.dumps(report,indent=2))
