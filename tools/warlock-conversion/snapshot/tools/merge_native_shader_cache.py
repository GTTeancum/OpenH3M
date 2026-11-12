"""Merge recorded native shader/pipeline caches for startup preparation.

No synthesized pipelines, shader edits or gameplay changes. Layouts follow
ReXGlue D3D12 PipelineCache's packed ShaderStoredHeader and PipelineDescription.
Only repository-local inputs/outputs are accepted; never overwrite a live cache.
"""
import argparse
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[4]


def confined(path):
    path = path.resolve()
    path.relative_to(ROOT)
    return path


def merge(sources, output):
    output = confined(output)
    if output.exists():
        raise ValueError('Use a fresh output directory')
    result, assembled = {}, {}
    for name, header_size in [('4D5307E6.xsh', 8), ('4D5307E6.rtv.d3d12.xpso', 12)]:
        header, records, incomplete_tails = None, {}, []
        for source in sources:
            data = (confined(source) / 'shaders/shareable' / name).read_bytes()
            if header is None:
                header = data[:header_size]
            if data[:header_size] != header or header[:4] != (b'XESH' if header_size == 8 else b'XEPS'):
                raise ValueError('Incompatible native cache header')
            at = header_size
            while at < len(data):
                if len(data) - at < 12:
                    incomplete_tails.append({'source': str(source), 'bytes': len(data)-at})
                    break
                size = (12 + 4 * (struct.unpack_from('<I', data, at + 8)[0] & 0x7fffffff)
                        if header_size == 8 else 72)
                row = data[at:at+size]
                if len(row) != size:
                    # A watchdog can interrupt the writer. Match the runtime's
                    # valid-prefix recovery without changing the input cache.
                    incomplete_tails.append({'source': str(source), 'bytes': len(data)-at})
                    break
                key = row[:8]
                if key in records and records[key] != row:
                    raise ValueError('Conflicting cache hash')
                records[key] = row
                at += size
        assembled[name] = header + b''.join(records.values())
        result[name] = {'records': len(records), 'bytes': len(assembled[name]),
                        'incomplete_tails_excluded': incomplete_tails}
    destination = output / 'shaders/shareable'
    destination.mkdir(parents=True)
    for name, data in assembled.items():
        (destination / name).write_bytes(data)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report = merge(args.source, args.output)
    confined(args.report).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
