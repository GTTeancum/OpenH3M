"""Package Haven's baked authoring tags with unchanged official H3 Tool."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h3ek'
sky_visible = '--sky-visible' in sys.argv
name = 'haven_skyview' if sky_visible else 'haven_preview'
DEST = OUT / ('sky-cache' if sky_visible else 'preview-cache')
assert not DEST.exists(), 'Inspect/preserve the previous build before retrying'
assert not (KIT / 'maps' / (name + '.map')).exists(), 'Do not overwrite a cache'
bake = json.loads((OUT / 'draft-lighting-2026110503/report.json').read_text())
assert bake['status'] == 'commands-completed'
assert all(s['returncode'] == 0 for s in bake['steps'])

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

for path, digest in bake['after'].items():
    assert sha(Path(path)) == digest, 'Baked input changed: ' + path
if sky_visible:
    old = (KIT / 'tags/levels/custom/haven_h4/haven.scenario_structure_bsp').read_bytes()
    new = (KIT / 'tags/levels/custom/haven_h4/haven_sky.scenario_structure_bsp').read_bytes()
    assert len(old) == len(new)
    differences = [(i, a, b) for i, (a, b) in enumerate(zip(old, new)) if a != b]
    # ManagedBlam also refreshes serialized identifiers/checksums on Save.
    # Preserve the complete diff as evidence; the authoring helper reopens and
    # verifies all eight sky-index fields through the official API.
DEST.mkdir()
env = os.environ.copy()
for key, subdir in [('TEMP', 'temp'), ('TMP', 'temp'),
                    ('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local')]:
    env[key] = str(OUT / 'h3-authoring' / subdir)
command = [str(KIT / 'tool.exe'), 'build-cache-file',
           'levels\\custom\\haven_h4\\' + name, 'x64']
report = dict(status='running', command=command, rendering_verified=False,
              native_h3_candidate=False, bake_job=bake['job'])
if sky_visible:
    report['bsp_serialized_byte_changes'] = differences
    report['sky_assignment_check'] = 'PrepareHavenSkyVisibility official API save/reopen: 8 clusters, sky 0'
    report['bsp_sha256'] = sha(KIT / 'tags/levels/custom/haven_h4/haven_sky.scenario_structure_bsp')
report_path = DEST / 'report.json'

def save():
    report_path.write_text(json.dumps(report, indent=2) + '\n')

started = time.monotonic()
with (DEST / 'build.log').open('wb') as log:
    process = subprocess.Popen(command, cwd=KIT, env=env, stdout=log,
                               stderr=subprocess.STDOUT)
    report['pid'] = process.pid
    save()
    try:
        report['returncode'] = process.wait(timeout=600)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        report['status'] = 'timeout'
        save()
        raise
report['seconds'] = time.monotonic() - started
cache = KIT / 'maps' / (name + '.map')
report['status'] = 'compiled' if report['returncode'] == 0 and cache.is_file() else 'failed'
if cache.is_file():
    report.update(output=str(cache.relative_to(ROOT)), bytes=cache.stat().st_size,
                  sha256=sha(cache))
save()
print(json.dumps(report, indent=2))
if report['status'] != 'compiled':
    raise SystemExit(1)
