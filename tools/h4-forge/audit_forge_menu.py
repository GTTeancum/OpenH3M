"""Verify original Forge menu bindings and inventory namespace-1 retail labels."""
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from Crypto.Cipher import AES

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT/'work/h4-forge-research'
cache = RESEARCH/'disc2-assets/ca_forge_ravine.map'
with cache.open('rb') as source:
    header = source.read(0x500)
    u = lambda offset: struct.unpack_from('>I', header, offset)[0]
    def read_at(offset, size):
        source.seek(offset)
        data = source.read(size)
        assert len(data) == size
        return data
    size = u(0x15c)
    encrypted = read_at((u(0x164)+u(0x47c)) & 0xffffffff, (size+15)//16*16)
    indices = read_at((u(0x160)+u(0x47c)) & 0xffffffff,u(0x158)*4)
key = bytes(v ^ 0xa5 for v in b'ILikeSafeStrings').ljust(16,b'\0')
strings = AES.new(key,AES.MODE_CBC,bytes(v ^ 0x3c for v in key)).decrypt(encrypted)[:size]
namespaces = {int(n.get('id'),0):int(n.get('startIndex'),0)
              for n in ET.parse(RESEARCH/'reference/H4_StringIDs.xml').getroot()}
assert namespaces[1] == 0x631
def label(value):
    assert (value >> 19) & 255 == 1
    index = namespaces[1] + (value & 0x7ffff)
    offset = struct.unpack_from('>I',indices,index*4)[0]
    if offset == 0xffffffff:
        return ''
    return strings[offset:strings.index(b'\0',offset)].decode('utf8')
def body(name, file):
    text = (RESEARCH/f'generated/halo4_recomp.{file}.cpp').read_text()
    return text.split(f'DEFINE_REX_FUNC(sub_{name}) {{',1)[1].split('DEFINE_REX_FUNC(',1)[0]
constructor = body('8268A290',66)
callback = body('82685E88',108)
# Exact original instructions connect label, list, default and event callback.
for instruction in ['lis r27,-32236','addi r5,r27,12960','stw r5,172(r31)',
                    'ori r3,r25,1478','stw r3,176(r31)',
                    'stw r30,184(r31)','addi r30,r3,56',
                    'li r26,5','stw r26,188(r31)']:
    assert '// '+instruction in constructor, instruction
for instruction in ['li r9,14','sth r9,344(r1)','stb r4,80(r1)',
                    'stw r4,16(r3)','bl 0x825812d0']:
    assert '// '+instruction in callback, instruction
image = (RESEARCH/'h4-image.bin').read_bytes()
assert struct.unpack_from('>I',image,0x821432a0+72-0x82000000)[0] == 0x82685e88
assert label(0x805c6) == 'forge_tools_snap'
options = [label(0x8060f+i) for i in range(6)]
assert options == ['snap_off','snap_90','snap_45','snap_30','snap_15','snap_5']
for i in range(6):
    assert f'ori r8,r10,{1551+i}' in constructor
bindings = []
for name, control, vtable, slot, setter, file, event in [
    ('forge_tools_delete_all_of_type',196,0x8214313c,52,'82685C50',171,8),
    ('forge_tools_delete_all_of_palette',240,0x82143174,68,'82686F58',133,9),
    ('forge_tools_duplicate_object',516,0x821431f4,52,'82685CA8',189,10),
    ('forge_tools_lock',536,0x8214322c,52,'82685DA0',35,11),
    ('forge_tools_unlock_all',556,0x82143264,52,'82685E50',289,12),
]:
    assert struct.unpack_from('>I',image,vtable+slot-0x82000000)[0] == int(setter,16)
    setter_body = body(setter,file)
    assert 'bl 0x825812d0' in setter_body
    assert any(f'li r{register},{event}' in setter_body for register in range(3,12))
    bindings.append(dict(name=name, control_offset=hex(control), vtable=hex(vtable),
                         slot=slot,callback=setter,event=event,
                         callback_sha256=hashlib.sha256(setter_body.encode()).hexdigest(),
                         evidence='Constructor label/control stores manually traced; image callback and event producer checked.'))
inventory = []
for offset in range(namespaces[2]-namespaces[1]):
    value = 0x80000+offset
    name = label(value)
    if name.startswith(('forge_', 'snap_')):
        inventory.append(dict(id=f'0x{value:08x}',name=name))
report = dict(source=str(cache.relative_to(ROOT)),
              scope='String identifiers are discovery leads, not proof a feature is reachable or implemented.',
              inventory=inventory, tools_bindings=bindings,
              rotation_snap=dict(constructor='8268A290',control_offset='0xac',
                 vtable='821432A0',setter_slot=72,setter='82685E88',event=14,
                 constructor_default=5, options=options,
                 constructor_sha256=hashlib.sha256(constructor.encode()).hexdigest(),
                 setter_sha256=hashlib.sha256(callback.encode()).hexdigest()))
(RESEARCH/'isolated/full-re-menu.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified rotation snap label/list/vtable/setter/event binding; constructor default 5 (snap_5).')
print(f'Inventoried {len(inventory)} namespace-1 Forge/snap string identifiers.')
for entry in inventory:
    if not entry['name'].endswith('_description'):
        print(entry['id'],entry['name'])
