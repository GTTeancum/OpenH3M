"""Inventory a single-table retail STFS reference directly from its ZIP."""
import argparse
import json
import struct
import zipfile
from pathlib import Path


def inspect(path):
    with zipfile.ZipFile(path) as archive:
        members = [x for x in archive.infolist() if not x.is_dir()]
        if len(members) != 1:
            raise ValueError('Expected exactly one package')
        with archive.open(members[0]) as stream:
            header = stream.read(0xB000)
            if header[:4] not in (b'LIVE', b'PIRS', b'CON '):
                raise ValueError('Not an STFS container')
            u32 = lambda o: struct.unpack_from('>I', header, o)[0]
            count = struct.unpack_from('<H', header, 0x37C)[0]
            block = int.from_bytes(header[0x37E:0x381], 'little')
            if count != 1 or block >= 170:
                raise ValueError('Reference needs multi-table traversal')
            backing = 1 if header[0x37B] & 1 else 2
            offset = ((u32(0x340) + 4095) & ~4095) + (block + backing) * 4096
            stream.seek(offset)
            table = stream.read(4096)
            if len(table) != 4096:
                raise ValueError('Truncated directory')
            entries = []
            for i in range(64):
                row = table[i*64:(i+1)*64]
                if not row[0]:
                    break
                entries.append(dict(index=i, name=row[:row[40] & 63].decode('ascii'),
                                    directory=bool(row[40] & 128),
                                    contiguous=bool(row[40] & 64),
                                    parent=int.from_bytes(row[50:52], 'big'),
                                    start_block=int.from_bytes(row[47:50], 'little'),
                                    bytes=int.from_bytes(row[52:56], 'big')))
            return dict(source=str(path), member=members[0].filename,
                        package_bytes=members[0].file_size, magic=header[:4].decode(),
                        title_id=f'{u32(0x360):08X}', content_type=u32(0x344),
                        display_name=header[0x411:0x511].decode('utf-16-be').rstrip('\0'),
                        entries=entries,
                        scope='Directory/header inventory only; no signature or payload hash validation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.archive)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'entries'}))
    print(f"Directory entries: {len(result['entries'])}")
