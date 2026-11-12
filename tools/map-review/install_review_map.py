"""Install one reviewed map, preserving its existing DLC metadata and Sanctuary."""
import argparse, hashlib, json, os, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / 'work/dlc/installed-corrections'
def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

p = argparse.ArgumentParser()
p.add_argument('manifest', type=Path)
p.add_argument('--apply', action='store_true')
p.add_argument('--replace-rollback', action='store_true', help='Retain only the latest verified pre-install map')
a = p.parse_args()
manifest = a.manifest.resolve(strict=True)
assert manifest.is_relative_to(ROOT)
r = json.loads(manifest.read_text())
assert len(r['maps']) == 1
name = r['maps'][0]['name']
assert name in ('chiron', 'rodentia', 'resuscitation', 'powerhouse', 'elongation')
target = Path(r['installed_target']).resolve(strict=True)
assert target.is_relative_to(SHARED) and target.name == name + '.map'
source = manifest.with_suffix('') / target.name
assert source.resolve(strict=True).is_relative_to(ROOT)
assert sha(source) == r['files'][target.name] == r['maps'][0]['sha256']
assert sha(target) == r['installed_before_sha256'], 'Installed map changed; inspect before rebasing'
for filename, digest in r['files'].items():
    assert Path(filename).name == filename
    if filename != target.name:
        assert sha(source.parent / filename) == sha(target.parent / filename) == digest
sanctuary_record = json.loads((ROOT / 'work/sanctuary/deployment-09.json').read_text())
sanctuary = Path(sanctuary_record['installed']).resolve(strict=True)
assert sanctuary.is_relative_to(SHARED)
assert sha(sanctuary) == sanctuary_record['after']
if not a.apply:
    print('Prepared single-map deployment:', source, '->', target)
else:
    subprocess.run(['powershell', '-NoProfile', '-Command',
        'if (Get-Process OpenH3M,halo3mp -ErrorAction SilentlyContinue) { exit 1 }'],
        cwd=ROOT, check=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    backup = manifest.parent / (name + '-before-review.map')
    temporary = target.with_name(target.name + '.review-new')
    assert not temporary.exists()
    if backup.exists():
        assert a.replace_rollback
        prior=json.loads((manifest.parent/(name+'-deployment.json')).read_text())
        assert sha(backup)==prior['before'] and sha(target)==prior['after'], 'Rollback chain changed'
    shutil.copy2(target, backup)
    assert sha(backup) == r['installed_before_sha256']
    shutil.copy2(source, temporary)
    assert sha(temporary) == r['files'][target.name]
    os.replace(temporary, target)
    assert sha(target) == r['files'][target.name]
    assert sha(sanctuary) == sanctuary_record['after']
    result = dict(target=str(target), backup=str(backup), before=sha(backup),
        after=sha(target), sanctuary_preserved=True, metadata_preserved=True,
        executable_and_settings_changed=False)
    (manifest.parent / (name + '-deployment.json')).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
