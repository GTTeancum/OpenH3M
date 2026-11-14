"""Xbox tiled-address regressions, including NumPy 2 unsigned masks."""
import unittest

import numpy as np

from xbox_bitmap import addresses, tile_base, untile_base


def scalar_address(x, y, pitch, log_bytes_per_block):
    """Independent XGAddress2DTiledOffset algebra using Python integers.

    Retained from check_texture_encoding.py, which compares the separate
    XG macro/micro-tile formulation with the vectorized Xenia formulation.
    """
    aligned = (pitch + 31) & ~31
    macro = ((x >> 5) + (y >> 5) * (aligned >> 5)) << (log_bytes_per_block + 7)
    micro = ((x & 7) + ((y & 6) << 2)) << log_bytes_per_block
    offset = (macro + ((micro & ~15) << 1) + (micro & 15)
              + ((y & 8) << (3 + log_bytes_per_block)) + ((y & 1) << 4))
    return ((offset & ~511) << 3) + ((offset & 448) << 2) + (offset & 63) \
        + ((y & 16) << 7) + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6)


class XboxBitmapTests(unittest.TestCase):
    def test_addresses_match_scalar_oracle_across_tile_boundaries(self):
        # Include subtiles, complete macrotiles, and unaligned row pitches.
        for width, height in ((1, 1), (7, 15), (31, 33), (32, 32), (33, 65), (257, 129)):
            for bytes_per_block in (2, 4, 8, 16):
                with self.subTest(width=width, height=height, bytes_per_block=bytes_per_block):
                    actual = addresses(width, height, bytes_per_block)
                    expected = np.array([
                        [scalar_address(x, y, width, bytes_per_block.bit_length() - 1)
                         for x in range(width)] for y in range(height)
                    ], dtype=np.uint32)
                    self.assertEqual(actual.dtype, np.dtype(np.uint32))
                    np.testing.assert_array_equal(actual, expected)
                    self.assertEqual(len(np.unique(actual)), width * height)

    def test_supported_base_formats_roundtrip_across_tile_boundaries(self):
        for fmt in (11, 14, 15, 16, 22, 26, 28, 33):
            with self.subTest(fmt=fmt):
                width, height = 133, 69
                uncompressed = fmt in (11, 22, 26, 28)
                block_width = width if uncompressed else (width + 3) // 4
                block_height = height if uncompressed else (height + 3) // 4
                bytes_per_block = 4 if fmt in (11, 26) else 2 if fmt == 22 else 8 if fmt in (14, 28) else 16
                payload = bytes((index * 37 + index // 251) & 255
                                for index in range(block_width * block_height * bytes_per_block))
                tiled = tile_base(payload, width, height, fmt)
                self.assertEqual(len(tiled) % 4096, 0)
                self.assertEqual(untile_base(tiled, width, height, fmt), payload)


if __name__ == '__main__':
    unittest.main()
