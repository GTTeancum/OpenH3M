"""Package an accepted Sky Bridge payload as standalone Xbox 360 LIVE DLC."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zipfile

from cache_reader import Cache
from build_dlc_live import build, confined
from verify_dlc_stfs import verify, verify_payload


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def package(payload, release, expected, launch_report):
    payload, release, launch_report = map(confined, (payload, release, launch_report))
    names = {'sky_bridge.map', 'sky_bridge.mapinfo'} | {
        'dlc_sky_bridge' + suffix + '.blf'
        for suffix in ('', '_sm', '_clip', '_film', '_variant')}
    if {p.name for p in payload.iterdir() if p.is_file()} != names:
        raise ValueError('Expected only Sky Bridge map, mapinfo and five previews')
    if digest(payload / 'sky_bridge.map') != expected:
        raise ValueError('Payload map differs from selected launch-tested map')
    cache = Cache(payload / 'sky_bridge.map')
    try:
        scenarios = [t for t in cache.tags.values() if t['group'] == 'scnr']
        if (len(scenarios) != 1 or cache.u(scenarios[0]['offset'] + 8) != 1747
                or bytes(cache.data[0x18C:0x1AC]).split(b'\0')[0] != b'sky_bridge'):
            raise ValueError('Map does not have the Sky Bridge DLC identity')
    finally:
        cache.close()
    info = (payload / 'sky_bridge.mapinfo').read_bytes()
    if (len(info) != 20113 or info[0x30:0x34] != b'levl'
            or struct.unpack_from('>I', info, 0x3C)[0] != 1747):
        raise ValueError('Mapinfo does not have the Sky Bridge DLC identity')
    evidence = launch_report.read_bytes()
    if not evidence:
        raise ValueError('Launch report is empty')
    if release.exists():
        raise ValueError('Release directory already exists')
    release.mkdir(parents=True)
    staged = release / 'payload'
    staged.mkdir()
    for name in sorted(names):
        shutil.copyfile(payload / name, staged / name)
    if digest(staged / 'sky_bridge.map') != expected:
        raise ValueError('Map changed during staging')
    destination = release / 'Content/0000000000000000/4D5307E6/00000002'
    result = build(staged, destination / 'SkyBridgeFinal')
    container = Path(result['package'])
    with container.open('r+b') as stream:
        header = bytearray(stream.read(0xB000))
        if header[:4] != b'LIVE':
            raise ValueError('Expected LIVE container')
        def label(offset, size, value):
            encoded = value.encode('utf-16-be')
            if len(encoded) + 2 > size:
                raise ValueError('Container label too long')
            header[offset:offset + size] = encoded.ljust(size, b'\0')
        for locale in range(9):
            label(0x411 + locale * 256, 256, 'Sky Bridge')
            label(0xD11 + locale * 256, 256,
                  'Sky Bridge for Halo 3. Xbox 360 / OpenH3M adaptation.')
        label(0x1611, 128, 'General Heed / Priception; OpenH3M adaptation')
        header[0x32C:0x340] = hashlib.sha1(header[0x344:]).digest()
        stream.seek(0)
        stream.write(header)
    final = container.with_name(header[0x32C:0x340].hex().upper())
    if final != container:
        if final.exists():
            raise ValueError('Final content ID already exists')
        container.rename(final)
    with final.open('rb') as stream:
        integrity = verify(stream)
    entries = verify_payload(final, staged)
    if {entry['name'] for entry in entries} != names:
        raise ValueError('Unexpected packaged files')
    if next(e['sha256'] for e in entries if e['name'] == 'sky_bridge.map') != expected:
        raise ValueError('Packaged map changed')
    archive = release / 'Sky-Bridge-LIVE-DLC.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as output:
        output.write(final, final.relative_to(release).as_posix())
    with zipfile.ZipFile(archive) as zipped:
        if len(zipped.infolist()) != 1:
            raise ValueError('Archive must contain one LIVE container')
        with zipped.open(zipped.infolist()[0]) as stream:
            zip_integrity = verify(stream)
    (release / 'launch-report.json').write_bytes(evidence)
    manifest = dict(name='Sky Bridge', format='LIVE/STFS', title_id='4D5307E6',
                    content_type='00000002', package=str(final), zip=str(archive),
                    content_id=final.name, sha256=digest(final), zip_sha256=digest(archive),
                    map_sha256=expected, entries=entries, integrity=integrity,
                    zip_integrity=zip_integrity, launch_report_sha256=hashlib.sha256(evidence).hexdigest(),
                    unsigned=True, target='OpenH3M and RGH/JTAG Xbox 360',
                    installed=False, pushed=False,
                    credits=dict(original='Sky Bridge, Halo Online',
                                 package='Halo Online Map Pack For Halo 3',
                                 authors=['General Heed', 'Priception'],
                                 url='https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190',
                                 adaptation='This project supplies the Xbox 360/OpenH3M adaptation.'))
    (release / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (release / 'README.txt').write_text(
        'SKY BRIDGE - LIVE DLC FOR USER PLAYTEST\n\n'
        'Extract Sky-Bridge-LIVE-DLC.zip at the content-storage root. It contains:\n'
        + final.relative_to(release).as_posix() + '\n\n'
        'Native LIVE/STFS container, unsigned for OpenH3M and RGH/JTAG Xbox 360.\n'
        'Includes Sky Bridge, map information and five previews. No files installed.\n'
        'See launch-report.json for the actual scope and outcome of the launch test.\n\n'
        'Source: Sky Bridge, Halo Online; General Heed / Priception,\n'
        'Halo Online Map Pack For Halo 3:\n'
        'https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190\n'
        'This project supplies the Xbox 360/OpenH3M adaptation.\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', required=True, type=Path)
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--map-sha256', required=True)
    parser.add_argument('--launch-report', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.payload, args.release, args.map_sha256,
                             args.launch_report), indent=2))
