"""Replace only the existing Sky Bridge map after coordinated shared-content access."""
import hashlib,json,os,shutil,struct,subprocess,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from build_scenario_checkpoint import resource_salt
from cache_reader import Cache

root=Path.cwd().resolve()
assert root==Path('C:/X360/ISOs/H3M/.local/OpenH3M-source').resolve()
shared=root/'work/dlc/installed-corrections'
target=shared/'0000000000000000/4D5307E6/00000002/C337EBA990B40F54512D18E8AB31188A2B040540/sky_bridge.map'
source=root/'work/sky-bridge/payload-32/sky_bridge.map'
old='506cdc953bed8c2a80c751b8ddbc8422a61549e9143d73446276947707d06e36'
new='311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d'
backup=root/'work/sky-bridge/candidate32-install-backup'
assert target.resolve().is_relative_to(root) and source.resolve().is_relative_to(root)
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def idle():
    r=subprocess.run(['powershell','-NoProfile','-Command',
        'if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }'],
        cwd=root,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
    if r.returncode:raise RuntimeError('Game is running; installation not changed')
idle()
assert digest(target)==old and digest(source)==new
assert not backup.exists()
raw=source.read_bytes();header=bytearray(raw[:0x3000]);stored=bytes(header[0x330:0x344])
assert int(np.bitwise_xor.reduce(np.frombuffer(raw,dtype='>u4',offset=0x3000)))==struct.unpack_from('>I',raw,0x2c4)[0]
for start,size in ((0x320,4),(0x328,8),(0x330,0x13c),(0x1c,0x100),(0x144,8),(0x16c,0x20),(0x49c,0x10)):
    header[start:start+size]=bytes(size)
assert stored==hashlib.sha1(resource_salt(Path('C:/X360/ISOs/H3M/default.xex'))+header).digest()
with_source=Cache(str(source))
try:
    scnr,=[t for t in with_source.tags.values() if t['group']=='scnr']
    assert with_source.u(scnr['offset']+8)==1747
    assert raw[0x18c:0x1ac].split(b'\0')[0]==b'sky_bridge'
finally:with_source.close()
for p in source.parent.iterdir():
    if p.name!='sky_bridge.map':assert digest(p)==digest(target.parent/p.name)
before={str(p.relative_to(shared)):digest(p) for p in shared.rglob('*') if p.is_file()}
bootstrap=Path('C:/X360/ISOs/H3M/OpenH3M.bootstrap.toml');settings=digest(bootstrap)
record=json.loads((root/'work/sky-bridge/shared-install-coordination.json').read_text())
runtime={row['target']:digest(Path(row['target'])) for row in record['runtime_comparison']}
assert all(runtime[row['target']]==row['tested_sha256'] for row in record['runtime_comparison'])
idle()
backup.mkdir();shutil.copyfile(target,backup/'sky_bridge.map')
assert digest(backup/'sky_bridge.map')==old
pending=target.with_suffix('.map.pending');assert not pending.exists()
shutil.copyfile(source,pending);assert digest(pending)==new
os.replace(pending,target)
after={str(p.relative_to(shared)):digest(p) for p in shared.rglob('*') if p.is_file()}
assert before.keys()==after.keys()
changed=[name for name in before if before[name]!=after[name]]
assert changed==[str(target.relative_to(shared))]
assert digest(bootstrap)==settings
assert all(digest(Path(p))==h for p,h in runtime.items())
report=dict(status='Candidate 32 installed for verification; not visually accepted',map=str(target),
    sha256=new,backup=str(backup/'sky_bridge.map'),changed_files=changed,
    unchanged_files=len(before)-1,bootstrap_sha256=settings,runtime_hashes=runtime,
    body_checksum_valid=True,header_digest_valid=True,map_identity=1747,
    before=before,after=after,
    coordination='Other chat confirmed research-only work and no concurrent shared writes; no Battle Canyon restore/copy or combined DLC rebuild.')
(root/'work/sky-bridge/candidate32-install.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('before','after','runtime_hashes')},indent=2))
