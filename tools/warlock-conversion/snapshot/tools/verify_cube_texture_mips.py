"""Verify every face and mip of an unchanged-size native cube against MCC source."""
import argparse
import json
from pathlib import Path
import numpy as np
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from resource_reader import Resource
from xbox_mip_chain import cube_layout


def verify(source, candidate, source_bitmap, target_bitmap):
    original, native = Cache(source, True), Cache(candidate)
    try:
        bitmaps = BitmapSource(original)
        info = bitmaps.info(source_bitmap)[0]
        source_row = original.block(original.tags[source_bitmap]['offset'] + 96, 56)[0]
        if original.unpack('H', source_row + 10)[0] != 2:
            raise ValueError('Source is not a cube')
        root = native.tags[target_bitmap]['offset']
        images = native.block(root + 96, 48)
        if len(images) != 1:
            raise ValueError('Expected a single native cube image')
        row = images[0]
        width, height = native.unpack('HH', row + 4)
        kind, fmt = native.unpack('HH', row + 10)
        count = native.data[row + 20] + 1
        if (width, height, kind, fmt, count) != (info['width'], info['height'], 2, info['format'], info['mips']):
            raise ValueError('Native cube dimensions, format or complete mip chain differ')
        if fmt not in (11, 14, 15, 16):
            raise ValueError('Unsupported cube format')
        resource = Resource(native, native.u(native.block(root + 140, 8)[0]))
        if resource.unpack('HHBBB', 40) != (width, height, 1, count, 2):
            raise ValueError('Native cube resource metadata differs')
        expected = bitmaps.pixels(source_bitmap)
        faces, size = cube_layout(width, count, fmt)
        raw = np.frombuffer(resource.raw[0], dtype=np.uint8)
        if len(raw) < size:
            raise ValueError('Native cube resource truncated')
        block = 4 if fmt == 11 else 8 if fmt == 14 else 16
        endian = 4 if fmt == 11 else 2
        consumed, checks = 0, []
        for face, levels in enumerate(faces):
            for mip, (positions, length) in enumerate(levels):
                decoded = raw[positions.reshape(-1, 1) + np.arange(block)]
                decoded = decoded.reshape(-1, endian)[:, ::-1].tobytes()
                equal = len(decoded) == length and decoded == expected[consumed:consumed + length]
                checks.append(dict(face=face, mip=mip, bytes=length, exact=equal))
                consumed += length
        if consumed != len(expected):
            raise ValueError('Source cube payload extends beyond authored mip chain')
        return dict(source=str(source), candidate=str(candidate), source_bitmap=source_bitmap,
                    target_bitmap=target_bitmap, width=width, mip_count=count, checks=checks,
                    passed=all(x['exact'] for x in checks),
                    scope='Decoded source/native cube payload comparison; does not prove live sampling.')
    finally:
        original.close()
        native.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--source-bitmap-index', type=int, required=True)
    parser.add_argument('--target-bitmap-index', type=int, required=True)
    args = parser.parse_args()
    result = verify(args.source, args.candidate, args.source_bitmap_index, args.target_bitmap_index)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
