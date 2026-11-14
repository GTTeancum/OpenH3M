"""Per-image runtime datarefs, not cumulative editor offsets, locate MCC pixels."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mcc_bitmap_source import BitmapSource


class BitmapResourcePixelTests(unittest.TestCase):
    def fixture(self):
        source = BitmapSource.__new__(BitmapSource)
        source.c = object()
        info = dict(size=9, high_size=5, pixel_offset=9999, high_offset=8888, resource=42)
        source.info = lambda _: [info, info]
        resource = SimpleNamespace(raw=[b'xxLOW!tail', b'zHIGH?tail'],
            fix={12: 0x40000002, 32: 0x60000001},
            unpack=lambda fmt, at: (4 if at == 0 else 5,))
        return source, resource, info

    def test_uses_per_image_fixups_and_validated_lengths(self):
        source, resource, _ = self.fixture()
        with patch('resource_reader.Resource', return_value=resource):
            self.assertEqual(source.pixels(7, 1), b'HIGH?LOW!')

    def test_rejects_unsupported_segment_truncation_and_length_mismatch(self):
        for failure in ('segment', 'length', 'truncated'):
            source, resource, info = self.fixture()
            if failure == 'segment': resource.fix[12] = 0x60000002
            elif failure == 'length': info['size'] = 10
            else: resource.raw[0] = b'xxLO'
            with patch('resource_reader.Resource', return_value=resource):
                with self.assertRaises(ValueError): source.pixels(7)


if __name__ == '__main__': unittest.main()
