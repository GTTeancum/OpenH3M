"""Build and verify the changed main LIVE bundle; retain old package until cleanup."""
import hashlib
import json
import shutil
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser()
p.add_argument('--map',choices=['elongation','powerhouse'],default='elongation')
args=p.parse_args()
changed_name=args.map+'.map'
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from build_dlc_live import build
from verify_dlc_stfs import verify, verify_payload

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

release = ROOT / '.local/releases/current-live'
manifest = release / 'manifest.json'
data = json.loads(manifest.read_text())
main, sky = data['packages']
assert main['name'] == 'Spartan Custom Maps' and sky['name'] == 'Sky Bridge'
old = Path(main['package']).resolve(strict=True)
source = Path(main['installed_source']).resolve(strict=True)
assert old.is_relative_to(release) and source.is_relative_to(ROOT / 'work/dlc/installed-corrections')
assert sha(old) == main['sha256'] and sha(Path(sky['package'])) == sky['sha256']
inventory = {p.name: sha(p) for p in source.iterdir()}
previous = {e['name']: e['sha256'] for e in main['entries']}
assert inventory.keys() == previous.keys()
assert {k for k in inventory if inventory[k] != previous[k]} == {changed_name}
deploy = json.loads((ROOT / 'work/map-review-20261105'/(args.map+'-deployment.json')).read_text())
assert inventory[changed_name] == deploy['after']
assert shutil.disk_usage(ROOT).free > main['bytes'] * 1.1
result = build(source, old.parent / 'building-main-refresh')
candidate = Path(result['package'])
with candidate.open('r+b') as stream:
    header = bytearray(stream.read(0xB000))
    for locale in range(9):
        for offset, text in ((0x411, main['name']), (0xD11, 'Current installed Halo 3 custom maps. Unsigned RGH/JTAG test package.')):
            at = offset + locale * 256
            header[at:at+256] = text.encode('utf-16-be').ljust(256, b'\0')
    header[0x32C:0x340] = hashlib.sha1(header[0x344:]).digest()
    stream.seek(0)
    stream.write(header)
final = candidate.with_name(header[0x32C:0x340].hex().upper())
assert not final.exists()
candidate.rename(final)
with final.open('rb') as stream:
    integrity = verify(stream)
entries = verify_payload(final, source)
assert {e['name']: e['sha256'] for e in entries} == inventory
assert {p.name: sha(p) for p in source.iterdir()} == inventory
assert sha(Path(sky['package'])) == sky['sha256']
main.update(package=str(final), bytes=final.stat().st_size, sha256=sha(final), entries=entries,
            integrity=integrity, conveyor_status='Tested linear-animation correction included; console runtime not tested')
if args.map=='powerhouse':
    main['powerhouse_status']='18.4559% polygon reduction; preservation audit and three native views reviewed. FPS gain and console runtime unverified.'
data.update(release_date='2026-11-11', superseded_main=str(old))
manifest.write_text(json.dumps(data, indent=2))
print(json.dumps(dict(package=str(final), superseded=str(old), verified_files=len(entries), sky_preserved=True), indent=2))
