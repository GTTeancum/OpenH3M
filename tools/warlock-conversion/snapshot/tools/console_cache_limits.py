"""Original Mythic cache-size gate; passing this is not console validation.

In the original executable, 821B0DD0 calls 82206388 with header.cache_type.
82206388's jump table at 822063B0 selects these limits when the disk cache
is available. With caching unavailable it instead returns INT32_MAX, which
is why a successful extracted-file host load does not exercise this gate.
The multiplayer cache slots 3..12 also have capacity 0x09600000 in the
82206030 table at 820398D8. Do not increase limits to make an export pass.
"""
import struct
from pathlib import Path

MYTHIC_CACHE_LIMITS = (0x1F400000, 0x09600000, 0x04100000,
                       0x0BE00000, 0x22600000)


def inspect_map(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as stream:
        header = stream.read(0x3000)
    if len(header) != 0x3000 or header[:4] != b'head' or header[-4:] != b'foot':
        raise ValueError(f'Not a native cache file: {path.name}')
    version, declared = struct.unpack_from('>II', header, 4)
    kind = struct.unpack_from('>h', header, 0x13C)[0]
    if version != 11 or not 0 <= kind < len(MYTHIC_CACHE_LIMITS):
        raise ValueError(f'Unsupported cache version/type: {path.name}')
    if declared != size:
        raise ValueError(f'Cache file length differs from header: {path.name}')
    limit = MYTHIC_CACHE_LIMITS[kind]
    return dict(map=path.name, cache_type=kind, file_bytes=size,
                cached_console_limit_bytes=limit, within_limit=size <= limit,
                excess_bytes=max(0, size-limit),
                scope='Original Mythic cached-file size gate only; not hardware acceptance')


def require_console_sizes(paths):
    reports = [inspect_map(p) for p in paths]
    failures = [r for r in reports if not r['within_limit']]
    if failures:
        details = '; '.join(f"{r['map']}: {r['file_bytes']} > {r['cached_console_limit_bytes']} bytes"
                            for r in failures)
        raise ValueError('Xbox 360 cache size limit exceeded; export stopped: ' + details)
    return reports
