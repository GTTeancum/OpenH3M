"""Build caller must not reactivate legacy caps or lose final resource identity."""
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from material_importer import MaterialImporter


class MaterialAuthoredMipTests(unittest.TestCase):
    def fixture(self):
        source = SimpleNamespace(
            info=lambda _: [dict(width=1024, height=256, format=14, mips=11)],
            pixels=lambda _, index=0: b'input',
            c=SimpleNamespace(tags={4: {}}, name=lambda _: 'authored_texture'))
        materials = MaterialImporter.__new__(MaterialImporter)
        materials.bitmaps = source
        materials.bitmap_preservation = []
        materials._bitmap_encodings = {}
        record = bytearray(48)
        struct.pack_into('>HH', record, 4, 1024, 256)
        struct.pack_into('>H', record, 12, 14)
        record[20] = 10
        struct.pack_into('>I', record, 28, 5)
        control = bytearray(64)
        from encode_bitmap import texture_gpu_format
        struct.pack_into('>I', control, 0, 5)
        struct.pack_into('>HHBBBBI', control, 40, 1024, 256, 1, 11, 0, 0, texture_gpu_format(14, 0))
        return materials, source, (bytes(record), bytes(control), b'tiled')

    def test_full_authored_policy_overrides_legacy_selection(self):
        materials, source, encoded = self.fixture()
        with patch('material_importer.encode_bitmap_base', return_value=encoded) as encoder:
            self.assertEqual(materials.encode_bitmap(source, 4, max_dimension=512,
                resize_blend=True, preserve_bc_mips=False, opaque_alpha=True), encoded)
        args = encoder.call_args.kwargs
        self.assertEqual(args['max_dimension'], 1024)
        self.assertTrue(args['preserve_authored_mips'])
        self.assertTrue(args['opaque_alpha'])
        self.assertNotIn('resize_blend', args)
        materials.record_bitmap_resource(*encoded, 0x90000001, 0x91000020)
        report = materials.bitmap_preservation_report({'old_to_new': {'32': 7}})
        self.assertEqual(report[0]['resource_datum'], 0x91000007)
        self.assertEqual(report[0]['staged_resource_datum'], 0x91000020)
        self.assertEqual(report[0]['input']['mips'], 11)
        self.assertFalse(report[0]['derived_input'])
        self.assertEqual(materials.bitmap_preservation[0]['resource_datum'], 0x91000020)

    def test_rejects_encoder_dropping_and_reports_retired_resources(self):
        materials, source, encoded = self.fixture()
        record = bytearray(encoded[0]); record[20] = 0
        with self.assertRaisesRegex(ValueError, 'lost authored'):
            materials.remember_bitmap_encoding(source, 4, 0, (bytes(record), *encoded[1:]))
        materials.remember_bitmap_encoding(source, 4, 0, encoded)
        materials.record_bitmap_resource(*encoded, 0x90000001, 0x91000020)
        report = materials.bitmap_preservation_report({'old_to_new': {}})
        self.assertFalse(report[0]['retained'])
        self.assertIsNone(report[0]['resource_datum'])

    def test_multi_image_resources_keep_order_and_all_records(self):
        from test_native_bitmap_recovery import fixture
        importer, _, _ = fixture()
        materials = importer.materials
        a = bytes([1])*48, bytes(64), b'first'
        b = bytes([2])*48, bytes(64), b'second'
        owner = materials.bitmap_resources([a, b])
        address = struct.unpack_from('>I', importer.registry.tags, (owner&65535)*8+4)[0]
        count, pointer = struct.unpack('>II', importer.builder.read(address+96, 8))
        self.assertEqual(count, 2)
        self.assertEqual(importer.builder.read(pointer, 96), a[0]+b[0])
        count, pointer = struct.unpack('>II', importer.builder.read(address+140, 8))
        self.assertEqual(count, 2)
        self.assertEqual([r[2]['raw'] for r in importer.registry.resources], [b'first', b'second'])


if __name__ == '__main__':
    unittest.main()
