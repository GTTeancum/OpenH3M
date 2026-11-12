"""Recovery preserves native settings and rejects unaudited/changed data."""
import hashlib
import struct
from types import SimpleNamespace
import unittest

from cache_reader import Cache
from encode_bitmap import mip_size
from map_builder import MapBuilder
from material_importer import MaterialImporter
from native_bitmap_recovery import recover
from source_schema import load_schema


def fixture():
    name = 'test/audited_bitmap'
    def cache(mcc):
        c = Cache.__new__(Cache)
        c.mcc, c.endian, c.base, c.start = mcc, '<' if mcc else '>', 0, 0
        c.data = bytearray(0x2000)
        c.tags = {3: dict(group='bitm', salt=0xABCD, offset=0x200)}
        c.name = lambda _: name
        c.file = SimpleNamespace(name='source.map' if mcc else 'native.map')
        c.data[0xA0:0xA0+23] = b'May 30 2023 12:00:00'.ljust(23, b'\0')
        struct.pack_into(c.endian+'III', c.data, 0x200+96, 1, 0x1000//4 if mcc else 0x1000, 0)
        struct.pack_into(c.endian+'III', c.data, 0x200+140, 1, 0x1100//4 if mcc else 0x1100, 0)
        struct.pack_into(c.endian+'HHBBHHH', c.data, 0x1004, 32, 32, 1, 0x1E, 0, 14, 3)
        c.data[0x1014:0x1016] = bytes((5,3))
        struct.pack_into(c.endian+'IH', c.data, 0x200, 5, 0x50)
        struct.pack_into(c.endian+'f', c.data, 0x20C, 0.25)
        return c
    source, native = cache(True), cache(False)
    pixels = b''.join(bytes([n])*mip_size(max(1,32>>n),max(1,32>>n),14) for n in range(6))
    expected = dict(width=32,height=32,depth=1,kind=0,format=14,mips=6,curve=3,
                    source_sha256=hashlib.sha256(pixels).hexdigest())
    builder = MapBuilder.__new__(MapBuilder)
    builder.base, builder.used, builder.reserve = 0, 0x100, 0x4000
    builder.meta = bytearray(builder.reserve)
    registry = SimpleNamespace(tags=bytearray(), resources=[])
    def newtag(group, data):
        address = builder.alloc(data)
        owner = 0x90000000 | len(registry.tags)//8
        registry.tags.extend(struct.pack('>HHI',0,0x9000,address))
        return owner,address
    def resource(owner, kind, data):
        registry.resources.append((owner,kind,data))
        return 0x91000000
    registry.newtag, registry.add_resource = newtag, resource
    materials = MaterialImporter.__new__(MaterialImporter)
    materials.target = native
    materials.builder, materials.registry, materials.done = builder, registry, {}
    materials.bitmaps = SimpleNamespace(c=source,pixels=lambda _, index=0:pixels,
        info=lambda _:[dict(width=32,height=32,format=14,mips=6,kind=0,curve=3)])
    importer = SimpleNamespace(source=source,materials=materials,builder=builder,registry=registry,
                               audited_bitmap_recoveries={name:expected},resolved={},added=[])
    return importer,native,load_schema(native,'bitm')


class RecoveryTests(unittest.TestCase):
    def test_retains_native_root_and_all_authored_mips(self):
        i,c,schema = fixture()
        before = bytes(c.data)
        group,owner = recover(i,c,0xABCD0003,schema)
        self.assertEqual(group,'bitm')
        address = struct.unpack_from('>I',i.registry.tags,(owner&65535)*8+4)[0]
        root = i.builder.read(address,164)
        self.assertEqual(root[:96],before[0x200:0x260])
        count,pointer = struct.unpack_from('>II',root,96)
        self.assertEqual(count,1)
        self.assertEqual(i.builder.read(pointer+20,2),bytes((5,3)))
        self.assertEqual(i.registry.resources[0][2]['control'][45],6)
        self.assertEqual(bytes(c.data),before)

    def test_changed_pixels_or_layout_reject_before_allocation(self):
        for change in ('source_sha256','width'):
            with self.subTest(change=change):
                i,c,schema = fixture()
                i.audited_bitmap_recoveries[c.name(3)][change] = 'bad' if change=='source_sha256' else 64
                with self.assertRaisesRegex(ValueError,'changed'):
                    recover(i,c,0xABCD0003,schema)
                self.assertEqual(len(i.registry.tags),0)

    def test_unlisted_texture_has_no_recovery(self):
        i,c,schema = fixture()
        i.audited_bitmap_recoveries.clear()
        self.assertIsNone(recover(i,c,0xABCD0003,schema))
        self.assertEqual(len(i.registry.tags),0)

    def test_populated_sequence_is_not_discarded(self):
        i,c,schema = fixture()
        field = next(n for n in schema if n.get('name')=='Sequences')
        struct.pack_into('>I',c.data,0x200+int(field.get('offset'),0),1)
        with self.assertRaisesRegex(ValueError,'cannot discard Sequences'):
            recover(i,c,0xABCD0003,schema)


if __name__ == '__main__':
    unittest.main()
