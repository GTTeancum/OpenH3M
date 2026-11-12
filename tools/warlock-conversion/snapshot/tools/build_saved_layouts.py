"""Package native Forge layouts as unsigned, profile-bound CON test saves."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from build_dlc_live import build, confined


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', type=Path, action='append', required=True)
    parser.add_argument('--profile-id', required=True, help='16-digit destination profile ID in hexadecimal')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.profile_id) != 16:
        parser.error('Profile ID must have 16 hex digits')
    profile = int(args.profile_id, 16)
    output = confined(args.output)
    if output.exists():
        raise ValueError('Use a new output directory; never overwrite installed saves')
    prepared = []
    for source in args.layout:
        source = confined(source)
        data = source.read_bytes()
        report = json.loads(source.with_suffix('.json').read_text())
        if hashlib.sha256(data).hexdigest() != report['sha256']:
            raise ValueError('Layout differs from conversion report')
        if (data[:4] != b'_blf' or data[0x30:0x34] != b'chdr' or
                struct.unpack_from('>i', data, 0x40 + 184)[0] != 10):
            raise ValueError('Not a native Mythic saved map layout')
        prepared.append((source.stem, data, report))
    if len({p[0] for p in prepared}) != len(prepared):
        raise ValueError('Duplicate layout names')
    output.mkdir(parents=True)
    packages = []
    for stem, data, report in prepared:
        payload = output/'payloads'/stem
        payload.mkdir(parents=True)
        (payload/'sandbox.map').write_bytes(data)
        package = build(payload, output/'packages'/stem,
                        saved_profile=profile, saved_name=report['name'])
        package.update(name=report['name'], home=report['home'],
                       payload=str(payload),
                       required_map_sha256=report['map_sha256'])
        packages.append(package)
        print(f"{report['name']}: {package['bytes']:,} bytes")
    (output/'manifest.json').write_text(json.dumps(packages, indent=2)+'\n')


if __name__ == '__main__':
    main()
