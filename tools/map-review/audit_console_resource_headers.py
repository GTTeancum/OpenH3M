"""Reconstruct native optimized-page reads without changing installed maps."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from build_scenario_checkpoint import resource_salt


def audit(path, salt):
    with path.open('rb') as stream:
        h = stream.read(0x3000)
        if not h[0x142]:
            return dict(path=str(path), map=path.name, optimized_header_enabled=False,
                        pages=[], invalid_enabled_pages=0)
        raw_start = sum(struct.unpack_from('>I', h, at)[0] for at in (0x484, 0x470)) & 0xffffffff
        count = struct.unpack_from('>H', h, 0x4ae)[0]
        offset = struct.unpack_from('>I', h, 0x4b0)[0]
        if count > 320:
            raise ValueError('Optimized records exceed header capacity')
        pages = []
        for i in range(count):
            at = 0x4c4 + i * 28
            packed, decoded_size = struct.unpack_from('>II', h, at)
            compressed, flags = packed >> 2, packed & 3
            expected = h[at+8:at+28].hex()
            row = dict(index=i, offset=offset, compressed_bytes=compressed,
                       decoded_bytes=decoded_size, flags=flags, expected_sha1=expected)
            stream.seek(raw_start+offset)
            data = stream.read(compressed)
            try:
                if len(data) != compressed:
                    raise ValueError('Truncated page')
                if flags & 1:
                    data = zlib.decompress(data, -15)
                actual = hashlib.sha1(salt+data).hexdigest()
                row.update(actual_decoded_bytes=len(data), actual_sha1=actual,
                           valid=len(data) == decoded_size and actual == expected)
            except (ValueError, zlib.error) as exc:
                row.update(valid=False, decode_error=str(exc))
            pages.append(row)
            offset += (compressed+4095) & ~4095
    return dict(path=str(path), map=path.name, optimized_header_enabled=bool(h[0x142]),
                pages=pages, invalid_enabled_pages=sum(not p['valid'] for p in pages) if h[0x142] else 0)


if __name__ == '__main__':
    salt = resource_salt(ROOT / '../../default.xex')
    manifest = json.loads((ROOT/'.local/releases/current-live/manifest.json').read_text())
    sources = [Path(b['installed_source'])/(name+'.map') for b in manifest['packages'] for name in b['maps']]
    reports = [audit(p, salt) for p in sorted(sources)]
    output = ROOT/'work/elongation-console-diagnostic/all-map-optimized-headers.json'
    output.write_text(json.dumps(reports, indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('map','optimized_header_enabled','invalid_enabled_pages')} for r in reports], indent=2))
