"""Read-only, bounded audit of the existing Warlock proof-of-concept cache."""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOCK = ROOT / 'maps/lockout.map'
CANDIDATE = Path('D:/Programming/GitHub/H3M/game/maps/lockout.map')


def audit(path):
    data = path.read_bytes()
    u32 = lambda offset: struct.unpack_from('>I', data, offset)[0]
    base = u32(0x2E8)
    section_offset = (u32(0x48C) + u32(0x474)) & 0xFFFFFFFF
    section_size = u32(0x490)
    index = u32(0x10) - base + section_offset
    groups, group_address, count, table_address = struct.unpack_from('>4I', data, index)
    table = table_address - base + section_offset
    errors = []
    if data[:4] != b'head' or data[0x2FFC:0x3000] != b'foot':
        errors.append('Header/footer magic mismatch')
    if u32(8) != len(data):
        errors.append('Declared file size differs from actual size')
    if not section_offset <= table <= section_offset + section_size - count * 8:
        errors.append('Tag table lies outside tag section')
    else:
        for n in range(count):
            group, salt, address = struct.unpack_from('>HHI', data, table + n * 8)
            if group == 0xFFFF or address in (0, 0xFFFFFFFF):
                continue
            if group >= groups or not base <= address < base + section_size:
                errors.append(f'Tag {n}: invalid group or address {address:#x}')
    return {
        'path': str(path), 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'tag_count': count, 'tag_section_end_virtual': hex(base + section_size),
        'tag_table_virtual': hex(table_address), 'basic_structure_errors': errors,
        'authentication_block_330_46c': data[0x330:0x46C].hex(),
    }


if __name__ == '__main__':
    stock, candidate = audit(STOCK), audit(CANDIDATE)
    same_auth = stock.pop('authentication_block_330_46c') == candidate.pop('authentication_block_330_46c')
    result = {'stock': stock, 'candidate': candidate,
              'authentication_block_unchanged': same_auth,
              'limitations': 'Basic bounds only; does not validate signatures, resource contents, gameplay, or system link.'}
    output = ROOT / '.local/reports/map-audit.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
