import struct
import unittest
from pathlib import Path
from types import SimpleNamespace
from map_exposure import adjust_camera


class PowerhouseCameraTests(unittest.TestCase):
    name = r'levels\multi\s3d_powerhouse\s3d_powerhouse'
    source = SimpleNamespace(file=Path('s3d_powerhouse.map'))

    def payload(self):
        data = bytearray(range(0xe4))
        struct.pack_into('>H', data, 0, 20)
        struct.pack_into('>2f', data, 0x10, 0., 2.)
        struct.pack_into('>H', data, 0x20, 0)
        struct.pack_into('>f', data, 0x24, .3)
        return bytes(data)

    def test_preserves_bloom_color_and_all_other_camera_data(self):
        before = self.payload()
        notes = []
        after = adjust_camera(self.source, self.name, before, notes)
        self.assertEqual(struct.unpack_from('>f', after, 0x14), (4.,))
        self.assertEqual(struct.unpack_from('>f', after, 0x24), (1.,))
        restored = bytearray(after)
        for offset in (0x14, 0x24):
            restored[offset:offset+4] = before[offset:offset+4]
        self.assertEqual(bytes(restored), before)
        self.assertTrue(notes)

    def test_profile_requires_both_map_and_tag_identity(self):
        before = self.payload()
        self.assertEqual(adjust_camera(self.source, 'other', before, []), before)
        other = SimpleNamespace(file=Path('other.map'))
        self.assertEqual(adjust_camera(other, self.name, before, []), before)

    def test_rejects_changed_or_nonfinite_source_sensitivity(self):
        for value in (0., .5, float('nan'), float('inf')):
            data = bytearray(self.payload())
            struct.pack_into('>f', data, 0x24, value)
            with self.assertRaises(ValueError):
                adjust_camera(self.source, self.name, data, [])


if __name__ == '__main__':
    unittest.main()
