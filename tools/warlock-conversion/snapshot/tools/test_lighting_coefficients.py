"""Regression: neutral MCC vertex lighting must remain neutral on retail."""
import unittest
from render_buffers import convert_vertices


class PackedLightingTests(unittest.TestCase):
    def test_neutral_and_signed_coefficients(self):
        # Five independently packed vectors, with neutral and signed endpoints.
        neutral = bytes([127]) * 4
        signed = bytes([0, 127, 254, 127])
        source = neutral + signed + neutral + signed + neutral
        expected = bytes(4) + bytes([0, 127, 0, 129]) + bytes(4) + bytes([0, 127, 0, 129]) + bytes(4)
        payload, stride = convert_vertices(source, 1, 6, 20)
        self.assertEqual(stride, 20)
        self.assertEqual(payload, expected)
        self.assertEqual(convert_vertices(signed, 1, 10, 4), (bytes([0, 127, 0, 129]), 4))


if __name__ == '__main__':
    unittest.main()
