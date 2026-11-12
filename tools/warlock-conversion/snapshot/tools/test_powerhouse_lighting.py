import struct
import unittest
from types import SimpleNamespace
from powerhouse_lighting import boost_atlas, boost_vertices, configure


class AmbientCalibrationTests(unittest.TestCase):
    def test_decoded_gain_and_unchanged_direction(self):
        original = bytes([8, 10, 20, 30, 252, 30, 40, 50, 9, 80, 90, 100,
                          10, 11, 12, 13, 14, 15, 16, 17])
        changed = boost_vertices(original, 4)
        self.assertEqual(changed[:4] + changed[5:], original[:4] + original[5:])
        before = struct.unpack('b', original[4:5])[0]
        after = struct.unpack('b', changed[4:5])[0]
        for mantissa in original[5:8]:
            self.assertEqual(mantissa / 127 * 2 ** (after / 4),
                             2 * mantissa / 127 * 2 ** (before / 4))

    def test_zero_and_overflow(self):
        zero = bytearray(20)
        zero[4] = 127
        self.assertEqual(boost_vertices(bytes(zero), 8), bytes(zero))
        zero[5] = 1
        with self.assertRaises(ValueError):
            boost_vertices(bytes(zero), 1)

    def test_atlas_only_changes_c0(self):
        original = bytearray(436)
        struct.pack_into('>2f', original, 8, 13.25, 7.0)
        changed = boost_atlas(original, 4)
        self.assertEqual(struct.unpack_from('>f', changed, 8)[0], 26.5)
        self.assertEqual(changed[:8] + changed[12:], original[:8] + original[12:])

    def test_default_and_other_map_confinement(self):
        other = SimpleNamespace(mcc=True, tags={0: {'group': 'scnr'}}, name=lambda _: 'other')
        configure(other, 0)
        self.assertEqual(boost_vertices(bytes(20), 0), bytes(20))
        with self.assertRaises(ValueError):
            configure(other, 4)


if __name__ == '__main__':
    unittest.main()
