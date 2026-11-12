"""Build a candidate main LIVE bundle without changing the installed release."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from build_dlc_live import build
from verify_dlc_stfs import verify,verify_payload

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

out=ROOT/'work/powerhouse-battle-rifle'
proof=json.loads((out/'proof.json').read_text())
release=json.loads((ROOT/'.local/releases/current-live/manifest.json').read_text())
main=release['packages'][0]
assert main['name']=='Spartan Custom Maps'
source=Path(main['installed_source']).resolve(strict=True)
assert source.is_relative_to(ROOT/'work/dlc/installed-corrections')
inventory={e['name']:e['sha256'] for e in main['entries']}
assert {p.name:sha(p) for p in source.iterdir()}==inventory
assert sha(Path(main['package']))==main['sha256']
assert inventory['powerhouse.map']==proof['before_sha256']
assert sha(out/'powerhouse.map')==proof['candidate_sha256']
stage=out/'payload'
stage.mkdir()
for p in source.iterdir():
    # Read-only staging links avoid duplicating a full installation.
    os.link(out/'powerhouse.map' if p.name=='powerhouse.map' else p,stage/p.name)
package=build(stage,out/'candidate-live')
path=Path(package['package'])
with path.open('r+b') as f:
    header=bytearray(f.read(0xB000))
    for locale in range(9):
        for off,value in ((0x411,main['name']),(0xD11,'Current Halo 3 custom maps; Powerhouse stock Battle Rifle correction.')):
            at=off+locale*256
            header[at:at+256]=value.encode('utf-16-be').ljust(256,b'\0')
    header[0x32c:0x340]=hashlib.sha1(header[0x344:]).digest()
    f.seek(0);f.write(header)
final=path.with_name(header[0x32c:0x340].hex().upper())
assert not final.exists()
path.rename(final)
with final.open('rb') as f:integrity=verify(f)
entries=verify_payload(final,stage)
expected=dict(inventory)
expected['powerhouse.map']=proof['candidate_sha256']
assert {e['name']:e['sha256'] for e in entries}==expected
assert {p.name:sha(p) for p in source.iterdir()}==inventory
package.update(package=str(final),sha256=sha(final),content_id=final.name,integrity=integrity,
    entries=entries,supersedes_sha256=main['sha256'],installed_modified=False,
    native_validation='Pending coordinated test; do not promote yet')
(out/'package-proof.json').write_text(json.dumps(package,indent=2)+'\n')
# Remove only the verified staging links. The installed files and candidate stay.
assert stage.resolve().is_relative_to(out.resolve())
for p in stage.iterdir():
    assert p.name in expected and sha(p)==expected[p.name]
    p.unlink()
stage.rmdir()
print(json.dumps({k:v for k,v in package.items() if k!='entries'},indent=2))
