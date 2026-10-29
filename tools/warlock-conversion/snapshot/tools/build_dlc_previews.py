"""Convert installed MCC map artwork to native H3 mapi BLFs, atomically.

Only artwork/metadata changes; map caches are never opened for writing.
Requires the version-checked mapi SHA1 adapter in patch_dlc_xex.py.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import struct
from PIL import Image, ImageOps
from build_dlc_payload import fixed

ROOT = Path(__file__).resolve().parents[4]
SOURCES = {
    'warlock': '2977651586/images/warlock_thumbnail.png',
    'resuscitation': '2898876653/images/resus-large.png',
    'prisoner': '2962955878/images/Prisoner.png',
    'forge_gulch': '3597611181/images/image large.png',
    'forge_island': '3597611181/images/image large.png',
}
# Dimensions measured from every matching Heroic Map Pack preview variant.
VARIANTS = {'': (463, 152), '_sm': (463, 152), '_clip': (256, 141),
            '_film': (256, 141), '_variant': (182, 100)}


def atomic(path, data):
    if not path.resolve().is_relative_to(ROOT):
        raise ValueError('Output must stay inside repository')
    pending = path.with_name(path.name + '.pending')
    with pending.open('xb') as f:
        f.write(data)
    os.replace(pending, path)  # Break existing staging/installation hardlinks.


def blf(jpeg):
    header = struct.pack('>4sIHHH', b'_blf', 48, 1, 2, 0xfffe) + bytes(34)
    data = header + struct.pack('>4sIHHII', b'mapi', len(jpeg)+20, 1, 1, 0, len(jpeg)) + jpeg
    # Native type-2 SHA1 EOF uses a 256-byte authentication field: digest + zeros.
    return data + struct.pack('>4sIHHIB', b'_eof', 273, 1, 1, len(data), 2) + hashlib.sha1(data).digest() + bytes(236)


def build(workshop, payload, names=None, images=None):
    report = {'authentication': 'native SHA1 EOF; requires custom-content adapter', 'maps': []}
    for name, relative in SOURCES.items():
        if (names is not None and name not in names) or not (payload / (name + '.mapinfo')).exists():
            continue
        source = (images or {}).get(name, workshop / relative)
        with Image.open(source) as opened:
            original = opened.convert('RGB')
        files = []
        for suffix, size in VARIANTS.items():
            picture = ImageOps.fit(original, size, method=Image.Resampling.LANCZOS)
            stream = io.BytesIO()
            picture.save(stream, format='JPEG', quality=90, progressive=False, optimize=False)
            data = blf(stream.getvalue())
            path = payload / ('dlc_' + name + suffix + '.blf')
            atomic(path, data)
            files.append(dict(file=path.name, size=list(size), bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        metadata = payload / (name + '.mapinfo')
        info = bytearray(metadata.read_bytes())
        if len(info) != 20113 or info[0x30:0x34] != b'levl':
            raise ValueError('Unexpected mapinfo layout')
        fixed(info, 0xf44, 256, 'dlc_' + name)
        atomic(metadata, info)
        report['maps'].append(dict(name=name, source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), files=files))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workshop', type=Path, required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = build(args.workshop, args.payload)
    atomic(args.report, (json.dumps(report, indent=2)+'\n').encode())
    print(f"Built {sum(len(row['files']) for row in report['maps'])} native previews for {len(report['maps'])} maps.")
