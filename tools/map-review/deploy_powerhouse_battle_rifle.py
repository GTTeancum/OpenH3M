"""Promote the natively verified map and actual LIVE bundle, preserving rollback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/powerhouse-battle-rifle'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--apply',action='store_true')
args=p.parse_args()
proof=json.loads((OUT/'proof.json').read_text())
package=json.loads((OUT/'package-proof.json').read_text())
acceptance=json.loads((OUT/'native-acceptance.json').read_text())
assert acceptance['approved_for_deployment'] is True
assert acceptance['map_sha256']==proof['candidate_sha256']
target=Path(proof['source']).resolve(strict=True)
assert target.is_relative_to(ROOT/'work/dlc/installed-corrections')
manifest=ROOT/'.local/releases/current-live/manifest.json'
manifest_before=manifest.read_bytes()
release=json.loads(manifest_before)
main=release['packages'][0]
assert main['name']=='Spartan Custom Maps'
assert sha(Path(main['package']))==main['sha256']==package['supersedes_sha256']
inventory={p.name:sha(p) for p in target.parent.iterdir()}
assert inventory=={e['name']:e['sha256'] for e in main['entries']}
assert inventory['powerhouse.map']==proof['before_sha256']
assert sha(OUT/'powerhouse.map')==proof['candidate_sha256']
candidate=Path(package['package']).resolve(strict=True)
assert candidate.parent==OUT and sha(candidate)==package['sha256']
new_inventory={e['name']:e['sha256'] for e in package['entries']}
assert set(new_inventory)==set(inventory)
assert {k for k in inventory if inventory[k]!=new_inventory[k]}=={'powerhouse.map'}
record=ROOT/'work/map-review-20261105/powerhouse-deployment.json'
previous=json.loads(record.read_text())
rollback=Path(previous['backup']).resolve(strict=True)
assert rollback.is_relative_to(ROOT/'work/map-review-20261105')
assert sha(rollback)==previous['before'] and previous['after']==proof['before_sha256']
final=Path(main['package']).parent/candidate.name
assert final.resolve().is_relative_to(ROOT/'.local/releases/current-live') and not final.exists()
old_active=Path(main['package'])
rollback_package=ROOT/'.local/releases/current-live/rollback'/old_active.name
assert rollback_package.resolve().is_relative_to(ROOT/'.local/releases/current-live') and not rollback_package.exists()
print('Verified promotion plan: map plus main LIVE bundle; other payloads unchanged.',flush=True)
if not args.apply:raise SystemExit(0)
subprocess.run(['powershell','-NoProfile','-Command',
    'if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { exit 1 }'],
    cwd=ROOT,check=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
assert manifest.read_bytes()==manifest_before
assert sha(target)==proof['before_sha256']
temporary=target.with_name('powerhouse.map.br-new')
assert not temporary.exists()
shutil.copy2(target,rollback)
assert sha(rollback)==proof['before_sha256']
shutil.copy2(OUT/'powerhouse.map',temporary)
assert sha(temporary)==proof['candidate_sha256']
os.replace(temporary,target)
assert {p.name:sha(p) for p in target.parent.iterdir()}==new_inventory
candidate.rename(final)
assert sha(final)==package['sha256']
rollback_package.parent.mkdir(exist_ok=True)
old_active.rename(rollback_package)
old_package=str(rollback_package)
main.update(package=str(final),sha256=package['sha256'],bytes=package['bytes'],
    entries=package['entries'],integrity=package['integrity'],
    powerhouse_status='18.4559% polygon reduction preserved; stock H3 Battle Rifle replacement natively tested. Xbox360 hardware/system-link untested.')
release.update(release_date='2026-11-11',superseded_main=old_package)
temp_manifest=manifest.with_suffix('.br-new.json')
temp_manifest.write_text(json.dumps(release,indent=2)+'\n')
assert manifest.read_bytes()==manifest_before
os.replace(temp_manifest,manifest)
deployment=dict(target=str(target),backup=str(rollback),before=proof['before_sha256'],
    after=proof['candidate_sha256'],sanctuary_preserved=True,metadata_preserved=True,
    executable_and_settings_changed=False,package=str(final),package_sha256=sha(final),
    rollback_package=old_package,native_acceptance=str(OUT/'native-acceptance.json'))
record.write_text(json.dumps(deployment,indent=2)+'\n')
(OUT/'deployment.json').write_text(json.dumps(deployment,indent=2)+'\n')
package['package']=str(final);package['installed_modified']=True
(OUT/'package-proof.json').write_text(json.dumps(package,indent=2)+'\n')
print(json.dumps(deployment,indent=2))
