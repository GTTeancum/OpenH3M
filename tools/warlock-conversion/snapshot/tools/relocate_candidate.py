"""Relocate the appended metadata below stock tags, preserving retail's fixed upper limit.

Pointer locations come from Assembly Halo3 schemas, not from scanning float values.
Only a separate local candidate is written. No runtime or disc files are edited.
"""
import hashlib
import json
import struct
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from xexlib import Xex

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/Programming/GitHub/H3M/game/maps/lockout.map')
EXPECTED = 'a2cf1f69bef10728b380848a2217bb69c2779797929a03beff17c8e64012d558'
data = bytearray(SOURCE.read_bytes())
assert hashlib.sha256(data).hexdigest() == EXPECTED
u = lambda o: struct.unpack_from('>I', data, o)[0]
base, size = u(0x2E8), u(0x18)
file_base = (u(0x48C) + u(0x474)) & 0xFFFFFFFF
limit = 0xBFC00000
end = base + size
extra = end - limit
new_base = base - extra
delta = new_base - limit
assert extra == 0x450000
offset = lambda address: address - base + file_base
pointer_fields = set()
seen = set()
schema_errors = []
retained_stock_nulls = []


def visit(node, address, depth=0):
    if depth > 32:
        raise ValueError('Schema recursion exceeded')
    key = (id(node), address)
    if key in seen:
        return
    seen.add(key)
    for field in node:
        kind = field.tag.lower()
        if kind not in ('tagblock', 'dataref'):
            continue
        loc = offset(address) + int(field.attrib['offset'], 0)
        count = u(loc)
        ptr_loc = loc + (4 if kind == 'tagblock' else 12)
        ptr = u(ptr_loc)
        if not count:
            continue
        if ptr == 0 and address < limit:
            # Some shipped zone descriptors retain a count with no resident array.
            with (ROOT / 'maps/lockout.map').open('rb') as stock:
                stock.seek(0x7861000 + loc - file_base)
                if stock.read(8) == data[loc:loc + 8]:
                    retained_stock_nulls.append(hex(loc))
                    continue
        stride = int(field.attrib['elementSize'], 0) if kind == 'tagblock' else 1
        if count > 2000000 or not base <= ptr < end or ptr + count * stride > end:
            schema_errors.append({'field': field.attrib.get('name'), 'location': hex(loc),
                                  'count': count, 'pointer': hex(ptr), 'stride': stride})
            continue
        pointer_fields.add(ptr_loc)
        if kind == 'tagblock':
            for i in range(count):
                visit(field, ptr + i * stride, depth + 1)


index = offset(u(0x10))
group_count, groups_address, count, table_address = struct.unpack_from('>4I', data, index)
groups = [data[offset(groups_address) + i * 16:offset(groups_address) + i * 16 + 4].decode('ascii')
          for i in range(group_count)]
for loc in (index + 4, index + 12, index + 20, index + 28):
    pointer_fields.add(loc)
schemas = {}
for i in range(count):
    loc = offset(table_address) + i * 8
    group, salt, address = struct.unpack_from('>HHI', data, loc)
    pointer_fields.add(loc + 4)
    if group == 0xFFFF or address in (0, 0xFFFFFFFF):
        continue
    name = groups[group]
    if name not in ('play', 'zone', 'sLdT', 'bitm', 'sbsp', 'scnr'):
        continue
    if name not in schemas:
        schemas[name] = ET.parse(ROOT / f'.local/reference/plugins/{name}.xml').getroot()
    visit(schemas[name], address)

report = {'input_sha256': EXPECTED, 'old_base': hex(base), 'new_base': hex(new_base),
          'required_end': hex(limit), 'old_end': hex(end), 'schema_errors': schema_errors,
          'pointer_fields_examined': len(pointer_fields)}
report['retained_stock_nulls'] = retained_stock_nulls
report_path = ROOT / '.local/reports/relocation.json'
if schema_errors:
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise SystemExit('Schema validation failed; no candidate written. See relocation.json.')

# The minimal imported scenario omitted the required collision soft-surface defaults.
# Retail sub_82115768 reads scnr+0x780 unconditionally during scenario initialization.
scenario = offset(u(offset(table_address) + 8 * 8 + 4))
if u(scenario + 0x77C) == 0 and u(scenario + 0x780) == 0:
    with (ROOT / 'maps/lockout.map').open('rb') as stock:
        h = stock.read(0x3000)
        su = lambda o: struct.unpack_from('>I', h, o)[0]
        sf = (su(0x48C) + su(0x474)) & 0xFFFFFFFF
        sb = su(0x2E8)
        def read_stock(address, length):
            stock.seek(address - sb + sf)
            return stock.read(length)
        si = read_stock(su(0x10), 0x28)
        st = struct.unpack_from('>I', si, 12)[0]
        sa = struct.unpack('>I', read_stock(st + 8 * 8 + 4, 4))[0]
        descriptor = read_stock(sa + 0x77C, 12)
        sn, sp = struct.unpack_from('>II', descriptor)
        assert sn == 1
        assert data[offset(sp):offset(sp) + 24] == read_stock(sp, 24)
    data[scenario + 0x77C:scenario + 0x788] = descriptor
    report['scenario_soft_surfaces'] = {'count': sn, 'stock_pointer': hex(sp)}

