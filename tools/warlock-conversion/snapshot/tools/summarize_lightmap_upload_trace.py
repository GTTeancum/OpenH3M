"""Summarize observed CPU lightmap vectors and GPU pixel constants in a draw trace.

CPU preparation and GPU submission are asynchronous. Their simultaneous snapshots
are not a per-command correspondence. Transitions refer to GPU draw order only.
"""
import argparse
import gzip
import json
import struct
from pathlib import Path

STRIDE = 0x5003 * 4
CONSTANT_OFFSET = (0x4000 + (256 + 210) * 4) * 4


def summarize(run):
    events = [json.loads(line) for line in (run / 'loading-trace.jsonl').read_text().splitlines()]
    draws = [event for event in events if event['event'] == 'draw']
    snapshots, transitions = [], []
    previous = None
    with gzip.open(run / 'draw-registers.bin.gz', 'rb') as stream:
        for draw in draws:
            state = stream.read(STRIDE)
            if len(state) != STRIDE:
                raise ValueError('Truncated draw-register evidence')
            values = list(struct.unpack_from('<12f', state, CONSTANT_OFFSET))
            pixel = draw['shaders'][1]
            shader_hash = hex(struct.unpack_from('<Q', bytes.fromhex(pixel), 40)[0]) if pixel else None
            identity = dict(sample=draw['sample'], index_count=draw['index_count'], pixel_hash=shader_hash)
            if values != previous:
                transitions.append(dict(**identity, gpu_c210_212=values))
                previous = values
            if 'lightmap_upload_state' in draw:
                cpu = draw['lightmap_upload_state']
                snapshots.append(dict(**identity, device=cpu['device'],
                                      cpu_vectors=cpu['vectors'], gpu_c210_212=values,
                                      cpu_dirty_flags=cpu['dirty_flags'],
                                      simultaneous_values_equal=cpu['vectors'] == values))
        if stream.read(1):
            raise ValueError('Unpaired draw-register evidence')
    if not snapshots:
        raise ValueError('No CPU upload snapshots in this trace')
    return dict(run=str(run), draw_count=len(draws), snapshots=snapshots,
                gpu_transitions=transitions,
                errors=[e for e in events if e['event'] in ('error', 'exception') or 'lightmap_upload_error' in e],
                exits=[e for e in events if e['event'] == 'exit'],
                hash_summary=[e for e in events if e['event'] == 'hash_summary'],
                scope=__doc__.strip())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.run), indent=2))
