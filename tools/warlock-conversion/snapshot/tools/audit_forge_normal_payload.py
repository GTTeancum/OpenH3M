"""Read back three rock normal maps from the serialized retail candidate."""
import argparse
import hashlib
import json
from pathlib import Path

from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from resource_reader import Resource
from xbox_bitmap import untile_base


def audit(source_path, candidate_path):
    source, candidate = Cache(source_path, True), Cache(candidate_path)
    try:
        bitmaps = BitmapSource(source)
        expected = {}
        for index, tag in source.tags.items():
            name = source.name(index) or ''
            if tag['group'] != 'bitm' or not name.endswith((
                    'forge_halo_rocks_2dblend_normal', 'forge_halo_rocks_lichen_normal',
                    'forge_halo_rocks_smooth_normal')):
                continue
            info = bitmaps.info(index)[0]
            assert info['format'] == 33
            data, width, height = bitmaps.pixels(index), info['width'], info['height']
            while max(width, height) > 512:
                data = data[((width+3)//4)*((height+3)//4)*16:]
                width, height = max(1, width//2), max(1, height//2)
            data = bytearray(data[:((width+3)//4)*((height+3)//4)*16])
            # Independent scalar expression; don't call the production converter.
            for block in range(0, len(data), 16):
                for offset in (0, 1, 8, 9):
                    data[block+offset] = (data[block+offset]+128) % 256
            expected[hashlib.sha256(data).hexdigest()] = name
        if len(expected) != 3:
            raise ValueError('Expected three distinct source rock normal textures')
        found, pages = [], {}
        for index, tag in candidate.tags.items():
            if tag['group'] != 'bitm' or candidate.name(index) is not None:
                continue  # Generated custom tags have no original debug name.
            rows = candidate.block(tag['offset']+0x60, 48)
            hardware = candidate.block(tag['offset']+0x8c, 8)
            for row, entry in zip(rows, hardware):
                if candidate.unpack('H', row+12)[0] != 33:
                    continue
                resource = Resource(candidate, candidate.u(entry), decoded_pages=pages)
                width, height = candidate.unpack('HH', row+4)
                data = untile_base(resource.raw[0], width, height, 33)
                digest = hashlib.sha256(data).hexdigest()
                if digest in expected:
                    gpu = resource.unpack('I', 48)[0]
                    if gpu != 0x1a215571:
                        raise ValueError('Rock normal fetch differs from original-disc DXN')
                    found.append({'source': expected[digest], 'candidate_tag': index,
                                  'linear_sha256': digest, 'gpu_format': hex(gpu)})
        if {row['source'] for row in found} != set(expected.values()):
            raise ValueError('Not all source rock normal payloads found in candidate')
        return found
    finally:
        source.close()
        candidate.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source, args.candidate)
    args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
