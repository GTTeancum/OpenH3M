"""Package the current verified installation as one unsigned LIVE file per map."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from build_dlc_live import build
from verify_dlc_stfs import verify, verify_payload
from console_cache_limits import require_console_sizes

RELEASE = ROOT / '.local/releases/current-live-per-map'
DEST = RELEASE / 'Content/0000000000000000/4D5307E6/00000002'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest_path = ROOT / '.local/releases/current-live/manifest.json'
    baseline = manifest_path.read_bytes()
    current = json.loads(baseline)
    assert not RELEASE.exists(), 'Inspect the existing per-map release before replacing it'
    inventory = []
    for bundle in current['packages']:
        source = Path(bundle['installed_source']).resolve(strict=True)
        assert source.is_relative_to(ROOT / 'work/dlc/installed-corrections')
        assert sha(Path(bundle['package'])) == bundle['sha256']
        expected = {e['name']: e['sha256'] for e in bundle['entries']}
        assert {p.name: sha(p) for p in source.iterdir()} == expected
        for name in bundle['maps']:
            info = (source / (name + '.mapinfo')).read_bytes()
            title = info[0x44:0x84].decode('utf-16-be').split('\0')[0]
            preview = info[0xF44:0x1044].split(b'\0')[0].decode('ascii')
            assert preview and not any(c in preview for c in '/\\:')
            names = [name + '.map', name + '.mapinfo']
            names += [preview + suffix + '.blf' for suffix in ('', '_sm', '_clip', '_film', '_variant')]
            inventory.append((bundle, source, name, title, {n: expected[n] for n in names}))
    assert len({item[2] for item in inventory}) == len(inventory)
    # This is a console export, unlike the general host/DLC builder. Enforce
    # the real cache limits before creating any release directories or files.
    require_console_sizes(source / (name + '.map') for _, source, name, _, _ in inventory)
    total = sum(sum((source / n).stat().st_size for n in files) for _, source, _, _, files in inventory)
    assert shutil.disk_usage(ROOT).free > total * 1.05 + 100 * 1024**2
    DEST.mkdir(parents=True)
    staging = RELEASE / '.staging'
    staging.mkdir()
    reports = []
    for bundle, source, name, title, expected in inventory:
        stage = staging / name
        stage.mkdir()
        for n in expected:
            os.link(source / n, stage / n)
        if bundle['maps'] == [name]:
            # Reuse the already-current single-map container without duplicating storage.
            final = DEST / Path(bundle['package']).name
            os.link(bundle['package'], final)
        else:
            result = build(stage, DEST / ('building-' + name))
            path = Path(result['package'])
            with path.open('r+b') as stream:
                header = bytearray(stream.read(0xB000))
                assert header[:4] == b'LIVE'
                for locale in range(9):
                    for offset, value in ((0x411, title), (0xD11, title + '; current installed map. Unsigned RGH/JTAG test package.')):
                        encoded = value.encode('utf-16-be')
                        assert len(encoded) + 2 <= 256
                        at = offset + locale * 256
                        header[at:at + 256] = encoded.ljust(256, b'\0')
                header[0x32C:0x340] = hashlib.sha1(header[0x344:]).digest()
                stream.seek(0)
                stream.write(header)
            final = path.with_name(header[0x32C:0x340].hex().upper())
            assert not final.exists()
            path.rename(final)
        with final.open('rb') as stream:
            integrity = verify(stream)
        entries = verify_payload(final, stage)
        assert {e['name']: e['sha256'] for e in entries} == expected
        assert {n: sha(source / n) for n in expected} == expected
        reports.append(dict(name=title, map=name, package=str(final), content_id=final.name,
                            bytes=final.stat().st_size, sha256=sha(final), entries=entries,
                            integrity=integrity, source_bundle=bundle['sha256'],
                            installed_source=str(source), console_runtime_test='Not performed'))
        assert stage.resolve().parent == staging.resolve()
        for p in stage.iterdir():
            assert p.name in expected
            p.unlink()
        stage.rmdir()
        print(f'Verified {title}: {final.name}', flush=True)
    staging.rmdir()
    assert manifest_path.read_bytes() == baseline
    assert len(list(DEST.iterdir())) == len(inventory)
    report = dict(release_date='2026-11-12', target='RGH/JTAG Xbox 360; unsigned LIVE',
                  source_manifest_sha256=hashlib.sha256(baseline).hexdigest(), packages=reports)
    (RELEASE / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    shutil.copy2(ROOT / 'tools/warlock-conversion/MAP-CREDITS.md', RELEASE / 'SOURCE-CREDITS.md')
    lines = ['# Xbox 360 per-map LIVE packages — November 12, 2026', '',
             'One package per current installed map. Copy the 12 extensionless files from',
             '`Content/0000000000000000/4D5307E6/00000002/` into the matching folder on Xbox 360 storage.', '',
             'Use with the project\'s RGH/JTAG-compatible Halo 3 setup. These unsigned packages are not retail-signed.',
             'Replace older custom packages containing these maps; do not install these alongside the combined custom-map bundles. Keep stock DLC.', '',
             'All 84 payloads byte-compared with the current installation; all 12 STFS header/data/hash trees verified.',
             'Current map corrections are preserved, including the Powerhouse and Sky Bridge Battle Rifle fixes.',
             'Console loading/gameplay and system-link are awaiting the user\'s hardware test.', '',
             '| Map | Package filename | MiB |', '| --- | --- | ---: |']
    lines += [f"| {r['name']} | `{r['content_id']}` | {r['bytes'] / 2**20:.1f} |" for r in reports]
    lines += ['', 'Saved Forge layouts are profile-bound saved content and are not included in these LIVE map packages.',
              'Source-map authorship and package links: SOURCE-CREDITS.md. Xbox 360/OpenH3M adaptation by this project.',
              'Full file hashes and integrity results: manifest.json. Installed maps and the existing combined release were not modified.']
    (RELEASE / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Complete: {len(reports)} packages, {sum(r["bytes"] for r in reports):,} bytes', flush=True)


if __name__ == '__main__':
    main()
