import unittest
import numpy as np
from native_dither_overlay import decode_native_dither
from hologram_overlay import sample


class NativeDitherTests(unittest.TestCase):
    PAYLOAD = bytes.fromhex(
        '00300c3c03330f3f083804340b3b073720102c1c23132f1f281824142b1b2717'
        '02320e3e01310d3d0a3a06360939053522122e1e21112d1d2a1a261629192515')

    def test_native_swizzle_and_linear_values(self):
        rgb = decode_native_dither(self.PAYLOAD)
        expected = np.array([[0,48,12,60,3,51,15,63],
                             [32,16,44,28,35,19,47,31],
                             [8,56,4,52,11,59,7,55],
                             [40,24,36,20,43,27,39,23],
                             [2,50,14,62,1,49,13,61],
                             [34,18,46,30,33,17,45,29],
                             [10,58,6,54,9,57,5,53],
                             [42,26,38,22,41,25,37,21]], dtype=np.float32)/255
        np.testing.assert_array_equal(rgb, np.repeat(expected[:,:,None], 3, axis=2))
        np.testing.assert_array_equal(sample(rgb, 8, 8), rgb)

    def test_fail_closed_for_wrong_size_or_pixels(self):
        for data in [self.PAYLOAD[:-1], self.PAYLOAD+b'\0', bytes(64)]:
            with self.assertRaises(ValueError):
                decode_native_dither(data)


if __name__ == '__main__':
    unittest.main()
