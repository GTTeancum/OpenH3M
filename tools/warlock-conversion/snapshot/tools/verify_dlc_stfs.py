"""Read-only STFS hash-tree verification, without extraction or signature claims."""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path


def data_block(index):
    result = index
    for span in (170, 28900, 4913000):
        result += (index + span) // span
        if index < span:
            break
    return result


def table_block(index, level):
    if level == 2:
        return 29071
    if level == 1:
        return 171 if index < 28900 else index // 28900 * 29071 + 1
    if index < 170:
        return 0
    return index // 170 * 171 + index // 28900 + 1 + (index >= 28900)


def verify(stream):
    header = stream.read(0x344)
    if header[:4] not in (b'LIVE', b'PIRS', b'CON '):
        raise ValueError('Not STFS')
    size = struct.unpack_from('>I', header, 0x340)[0]
    if not 0x971A <= size <= 0x100000:
        raise ValueError('Unexpected header size')
    base = (size + 4095) & ~4095
    header += stream.read(base - len(header))
    if len(header) != base or header[0x379] != 0x24:
        raise ValueError('Truncated or invalid volume descriptor')
    if not header[0x37B] & 1:
        raise ValueError('Only single-backing read-only STFS supported')
    count = struct.unpack_from('>I', header, 0x395)[0]
    if not 0 < count <= 4913000:
        raise ValueError('Invalid block count')
    # Reference content ID covers header padding through the first block boundary.
    if hashlib.sha1(header[0x344:base]).digest() != header[0x32C:0x340]:
        raise ValueError('Header SHA1 mismatch')
    top = 0 if count <= 170 else 1 if count <= 28900 else 2
    locations = {data_block(i): ('data', i) for i in range(count)}
    for level in range(top + 1):
        span = 170 ** (level + 1)
        for index in range(0, count, span):
            physical = table_block(index, level)
            if physical in locations:
                raise ValueError('Overlapping table/data layout')
            locations[physical] = ('table', (level, index // span))
    hashes = [None] * count
    tables = {}
    position = base
    for physical, (kind, identity) in sorted(locations.items()):
        target = base + physical * 4096
        gap = target - position
        if gap < 0:
            raise ValueError('Non-monotonic layout')
        if gap and len(stream.read(gap)) != gap:
            raise ValueError('Truncated gap')
        block = stream.read(4096)
        if len(block) != 4096:
            raise ValueError('Truncated block')
        position = target + 4096
        if kind == 'data':
            hashes[identity] = hashlib.sha1(block).digest()
        else:
            tables[identity] = block
    for index, digest in enumerate(hashes):
        row = index % 170 * 24
        if tables[0, index // 170][row:row + 20] != digest:
            raise ValueError(f'Data SHA1 mismatch at block {index}')
    for (level, index), block in tables.items():
        digest = hashlib.sha1(block).digest()
        if level == top:
            expected = header[0x381:0x395]
        else:
            row = index % 170 * 24
            expected = tables[level + 1, index // 170][row:row + 20]
        if digest != expected:
            raise ValueError(f'Hash table mismatch at level {level}, index {index}')
    return dict(data_blocks=count, hash_tables=len(tables), top_level=top,
                header_sha1='pass', data_sha1='pass', hash_tree='pass',
                signature_validation='NOT performed',
                scope='Integrity only; does not establish retail acceptance')


def verify_payload(package, payload):
    """Read the package directory and chains; compare every byte to staged files."""
    with package.open('rb') as stream:
        header = stream.read(0xB000)
        base = (struct.unpack_from('>I', header, 0x340)[0] + 4095) & ~4095
        if struct.unpack_from('<H', header, 0x37C)[0] != 1:
            raise ValueError('Expected one root directory block')
        first = int.from_bytes(header[0x37E:0x381], 'little')
        total = struct.unpack_from('>I', header, 0x395)[0]
        def read_block(index):
            if not 0 <= index < total:
                raise ValueError('Block outside volume')
            stream.seek(base + data_block(index) * 4096)
            block = stream.read(4096)
            if len(block) != 4096:
                raise ValueError('Truncated data')
            return block
        directory = read_block(first)
        seen, used, tables = set(), {first}, {}
        result = []
        for row_offset in range(0, 4096, 64):
            row = directory[row_offset:row_offset + 64]
            if row[40] & 63 == 0:
                continue
            name = row[:row[40] & 63].decode('ascii')
            if name in seen or Path(name).name != name or '/' in name or '\\' in name:
                raise ValueError('Duplicate or non-flat name')
            if row[40] & 128 or row[50:52] != b'\xff\xff':
                raise ValueError('Expected root file')
            seen.add(name)
            size = int.from_bytes(row[52:56], 'big')
            blocks = (size + 4095) // 4096
            if any(int.from_bytes(row[a:a + 3], 'little') != blocks for a in (41, 44)):
                raise ValueError('Directory allocation mismatch')
            index = int.from_bytes(row[47:50], 'little')
            digest = hashlib.sha256()
            with (payload / name).open('rb') as expected:
                for n in range(blocks):
                    if index in used:
                        raise ValueError('Cross-linked file or loop')
                    used.add(index)
                    block = read_block(index)
                    length = min(4096, size - n * 4096)
                    if block[:length] != expected.read(length):
                        raise ValueError(f'Payload mismatch: {name}, block {n}')
                    if any(block[length:]):
                        raise ValueError('Nonzero final-block padding')
                    digest.update(block[:length])
                    physical = table_block(index, 0)
                    if physical not in tables:
                        stream.seek(base + physical * 4096)
                        tables[physical] = stream.read(4096)
                    info = struct.unpack_from('>I', tables[physical], index % 170 * 24 + 20)[0]
                    if info >> 30 != 2:
                        raise ValueError('File block not allocated')
                    index = info & 0xFFFFFF
                if index != 0xFFFFFF or expected.read(1):
                    raise ValueError('File chain or source length mismatch')
            result.append(dict(name=name, bytes=size, sha256=digest.hexdigest()))
        if seen != {p.name for p in payload.iterdir()} or len(used) != total:
            raise ValueError('Missing, extra, or orphaned payload data')
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--payload', type=Path, help='Compare flat payload with an unpacked container file')
    args = parser.parse_args()
    if zipfile.is_zipfile(args.source):
        with zipfile.ZipFile(args.source) as archive:
            members = [x for x in archive.infolist() if not x.is_dir()]
            if len(members) != 1:
                raise ValueError('Expected one package in ZIP')
            with archive.open(members[0]) as stream:
                result = verify(stream)
    else:
        with args.source.open('rb') as stream:
            result = verify(stream)
    if args.payload:
        if zipfile.is_zipfile(args.source):
            raise ValueError('Payload comparison takes a container file, not a ZIP')
        result['payload_files'] = verify_payload(args.source, args.payload)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
