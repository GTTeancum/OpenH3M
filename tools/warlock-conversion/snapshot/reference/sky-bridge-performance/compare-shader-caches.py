"""Compare stored Xenos programs and D3D12 descriptions without editing caches."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def read(path, pipeline):
    data = path.read_bytes()
    if pipeline:
        if data[:8] != b'XEPSDXRT' or (len(data) - 12) % 72:
            raise ValueError('Unexpected RTV pipeline storage layout')
        header, offset = data[:12], 12
    else:
        if data[:8] != b'XESH\x20\x20\x12\x19':
            raise ValueError('Unexpected shader storage version')
        header, offset = data[:8], 8
    entries = {}
    duplicates = 0
    while offset < len(data):
        key, = struct.unpack_from('<Q', data, offset)
        size = 72 if pipeline else 12 + 4 * (struct.unpack_from('<I', data, offset + 8)[0] & 0x7fffffff)
        entry = data[offset:offset+size]
        if len(entry) != size:
            raise ValueError('Truncated storage entry')
        if key in entries:
            if entries[key] != entry:
                raise ValueError('Different payloads with the same stored key')
            duplicates += 1
        entries[key] = entry
        offset += size
    return header, entries, {'file': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
                             'bytes': len(data), 'entries': len(entries), 'duplicates': duplicates}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('replay', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[5]
    for path in (args.original, args.replay, args.output):
        path.resolve().relative_to(root)
    results = []
    for suffix, pipeline in [('xsh', False), ('rtv.d3d12.xpso', True)]:
        ha, a, ma = read(args.original / ('4D5307E6.' + suffix), pipeline)
        hb, b, mb = read(args.replay / ('4D5307E6.' + suffix), pipeline)
        if ha != hb:
            raise ValueError('Storage versions differ')
        common = a.keys() & b.keys()
        results.append({'kind': suffix, 'original': ma, 'replay': mb,
                        'shared_keys': len(common),
                        'shared_keys_with_different_bytes': [str(k) for k in sorted(common) if a[k] != b[k]],
                        'original_only_keys': [str(k) for k in sorted(a.keys()-b.keys())],
                        'replay_only_keys': [str(k) for k in sorted(b.keys()-a.keys())]})
    report = {'comparisons': results,
              'layout_evidence': 'rexglue-sdk/include/rex/graphics/d3d12/pipeline_cache.h ShaderStoredHeader, PipelineDescription, PipelineStoredDescription; src/graphics/d3d12/pipeline_cache.cpp InitializeShaderStorage',
              'limitation': 'Checks framing and exact bytes by stored key; does not independently recompute XXH3 keys. Equal common entries do not establish equal compilation timing, cache population, runtime state, or visual behavior.'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    for r in results:
        print(json.dumps({'kind': r['kind'], 'original_entries': r['original']['entries'],
                          'replay_entries': r['replay']['entries'], 'shared_keys': r['shared_keys'],
                          'different_shared_payloads': len(r['shared_keys_with_different_bytes']),
                          'replay_only_keys': len(r['replay_only_keys'])}))
