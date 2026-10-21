"""MCC signed normal endpoints must reach retail shaders as biased DXN."""
import unittest
from encode_bitmap import mcc_dxn_to_retail, texture_gpu_format


class NormalEncodingTests(unittest.TestCase):
    def test_endpoints_biased_without_reordering_channels_or_selectors(self):
        block = bytes([129, 127, 1, 2, 3, 4, 5, 6, 0, 64, 7, 8, 9, 10, 11, 12])
        self.assertEqual(mcc_dxn_to_retail(block),
            bytes([1, 255, 1, 2, 3, 4, 5, 6, 128, 192, 7, 8, 9, 10, 11, 12]))

    def test_native_normal_fetch_is_biased_linear(self):
        value = texture_gpu_format(33, 3)
        # Independent decoded fields from 181 native BC5 resources in Last
        # Resort and Valhalla: DXN 49, 8-in-16, tiled, bias on XYZW.
        self.assertEqual(value & 63, 49)
        self.assertEqual(value >> 6 & 3, 1)
        self.assertEqual(value >> 8 & 1, 1)
        self.assertEqual([(value >> shift) & 3 for shift in (9, 11, 13, 15)], [2]*4)
        self.assertEqual(value, 0x1a215571)


if __name__ == '__main__':
    unittest.main()
