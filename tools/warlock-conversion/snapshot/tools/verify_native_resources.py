"""Read-only comparison of converted native sound packets against disc donors."""
import argparse
import hashlib
import json
from pathlib import Path
from cache_reader import Cache
from resource_reader import Resource


def sound_data(cache, index, shared):
    at = cache.tags[index]['offset']
    datum = cache.u(at + 24)
    resource = Resource(cache, datum, shared)
    zone = next(t['offset'] for t in cache.tags.values() if t['group'] == 'zone')
    play = next(t['offset'] for t in cache.tags.values() if t['group'] == 'play')
    row = cache.block(zone + 88, 64)[datum & 65535]
    location = cache.block(play + 48, 16)[cache.unpack('h', row + 34)[0]]
    tables = cache.block(play + 36, 16)
    parts = []
    for slot, table in enumerate(cache.unpack('hh', location + 12)):
        if table < 0:
            continue
        cursor = 0
        for item in cache.block(tables[table] + 4, 8):
            offset, size = cache.unpack('II', item)
            data = resource.raw[slot][cursor:cursor + size]
            if len(data) != size:
                raise ValueError('Truncated sound streaming segment')
            parts.append((offset, data))
            cursor += size
    output = bytearray(max((offset + len(data) for offset, data in parts), default=0))
    for offset, data in parts:
        output[offset:offset + len(data)] = data
    ugh = next(t['offset'] for t in cache.tags.values() if t['group'] == 'ugh!')
    codec = cache.block(ugh, 3)[cache.unpack('h', at + 4)[0]]
    return bytes(cache.data[codec:codec + 3]), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--disc-maps', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if hashlib.sha256(args.map.read_bytes()).hexdigest() != report['output_sha256']:
        raise ValueError('Map does not match its build report')
    shared = {f'maps\\{name}': args.disc_maps / name for name in ('shared.map', 'mainmenu.map')}
    target = Cache(args.map)
    checked = 0
    try:
        for item in report['sounds']:
            if item['encoding'] != 'native retail':
                continue
            donor = Cache(args.disc_maps / item['donor'])
            try:
                index = next(i for i, t in donor.tags.items()
                             if t['group'] == 'snd!' and donor.name(i) == item['source'])
                original = sound_data(donor, index, shared)
                converted = sound_data(target, int(item['datum'], 16) & 65535, shared)
                if original != converted:
                    raise ValueError('Native codec/packet mismatch: ' + item['source'])
                checked += 1
            finally:
                donor.close()
    finally:
        target.close()
    print(json.dumps({'native_sounds_verified': checked, 'codec_and_packets_identical': True}))


if __name__ == '__main__':
    main()
