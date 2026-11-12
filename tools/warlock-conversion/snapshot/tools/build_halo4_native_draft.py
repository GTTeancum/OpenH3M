"""Run the existing MCC-to-original-H3 pipeline on the baked Haven preview."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from cache_reader import Cache
from inventory_conversion import scenario
from preflight_collision_budget import inspect as inspect_collision
from preflight_variant_budget import inspect as inspect_variant
from source_schema import load_schema

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', type=int, required=True)
parser.add_argument('--sky-visible', action='store_true')
parser.add_argument('--source-report', type=Path, help='Repository-local official-tool diagnostic build report')
args = parser.parse_args()
assert args.candidate > 0
dest = ROOT / '.local/haven' / ('candidate' + str(args.candidate))
assert not dest.exists(), 'Keep prior candidate evidence; choose a fresh number'
built_path = args.source_report or (OUT / ('sky-cache' if args.sky_visible else 'preview-cache') / 'report.json')
assert built_path.resolve().is_relative_to(ROOT.resolve())
built = json.loads(built_path.read_text())
source = ROOT / built['output']
assert source.resolve().is_relative_to(ROOT.resolve())
assert built['status'] == 'compiled'
with source.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == built['sha256']
cache = Cache(source, True)
try:
    inventory = scenario(cache, load_schema(cache, 'scnr'))
    assert inventory['references']['Lightmaps']['name'] == r'levels\custom\haven_h4\haven_preview_faux_lightmap'
    sky_refs = [ref for row in inventory['blocks']['Skies']['references']
                for ref in row.values() if ref]
    assert any(ref['name'] == r'levels\custom\haven_h4\sky\sky' for ref in sky_refs), sky_refs
    assert inventory['blocks']['Scenery']['count'] == 510
    assert inventory['blocks']['Structure BSPs']['count'] == 1
    collision, variant = inspect_collision(cache), inspect_variant(cache)
    assert collision['conversion_ready'] and variant['conversion_ready']
    readback = dict(source_sha256=built['sha256'], scenario=inventory,
                    collision=collision, variant=variant, rendering_verified=False)
finally:
    cache.close()
dest.mkdir(parents=True)
(dest / 'source-readback.json').write_text(json.dumps(readback, indent=2) + '\n')
command = [sys.executable, '-B', str(Path(__file__).with_name('build_scenario_checkpoint.py')),
           '--project', str(ROOT), '--haven-draft', '--slot', 'zanzibar',
           '--source', str(source), '--basis', 'C:/X360/ISOs/H3M/maps/zanzibar.map',
           '--xex', 'C:/X360/ISOs/H3M/default.xex', '--disc-maps', 'C:/X360/ISOs/H3M/maps',
           '--sound-bank', 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb',
           '--decoder', 'C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe',
           '--output', str(dest / 'zanzibar.map'), '--report', str(dest / 'build.json')]
env = os.environ.copy()
for key, subdir in [('TEMP', 'temp'), ('TMP', 'temp'),
                    ('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local')]:
    env[key] = str(OUT / 'h3-authoring' / subdir)
env['PYTHONDONTWRITEBYTECODE'] = '1'
started = time.monotonic()
run = dict(command=command, status='running', rendering_verified=False)
with (dest / 'build.log').open('wb') as log:
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    run['pid'] = process.pid
    (dest / 'run.json').write_text(json.dumps(run, indent=2) + '\n')
    try:
        run['returncode'] = process.wait(timeout=900)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
        run.update(status='timeout', seconds=time.monotonic() - started)
        (dest / 'run.json').write_text(json.dumps(run, indent=2) + '\n')
        raise
run.update(status='completed' if run['returncode'] == 0 else 'failed',
           seconds=time.monotonic() - started)
(dest / 'run.json').write_text(json.dumps(run, indent=2) + '\n')
print(json.dumps(run, indent=2))
raise SystemExit(run['returncode'])
