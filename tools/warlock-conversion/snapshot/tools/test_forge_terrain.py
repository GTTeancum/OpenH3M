import unittest
import numpy as np
from PIL import Image
from encode_bitmap import clear_bc3_blue


class TerrainBlendTests(unittest.TestCase):
    def test_inactive_blue_zero_preserves_all_other_decoded_channels(self):
        # Includes endpoint-order reversals/equality after masking blue.
        payload = np.random.default_rng(17).integers(0, 256, 4096, dtype=np.uint8).tobytes()
        before = np.asarray(Image.frombytes('RGBA', (64, 64), payload, 'bcn', 3))
        after = np.asarray(Image.frombytes('RGBA', (64, 64), clear_bc3_blue(payload), 'bcn', 3))
        self.assertTrue(np.array_equal(before[:, :, [0, 1, 3]], after[:, :, [0, 1, 3]]))
        self.assertFalse(after[:, :, 2].any())

    def test_partial_bc3_block_rejected(self):
        with self.assertRaises(ValueError):
            clear_bc3_blue(bytes(15))


if __name__ == '__main__':
    unittest.main()
