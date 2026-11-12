"""Package current installed maps directly, without duplicate payload staging."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from build_dlc_live import build
from verify_dlc_stfs import verify, verify_payload

BASE = ROOT / 'work/dlc/installed-corrections/0000000000000000/4D5307E6/00000002'
RELEASE = ROOT / '.local/releases/current-live'
DEST = RELEASE / 'Content/0000000000000000/4D5307E6/00000002'
BUNDLES = [
    ('Spartan Custom Maps', 'E3C216511E5A0ED8A2E37F70BC65E407C481C510',
     {'chiron', 'desolation', 'elongation', 'forge_gulch', 'forge_island',
      'powerhouse', 'prisoner', 'resuscitation', 'rodentia', 'sanctuary', 'warlock'}),
    ('Sky Bridge', 'C337EBA990B40F54512D18E8AB31188A2B040540', {'sky_bridge'}),
]

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert not RELEASE.exists(), 'Inspect existing current release before replacing it'
inventories = {}
payload_bytes = 0
for label, folder, maps in BUNDLES:
    source = BASE / folder
    assert source.resolve().is_relative_to(ROOT)
    expected = {name + ext for name in maps for ext in ('.map', '.mapinfo')}
    expected |= {'dlc_' + name + suffix + '.blf' for name in maps
                 for suffix in ('', '_sm', '_clip', '_film', '_variant')}
    assert {p.name for p in source.iterdir()} == expected
    files = list(source.iterdir())
    assert all(p.is_file() and not p.is_symlink() for p in files)
    inventories[folder] = {p.name: sha(p) for p in files}
    payload_bytes += sum(p.stat().st_size for p in files)
free = shutil.disk_usage(ROOT).free
assert free > payload_bytes * 1.05 + 100*1024**2, 'Insufficient room for two containers'
DEST.mkdir(parents=True)
reports = []
for label, folder, maps in BUNDLES:
    source = BASE / folder
    result = build(source, DEST / ('building-' + folder))
    package = Path(result['package'])
    with package.open('r+b') as stream:
        header = bytearray(stream.read(0xB000))
        assert header[:4] == b'LIVE'
        def text(at, value):
            encoded = value.encode('utf-16-be')
            assert len(encoded) + 2 <= 256
            header[at:at+256] = encoded.ljust(256, b'\0')
        for locale in range(9):
            text(0x411 + locale*256, label)
            text(0xD11 + locale*256,
                 'Current installed Halo 3 custom maps. Unsigned RGH/JTAG test package.')
        header[0x32C:0x340] = hashlib.sha1(header[0x344:]).digest()
        stream.seek(0)
        stream.write(header)
    final = package.with_name(header[0x32C:0x340].hex().upper())
    assert not final.exists()
    package.rename(final)
    with final.open('rb') as stream:
        integrity = verify(stream)
    entries = verify_payload(final, source)
    assert {e['name']:e['sha256'] for e in entries} == inventories[folder]
    assert {p.name:sha(p) for p in source.iterdir()} == inventories[folder]
    report = dict(name=label, package=str(final), bytes=final.stat().st_size,
        sha256=sha(final), maps=sorted(maps), entries=entries, integrity=integrity,
        installed_source=str(source), payload_comparison='Every file byte compared to current installed source',
        target='RGH/JTAG Xbox 360; unsigned LIVE', console_runtime_test='Not performed',
        conveyor_status='Installed 3longation retained; experimental linear animation is not included')
    reports.append(report)
    (RELEASE / 'manifest.json').write_text(json.dumps(dict(
        release_date='2026-11-07', payload_bytes=payload_bytes,
        free_bytes_before=free, staging_copies=0, packages=reports), indent=2))
    print(json.dumps({k:report[k] for k in ('name','package','bytes','sha256')}), flush=True)
assert len(list(DEST.iterdir())) == 2
lines = ['# Current Xbox 360 LIVE containers', '',
    'Copy the two extensionless files below into `Content/0000000000000000/4D5307E6/00000002/` on the Xbox 360 storage device.', '',
    'Target: RGH/JTAG. These are unsigned LIVE test packages. Console loading/gameplay still requires testing.', '',
    'Use these in place of older custom-map bundles containing the same maps; do not keep duplicate versions installed. Stock DLC is separate.', '']
for r in reports:
    lines += [f"- **{r['name']}**: `{Path(r['package']).name}` ({r['bytes']:,} bytes)",
              '  Maps: ' + ', '.join(r['maps']) + '.']
lines += ['', 'All packaged bytes, directory chains and STFS hash trees were verified. Original metadata and thumbnails retained.',
    'Includes the installed Sanctuary, Chiron, Powerhouse, Resuscitation, Rodentia and Sky Bridge corrections. Rodentia retains restored source exposure. The pending experimental 3longation conveyor fix is not included.',
    'No duplicate payload directory or ZIP was created. Compact verification details are in manifest.json.']
(RELEASE / 'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
