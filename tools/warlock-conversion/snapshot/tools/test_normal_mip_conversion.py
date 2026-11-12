"""Regression: V16U16 conversion must retain and quantize every selected mip."""
import unittest
from unittest.mock import patch

import numpy as np

from encode_bitmap import encode_bitmap_base
from xbox_mip_chain import tile_chain


class NormalMipConversion(unittest.TestCase):
    def test_selected_chain_preserves_small_levels_and_signed_extremes(self):
        # Distinct values at each level expose accidental reuse of the base.
        levels = []
        for level in range(7):
            side = max(1, 64 >> level)
            values = np.resize(np.array([-32768, -16384, 0, 16384, 32767,
                                         level * 1000], dtype='<i2'), side * side * 2)
            levels.append(values.tobytes())

        class Source:
            def info(self, tag):
                return [dict(width=64, height=64, format=29, mips=7, kind=0, curve=0)]

            def pixels(self, tag, index):
                return b''.join(levels)

        observed = []

        def check_chain(payload, width, height, count, fmt):
            observed.append((width, height, count, fmt))
            # Independent scalar reference, including the -32768 endpoint.
            source = np.frombuffer(b''.join(levels[1:]), dtype='<i2')
            expected = bytes((max(-127, min(127, round(max(-32767, int(v))
                                                       * 127 / 32767))) & 255)
                             for v in source)
            self.assertEqual(payload, expected)
            return tile_chain(payload, width, height, count, fmt)

        with patch('xbox_mip_chain.tile_chain', check_chain):
            record, control, raw = encode_bitmap_base(Source(), 0, max_dimension=32,
                                                      preserve_normal_mips=True)
        self.assertEqual(observed, [(32, 32, 6, 22)])
        self.assertEqual(record[20], 5)
        self.assertTrue(raw)


if __name__ == '__main__':
    unittest.main()
