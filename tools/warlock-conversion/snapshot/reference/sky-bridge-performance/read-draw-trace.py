"""Decode actual SkyDrawTrace packets. No inference of visible pixel correctness."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


def decode(path):
    registers = [0] * 0x5003
    seen = set()
    frames = Counter()
    changed = Counter()
    shaders = {}
    draws = []
    prefixes = []
    pending_shader = pending_prefix = current = None
    completion = None
    packets = Counter()
    with path.open('rb') as stream:
        while header := stream.read(8):
            if len(header) != 8:
                raise ValueError('Truncated packet header')
            kind, length = struct.unpack('<II', header)
            if length > 0x100000:
                raise ValueError('Invalid packet size')
            data = stream.read(length)
            if len(data) != length:
                raise ValueError('Truncated packet body')
            packets[kind] += 1
            if kind == 0:
                assert struct.unpack('<II', data) == (1, 0x5003)
            elif kind == 1:
                row = struct.unpack('<11Q', data)
                current = dict(zip(('sequence', 'frame', 'nanoseconds', 'vs', 'ps',
                    'primitive', 'index_count', 'index_address', 'index_length',
                    'index_format', 'index_endian'), row))
                current['emitted'] = False
                draws.append(current)
                frames[current['frame']] += 1
            elif kind == 2:
                assert current is not None and length % 8 == 0
                current['register_changes'] = []
                for index, value in struct.iter_unpack('<II', data):
                    assert index < len(registers)
                    registers[index] = value
                    seen.add(index)
                    current['register_changes'].append([index, value])
                    if len(draws) > 1:
                        changed[index] += 1
                assert len(seen) == len(registers), 'Missing initial full register state'
                current['register_state_sha256'] = hashlib.sha256(
                    struct.pack('<%dI' % len(registers), *registers)).hexdigest()
                current['fetch_words'] = registers[0x4800:0x48c0]
            elif kind == 3:
                pending_shader = struct.unpack('<QQ', data)
            elif kind == 4:
                assert pending_shader is not None and length % 4 == 0
                shader_id, shader_type = pending_shader
                shaders[shader_id] = {'type': shader_type, 'dwords': length // 4,
                    'host_endian_sha256': hashlib.sha256(data).hexdigest(),
                    'guest_endian_sha256': hashlib.sha256(b''.join(
                        struct.pack('>I', word[0]) for word in struct.iter_unpack('<I', data))).hexdigest()}
                pending_shader = None
            elif kind == 5:
                sequence, frame = struct.unpack('<QQ', data)
                assert current and (sequence, frame) == (current['sequence'], current['frame'])
                current['emitted'] = True
            elif kind == 6:
                pending_prefix = struct.unpack('<4Q', data)
            elif kind == 7:
                assert pending_prefix and len(data) == pending_prefix[3]
                prefixes.append({'sequence': pending_prefix[0], 'address': pending_prefix[1],
                    'bound_length': pending_prefix[2], 'prefix_length': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(), 'bytes': data.hex()})
                pending_prefix = None
            elif kind == 9:
                completion, = struct.unpack('<Q', data)
            else:
                raise ValueError(f'Unknown packet {kind}')
    assert packets[0] == 1 and not pending_shader and not pending_prefix
    return {'completion_reason': completion, 'complete': completion in (1, 2, 4),
        'draw_count': len(draws), 'emitted_count': sum(d['emitted'] for d in draws),
        'frames': dict(frames), 'shaders': shaders, 'prefixes': prefixes, 'draws': draws,
        'register_change_counts': {hex(k): v for k, v in changed.items()},
        'limitations': ['CPU register state and byte prefixes; not rendered pixel evidence.',
            'Fetch candidates require shader-binding verification before geometry attribution.',
            'Diagnostic recording overhead invalidates performance comparisons.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture-check', action='store_true')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[5]
    args.output.resolve().relative_to(repo)
    report = decode(args.trace)
    if args.fixture_check:
        assert report['completion_reason'] == 1
        assert report['draw_count'] == report['emitted_count'] == 2
        assert report['frames'] == {20: 1, 21: 1}
        assert report['draws'][1]['register_changes'] == [[0x4400, 0x3f800000]]
        assert len(report['shaders']) == 1
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('complete', 'draw_count', 'emitted_count', 'frames')}))
