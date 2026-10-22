"""Stage distinct DLC identities; output is an unsigned test payload, not STFS."""
import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path
from cache_reader import Cache

MAPS = [('lockout', 'warlock', 'Warlock', 1520),
        ('zanzibar', 'resuscitation', 'Resuscitation', 1030),
        ('chillout', 'prisoner', 'Prisoner', 1600),
        ('sandbox', 'forge_gulch', 'Forge Gulch', 1730)]


def fixed(data, offset, length, text, encoding='ascii'):
    value = text.encode(encoding)
    terminator = 2 if encoding == 'utf-16-be' else 1
    if len(value) + terminator > length:
        raise ValueError('String too long')
    data[offset:offset+length] = value.ljust(length, b'\0')


def build(converted, stock, output):
    if output.exists():
        raise ValueError('Output exists; review/remove old staging before rebuilding')
    stock_ids = set()
    for path in (stock / 'info').glob('*.mapinfo'):
        data = path.read_bytes()
        if data[0x30:0x34] == b'levl':
            stock_ids.add(struct.unpack_from('>I', data, 0x3C)[0])
    for _, _, _, map_id in MAPS:
        if map_id in stock_ids:
            raise ValueError(f'Map ID {map_id} already used by stock content')
    output.mkdir(parents=True)
    report = {'status': 'staged, not runtime validated or signed', 'maps': []}
    for slot, name, title, map_id in MAPS:
        source = converted / (slot + '.map')
        with_source = Cache(source)
        try:
            scenarios = [t for t in with_source.tags.values() if t['group'] == 'scnr']
            if len(scenarios) != 1:
                raise ValueError('Expected one scenario')
            scenario_offset = scenarios[0]['offset']
            old_id = with_source.u(scenario_offset + 8)
            header_name = with_source.data[0x18C:0x1AC].split(b'\0')[0]
            if header_name != slot.encode():
                raise ValueError('Unexpected source identity')
        finally:
            with_source.close()
        dest = output / (name + '.map')
        shutil.copyfile(source, dest)
        with dest.open('r+b') as stream:
            header = bytearray(stream.read(0x3000))
            fixed(header, 0x18C, 32, name)
            fixed(header, 0x1B0, 256, 'levels\\dlc\\' + name + '\\' + name)
            stream.seek(0)
            stream.write(header)
            stream.seek(scenario_offset + 8)
            stream.write(struct.pack('>I', map_id))
        info = bytearray((stock / 'info' / (slot + '.mapinfo')).read_bytes())
        if info[0x30:0x34] != b'levl' or info[0x4D80:0x4D84] != b'_eof':
            raise ValueError('Unexpected retail mapinfo layout')
        if struct.unpack_from('>I', info, 0x3C)[0] != old_id:
            raise ValueError('Scenario and mapinfo identity mismatch')
        struct.pack_into('>I', info, 0x3C, map_id)
        flags = struct.unpack_from('>I', info, 0x40)[0]
        struct.pack_into('>I', info, 0x40, flags | 0x80)
        for locale in range(12):
            fixed(info, 0x44 + locale*64, 64, title, 'utf-16-be')
            fixed(info, 0x344 + locale*256, 256,
                  title + ' - custom Halo 3 map.', 'utf-16-be')
        # Reuse existing stock preview initially; replace with native custom captures
        # before release. This remains explicit in the output manifest.
        fixed(info, 0x1044, 256, name)
        # Changed data cannot retain the stock RSA signature. Native BLF supports
        # authentication type None; acceptance by this game is a required test.
        info[0x4D80:] = struct.pack('>4sIHHIB', b'_eof', 17, 1, 1, 0x4D80, 0)
        (output / (name + '.mapinfo')).write_bytes(info)
        with dest.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        report['maps'].append(dict(name=name, title=title, map_id=map_id,
                                   original_slot=slot, original_id=old_id,
                                   bytes=dest.stat().st_size,
                                   sha256=digest,
                                   preview='stock placeholder', authentication='none'))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--converted', required=True, type=Path)
    parser.add_argument('--stock', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report = build(args.converted, args.stock, args.output)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
