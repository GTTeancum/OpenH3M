"""Derive the native alphabetical map route from the actual loaded metadata."""
import struct
from verify_dlc_stfs import data_block, read_directory


def menu_route(stock, directories, package, selected):
    entries = {}

    def add(data):
        if data[0x30:0x34] != b'levl':
            raise ValueError('Invalid mapinfo')
        if not struct.unpack_from('>I', data, 0x40)[0] & 0x40:
            return  # Campaign and menu metadata do not appear in multiplayer.
        name = data[0x1044:0x1144].split(b'\0')[0].decode('ascii')
        title = data[0x44:0x84].decode('utf-16-be').split('\0')[0]
        entries[name] = title

    for path in stock.glob('*.mapinfo'):
        add(path.read_bytes())
    for directory in directories:
        if directory:
            for path in directory.rglob('*.mapinfo'):
                add(path.read_bytes())
    if package:
        with package.open('rb') as stream:
            base, directory, _ = read_directory(stream)
            for offset in range(0, len(directory), 64):
                row = directory[offset:offset + 64]
                if not row[:40].split(b'\0')[0].endswith(b'.mapinfo'):
                    continue
                first = int.from_bytes(row[47:50], 'little')
                # Mapinfo identity and English title fit in its first block.
                # Filename lives in the second block, so gather the full file.
                size = int.from_bytes(row[52:56], 'big')
                data = bytearray()
                for block in range((size + 4095) // 4096):
                    stream.seek(base + data_block(first + block) * 4096)
                    data.extend(stream.read(4096))
                add(data[:size])
    ordered = sorted(entries, key=lambda name: entries[name].casefold())
    distance = ordered.index(selected) - ordered.index('zanzibar')
    return ('DOWN' if distance >= 0 else 'UP', abs(distance))
