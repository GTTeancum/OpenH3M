"""Build an unsigned LIVE/STFS test container. No authentication bypass or signing."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from verify_dlc_stfs import data_block, table_block, verify

BLOCK = 4096
BASE = 0xB000


def confined(path):
    root = Path(__file__).resolve().parents[4]
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Path outside repository: {path}')
    return path


def build(payload, output):
    payload, output = confined(payload), confined(output)
    files = sorted(payload.iterdir())
    if not 1 <= len(files) <= 64:
        raise ValueError('Expected 1..64 flat files')
    # Fail early instead of silently shipping the generic missing-preview icon.
    for info in payload.glob('*.mapinfo'):
        data = info.read_bytes()
        if len(data) < 0x1044 or data[0x30:0x34] != b'levl':
            raise ValueError(f'Unsupported mapinfo: {info.name}')
        preview = data[0xF44:0x1044].split(b'\0')[0].decode('ascii')
        if not preview or any(c in preview for c in '/\\:'):
            raise ValueError(f'Invalid preview basename: {info.name}')
        for suffix in ('', '_sm', '_clip', '_film', '_variant'):
            if not (payload / (preview + suffix + '.blf')).is_file():
                raise ValueError(f'Missing native preview {preview}{suffix}.blf; run build_dlc_previews.py')
    entries, count, directory = [], 1, bytearray(BLOCK)
    for index, path in enumerate(files):
        if not path.is_file() or path.is_symlink():
            raise ValueError('Only ordinary flat files supported')
        name = path.name.encode('ascii')
        size = path.stat().st_size
        if not 1 <= len(name) <= 40 or not 0 < size <= 0xFFFFFFFF:
            raise ValueError('Invalid file name or size')
        blocks = (size + BLOCK - 1) // BLOCK
        row = index * 64
        directory[row:row + len(name)] = name
        directory[row + 40] = len(name) | 0x40
        directory[row + 41:row + 44] = blocks.to_bytes(3, 'little')
        directory[row + 44:row + 47] = blocks.to_bytes(3, 'little')
        directory[row + 47:row + 50] = count.to_bytes(3, 'little')
        struct.pack_into('>HIHHHH', directory, row + 50,
                         0xFFFF, size, 0x21, 0, 0x21, 0)
        entries.append(dict(name=path.name, bytes=size, start=count, blocks=blocks))
        count += blocks
    if count > 4913000:
        raise ValueError('Exceeds three-level STFS capacity')
    top = 0 if count <= 170 else 1 if count <= 28900 else 2
    tables = {}
    for level in range(top + 1):
        span = 170 ** (level + 1)
        for index in range(0, count, span):
            table = bytearray(BLOCK)
            if level:
                struct.pack_into('>I', table, 4080, min(span, count - index))
            tables[level, index // span] = table
    total_size = BASE + (data_block(count - 1) + 1) * BLOCK
    header = bytearray(BASE)
    header[:4] = b'LIVE'
    # A fresh, intentionally unsigned header; never retain a retail signature.
    struct.pack_into('>QII', header, 0x22C, 0xFFFFFFFFFFFFFFFF, 1, 1)
    struct.pack_into('>IIIQ', header, 0x340, 0xAD0E, 2, 2, total_size - BASE)
    struct.pack_into('>I', header, 0x360, 0x4D5307E6)
    header[0x379:0x37E] = b'\x24\x00\x01\x01\x00'
    struct.pack_into('>I', header, 0x395, count)
    def text(offset, length, value):
        encoded = value.encode('utf-16-be')
        if len(encoded) + 2 > length:
            raise ValueError('Metadata string too long')
        header[offset:offset + length] = encoded.ljust(length, b'\0')
    titles = [p.read_bytes()[0x44:0x84].decode('utf-16-be').split('\0')[0]
              for p in files if p.suffix == '.mapinfo']
    description = ', '.join(titles) + '. Unsigned test package.'
    for locale in range(9):
        text(0x411 + locale * 256, 256, 'OpenH3M Custom Map Bundle - Test')
        text(0xD11 + locale * 256, 256,
             description)
    text(0x1611, 128, 'Custom map conversion')
    text(0x1691, 128, 'Halo 3')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.truncate(total_size)
        def write_block(index, block, next_block):
            stream.seek(BASE + data_block(index) * BLOCK)
            stream.write(block)
            table = tables[0, index // 170]
            row = index % 170 * 24
            table[row:row + 20] = hashlib.sha1(block).digest()
            struct.pack_into('>I', table, row + 20, 0x80000000 | next_block)
        write_block(0, directory, 0xFFFFFF)
        for entry in entries:
            digest = hashlib.sha256()
            with (payload / entry['name']).open('rb') as source:
                for relative in range(entry['blocks']):
                    chunk = source.read(BLOCK)
                    expected = min(BLOCK, entry['bytes'] - relative * BLOCK)
                    if len(chunk) != expected:
                        raise ValueError('Payload changed during packaging')
                    digest.update(chunk)
                    index = entry['start'] + relative
                    next_block = index + 1 if relative + 1 < entry['blocks'] else 0xFFFFFF
                    write_block(index, chunk.ljust(BLOCK, b'\0'), next_block)
                if source.read(1):
                    raise ValueError('Payload grew during packaging')
            entry['sha256'] = digest.hexdigest()
        for level in range(top + 1):
            for (table_level, index), table in tables.items():
                if table_level != level:
                    continue
                stream.seek(BASE + table_block(index * 170 ** (level + 1), level) * BLOCK)
                stream.write(table)
                digest = hashlib.sha1(table).digest()
                if level < top:
                    row = index % 170 * 24
                    tables[level + 1, index // 170][row:row + 20] = digest
                else:
                    header[0x381:0x395] = digest
        header[0x32C:0x340] = hashlib.sha1(header[0x344:]).digest()
        stream.seek(0)
        stream.write(header)
    with output.open('rb') as stream:
        integrity = verify(stream)
    with output.open('rb') as stream:
        package_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    # Halo uses the container filename as a mounted device name. A dot here
    # is consumed by its first-extension stripping, truncating map paths.
    # Follow the retail reference: an extensionless content-ID filename.
    content_id = header[0x32C:0x340].hex().upper()
    canonical = output.with_name(content_id)
    if canonical != output:
        if canonical.exists():
            raise ValueError('Canonical package already exists')
        output.rename(canonical)
        output = canonical
    return dict(package=str(output), bytes=total_size, sha256=package_hash,
                content_id=content_id, title_id='4D5307E6',
                content_type=2, entries=entries, integrity=integrity,
                signature='unsigned; zero signature field',
                runtime_validation='not performed',
                retail_acceptance='not targeted; OpenH3M and RGH/JTAG only')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report_path = confined(args.report)
    if report_path.exists():
        raise ValueError('Report already exists')
    report = build(args.payload, args.output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'entries'}))
