"""Exercise real assembly stages with synthetic old/current MCC records."""
import struct
from types import SimpleNamespace
import unittest

from assemble_scenario import field, stage_spawn_settings
from cache_reader import Cache
from map_builder import MapBuilder
from scenario_forge import stage_forge
from source_schema import REFERENCE, MCC_2022_BUILD, load_schema


def fixture(old):
    def cache(mcc):
        value = Cache.__new__(Cache)
        value.mcc, value.endian, value.base, value.start = mcc, '<' if mcc else '>', 0, 0
        value.data = bytearray(0x4000)
        value.tags = {8: dict(group='scnr', offset=0x1000, salt=1),
                      3: dict(group='weap', offset=0x3800, salt=0xABCD)}
        value.name = lambda _: r'levels\multi\schema_test\schema_test'
        if mcc:
            build = MCC_2022_BUILD if old else 'May 30 2023 12:00:00'
            value.data[0xA0:0xA0 + len(build)] = build.encode('ascii')
        return value
    source, target = cache(True), cache(False)
    builder = MapBuilder.__new__(MapBuilder)
    builder.cache, builder.base, builder.reserve = target, 0, 0x10000
    builder.meta, builder.used = bytearray(builder.reserve), 0x8000
    importer = SimpleNamespace(source=source, builder=builder, registry=SimpleNamespace(cache=target),
        reference=REFERENCE, source_strings=SimpleNamespace(translate=lambda value, _: value + 1),
        target_strings=None, import_tag=lambda _: ('weap', 0x90001234), failed=False)
    return importer, load_schema(source, 'scnr'), load_schema(target, 'scnr')


class ScenarioRecordTests(unittest.TestCase):
    def test_both_forge_layouts_keep_reference_label_limit_and_price(self):
        for old in (True, False):
            with self.subTest(old=old):
                importer, source_schema, target_schema = fixture(old)
                source = importer.source
                label = 'Map Variant Weapon Palette'
                sf, df = field(source_schema, label), field(target_schema, label)
                struct.pack_into('<III', source.data, 0x1000 + int(sf.get('offset'), 0), 1, 0x3000 // 4, 0)
                struct.pack_into('<4I2If', source.data, 0x3000, 0x77656170, 0, 0, 0xABCD0003, 100, 16, 25.5)
                result = stage_forge(importer)
                count, pointer = struct.unpack('>II', importer.builder.read(0x1000 + int(df.get('offset'), 0), 8))
                record = importer.builder.read(pointer, 48)
                self.assertEqual(result[label], 1)
                self.assertEqual(count, 1)
                self.assertEqual(record[:4], b'weap')
                self.assertEqual(struct.unpack_from('>3If', record, 12), (0x90001234, 101, 16, 25.5))
                self.assertEqual(record[28:], bytes(20))

    def test_nonzero_legacy_forge_unknowns_still_reject(self):
        importer, source_schema, _ = fixture(True)
        sf = field(source_schema, 'Map Variant Weapon Palette')
        struct.pack_into('<III', importer.source.data, 0x1000 + int(sf.get('offset'), 0), 1, 0x3000 // 4, 0)
        struct.pack_into('<I', importer.source.data, 0x3000 + 12, 0xffffffff)
        struct.pack_into('<I', importer.source.data, 0x3000 + 28, 1)
        with self.assertRaisesRegex(ValueError, 'nonzero unknown'):
            stage_forge(importer)

    def test_both_spawn_layouts_keep_heights_and_native_block_offsets(self):
        for old in (True, False):
            with self.subTest(old=old):
                importer, source_schema, target_schema = fixture(old)
                sf, df = field(source_schema, 'Spawn Data'), field(target_schema, 'Spawn Data')
                struct.pack_into('<III', importer.source.data, 0x1000 + int(sf.get('offset'), 0), 1, 0x3000 // 4, 0)
                struct.pack_into('<3f', importer.source.data, 0x3000, -4., 12., -30.)
                result = stage_spawn_settings(importer)
                count, pointer = struct.unpack('>II', importer.builder.read(0x1000 + int(df.get('offset'), 0), 8))
                record = importer.builder.read(pointer, 108)
                self.assertEqual(result['Spawn Data'], 1)
                self.assertEqual(count, 1)
                self.assertEqual(struct.unpack_from('>3f', record), (-4., 12., -30.))
                self.assertEqual(record[12:72], bytes(60))
                for offset in (72, 84, 96):
                    self.assertEqual(struct.unpack_from('>3I', record, offset), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
