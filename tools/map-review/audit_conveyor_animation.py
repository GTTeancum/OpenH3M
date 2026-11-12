"""Compare serialized conveyor animation and expose authored translation keys."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from animation_resource import convert_animation_resource

source = Cache(Path('D:/SteamLibrary/steamapps/workshop/content/976730/3618057049/maps/h2_elongation.map'), True)
target = Cache(ROOT / 'work/elongation/zanzibar-06.map')

def animation(c, machine):
    model = c.tags[c.u(c.tags[machine]['offset'] + 0x40) & 65535]['offset']
    graph = c.tags[c.u(model + 0x2c) & 65535]['offset']
    groups = c.block(graph + 0xf8, 12)
    assert len(groups) == 1
    return Resource(c, c.u(groups[0] + 4))

sr, tr = animation(source, 4012), animation(target, 0x24f9)
converted = convert_animation_resource(sr, lambda value: value)
assert converted['control'] == tr.data
assert converted['raw'] == tr.raw[0]
assert dict(converted['fixups']) == tr.fix
assert sr.unpack('I', sr.root)[0] == 1
member = sr.ptr(sr.root + 4)
values = sr.unpack('IIHBB2B3H2I', member)
pointer = sr.fix[member + 40]
size = sr.unpack('I', member + 28)[0]
payload = sr.raw[(pointer >> 29) - 2][pointer & 0x1fffffff:][:size]
assert values[2] == 16 and values[9] == 0 and values[11] == 216
assert payload[:4] == bytes([6, 0, 2, 0])
assert struct.unpack_from('<9I', payload, 12) == (48, 56, 56, 56, 68, 72, 72, 216, 0)
keys = [list(payload[56:62]), list(payload[62:68])]
translations = [[struct.unpack_from('<3f', payload, 72 + 12*(node*6+i)) for i in range(6)] for node in range(2)]
report = {
    'source': str(source.file.name), 'native': str(target.file.name),
    'comparison': 'Entire endian-converted control, raw payload and fixup table match native resource exactly.',
    'native_payload_sha256': hashlib.sha256(tr.raw[0]).hexdigest(),
    'frames': 16, 'codec': 6, 'codec_name': 'ReverseByteKeyframeLightlyQuantized',
    'translation_keys_in_storage_order': keys,
    'translation_values_in_storage_order': translations,
    'node_flags_hex': payload[216:].hex(),
    'interpretation': 'Authored curve has equal first two keys, eased motion and opposite translation streams. Reverse codec reverses channel order. No conversion-specific loss demonstrated; live channel progression remains to be measured.',
}
(ROOT / 'work/map-review-20261105/conveyor-animation-audit.json').write_text(json.dumps(report, indent=2))
source.close()
target.close()
print(report['comparison'])
