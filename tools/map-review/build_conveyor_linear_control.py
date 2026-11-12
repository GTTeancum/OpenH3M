"""Private animation diagnostic: retain path/endpoints, remove eased stalls."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt

b = MapBuilder(ROOT / 'work/elongation/zanzibar-06.map', 0)
c = b.cache
assert hashlib.sha256(b.original).hexdigest() == 'd16fc47ddff19aedded262731bd7fdf4dcbcd4ba6b2c9d300928643c42ff989f'
machine = c.tags[0x24f9]['offset']
model = c.tags[c.u(machine + 0x40) & 65535]['offset']
graph = c.tags[c.u(model + 0x2c) & 65535]['offset']
groups = c.block(graph + 0xf8, 12)
assert len(groups) == 1
datum = c.u(groups[0] + 4)
r = Resource(c, datum)
assert len(r.raw[0]) == 228 and r.raw[0][:4] == bytes([6, 0, 2, 0])
data = bytearray(r.raw[0])
changes = []
allowed = set()
for node in range(2):
    keys = list(data[56+node*6:62+node*6])
    assert keys == [0, 1, 2, 5, 12, 15]
    start = 72 + node*72
    first = struct.unpack_from('>f', data, start)[0]
    last = struct.unpack_from('>f', data, start+60)[0]
    for i, frame in enumerate(keys[1:-1], 1):
        at = start + i*12
        old = struct.unpack_from('>f', data, at)[0]
        new = first + (last-first)*frame/15
        struct.pack_into('>f', data, at, new)
        allowed.update(range(at, at+4))
        changes.append(dict(node_storage_index=node, frame=frame, before=old, after=new))
assert all(a == d or i in allowed for i, (a,d) in enumerate(zip(r.raw[0], data)))
zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
resource = c.block(zone+88,64)[datum & 65535]
location = c.block(play+48,16)[c.unpack('h',resource+34)[0]]
page_id, secondary, offset, offset2 = c.unpack('2h2I',location)
assert secondary == -1 and offset == offset2 == 0
page = c.block(play+24,88)[page_id]
assert c.unpack('h',page+4)[0] == -1 and c.u(page+16) == len(data)
salt = resource_salt('C:/X360/ISOs/H3M/default.xex')
compressed = zlib.compress(data)[2:-4]
raw_offset = b.append_raw(compressed)
address = page-c.start+c.base
b.put(address+3, 'B', 0)
b.put(address+8, '4I', raw_offset,len(compressed),len(data),zlib.crc32(data)^0xffffffff)
hashes = b''.join(hashlib.sha1(salt+x).digest() for x in (data,data[:1024],data[-1024:]))
for i,v in enumerate(hashes): b.put(address+24+i,'B',v)
out = ROOT/'work/map-review-20261105/elongation-linear-control.map'
assert not out.exists()
out.write_bytes(b.finish(salt))
check = Cache(out)
rr = Resource(check,datum)
assert rr.raw[0] == data and rr.data == r.data and rr.fix == r.fix
check.close()
report = dict(status='Private diagnostic; not deployed', changes=changes,
    preserved='Animation duration, endpoints, opposing node paths, key indices, collision, scripts, flags, geometry and simulation settings',
    hypothesis='Repeated creation re-enters the flat/eased opening of the source curve; a linear curve should carry at steady speed.',
    sha256=hashlib.sha256(out.read_bytes()).hexdigest())
(out.with_suffix('.json')).write_text(json.dumps(report,indent=2))
b.close()
print(out)