patches = []
for loc in sorted(pointer_fields):
    value = u(loc)
    if limit <= value < end:
        struct.pack_into('>I', data, loc, value + delta)
        patches.append({'offset': hex(loc), 'before': hex(value), 'after': hex(value + delta)})

# The original tag addresses remain unchanged. Only appended allocations move.
old_span = limit - base
tag_bytes = bytes(data[file_base:file_base + size])
data[file_base:file_base + size] = tag_bytes[old_span:] + tag_bytes[:old_span]
struct.pack_into('>I', data, 0x2E8, new_base)
struct.pack_into('>I', data, 0x2F0, new_base)
struct.pack_into('>I', data, 0x2F4, u(0x2F4) + extra)
struct.pack_into('>I', data, 0x31C, u(0x31C) - extra)
assert new_base + size == limit
report['pointer_patches'] = patches
def checksum(blob):
    return int(np.bitwise_xor.reduce(np.frombuffer(blob, dtype='>u4', offset=0x3000)))

assert checksum(SOURCE.read_bytes()) == 0x718DD886
struct.pack_into('>I', data, 0x2C4, checksum(data))
xex = Xex(str(ROOT / 'default.xex'))
image = xex.image()
resources = xex.hdrs[0x2FF]
resource_size = struct.unpack_from('>I', xex.raw, resources)[0]
salt = None
for pos in range(resources + 4, resources + resource_size, 16):
    if xex.raw[pos:pos + 8].rstrip(b'\0') == b'00':
        address, length = struct.unpack_from('>II', xex.raw, pos + 8)
        assert length == 0x138
        salt = image[address - xex.image_base:address - xex.image_base + 0x22]
assert salt is not None

# Five imported pages in the old candidate have valid CRCs but blank SHA1 fields.
# Resource hashes use the same retail salt; first/last chunks are 1024 bytes.
new_offset = lambda address: address - new_base + file_base
play = new_offset(0xBECE7060)
page_count = u(play + 0x18)
page_table = new_offset(u(play + 0x1C))
resource_base = (u(0x484) + u(0x470)) & 0xFFFFFFFF
repaired_pages = []
for i in range(page_count):
    page = page_table + i * 0x58
    if any(data[page + 0x18:page + 0x54]):
        continue
    if struct.unpack_from('>h', data, page + 4)[0] != -1:
        continue
    block, compressed_size, raw_size, crc = struct.unpack_from('>4I', data, page + 8)
    assert resource_base + block + compressed_size <= file_base
    payload = bytes(data[resource_base + block:resource_base + block + compressed_size])
    codec = data[page + 3]
    if codec == 0:
        payload = zlib.decompress(payload, -15)
    else:
        assert codec == 0xFF, f'Unsupported codec {codec}'
    assert len(payload) == raw_size
    assert (zlib.crc32(payload) ^ 0xFFFFFFFF) == crc, f'Page {i} CRC mismatch'
    hashes = b''.join(hashlib.sha1(salt + chunk).digest()
                      for chunk in (payload, payload[:1024], payload[-1024:]))
    data[page + 0x18:page + 0x54] = hashes
    repaired_pages.append(i)
report['resource_pages_repaired'] = repaired_pages
struct.pack_into('>I', data, 0x2C4, checksum(data))

def header_hash(blob):
    header = bytearray(blob[:0x3000])
    # Exact normalization in retail sub_82206440 before sub_82151DC8.
    for start, length in [(0x320, 4), (0x328, 8), (0x330, 0x13C),
                          (0x1C, 0x100), (0x144, 8), (0x16C, 0x20), (0x49C, 0x10)]:
        header[start:start + length] = bytes(length)
    return hashlib.sha1(salt + header).digest()

with (ROOT / 'maps/lockout.map').open('rb') as stock_file:
    stock_header = stock_file.read(0x3000)
assert header_hash(stock_header) == stock_header[0x330:0x344]
data[0x330:0x344] = header_hash(data)
report['checksum'] = hex(u(0x2C4))
report['header_hash'] = data[0x330:0x344].hex()
report['signature_note'] = 'RSA signature retained; no signature bypass or runtime edit is made. Original-console acceptance is unverified.'
output = ROOT / '.local/candidate/lockout.map'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(data)
report['output_sha256'] = hashlib.sha256(data).hexdigest()
report['output'] = str(output)
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'pointer_patches'}, indent=2))
print('Relocated pointer fields:', len(patches))
