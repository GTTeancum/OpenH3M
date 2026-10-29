"""Regression for the retail four-coefficients-per-element PRT layout."""
import struct
import unittest
from types import SimpleNamespace
from render_resource import convert_render_resource


class AmbientPrtTest(unittest.TestCase):
    def test_native_packed_coefficients_and_descriptor(self):
        # Native Xbox reader consumes one UNORM8 per primary vertex, while
        # the resource descriptor counts four-byte groups, rounded upward.
        header = struct.pack('<IHHI', 6, 9, 4, 24) + bytes(16)
        source = SimpleNamespace(
            raw=[struct.pack('<6f', 0, .25, .5, .75, 1, .2820937)],
            fix={20: 0x40000000},
            buffers=lambda kind: [0] if kind == 'vertex' else [],
            unpack=lambda fmt, at: struct.unpack_from('<'+fmt, header, at))
        result = convert_render_resource(source)
        self.assertEqual(result['raw'], bytes.fromhex('004080bfff480000'))
        self.assertEqual(struct.unpack_from('>IHHI', result['control'], 60), (2, 9, 4, 8))


if __name__ == '__main__':
    unittest.main()
