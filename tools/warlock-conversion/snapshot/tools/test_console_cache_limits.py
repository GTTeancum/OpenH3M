"""Native export gates use serialized limits, not successful host loading."""
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

from cache_reader import Cache
from console_cache_limits import (MYTHIC_CACHE_LIMITS, inspect_map,
                                  inspect_native_budget, require_native_budget)
from source_schema import load_schema
from test_cache_finalization import native_cache


class ConsoleCacheLimits(unittest.TestCase):
    def setUp(self):
        work = Path(__file__).resolve().parents[4] / 'work'
        work.mkdir(exist_ok=True)
        directory = tempfile.TemporaryDirectory(prefix='console-budget-', dir=work)
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def sparse_header(self, size, kind=1):
        path = self.directory / 'size.map'
        header = bytearray(0x3000)
        header[:4], header[-4:] = b'head', b'foot'
        struct.pack_into('>II', header, 4, 11, size)
        struct.pack_into('>h', header, 0x13c, kind)
        with path.open('wb') as stream:
            stream.write(header)
            stream.truncate(size)
        return path

    def test_exact_native_file_limit_and_one_byte_over(self):
        for kind, limit in enumerate(MYTHIC_CACHE_LIMITS):
            with self.subTest(kind=kind):
                report = inspect_map(self.sparse_header(limit, kind))
                self.assertTrue(report['within_limit'])
                self.assertEqual(report['cached_console_limit_bytes'], limit)
                report = inspect_map(self.sparse_header(limit + 1, kind))
                self.assertFalse(report['within_limit'])
                self.assertEqual(report['excess_bytes'], 1)

    def test_bad_version_type_or_declared_size_is_rejected(self):
        for offset, fmt, value in ((4, '>I', 13), (0x13c, '>h', -1),
                                    (0x13c, '>h', 5), (8, '>I', 0)):
            with self.subTest(offset=offset, value=value):
                path = self.sparse_header(0x3000)
                with path.open('r+b') as stream:
                    stream.seek(offset)
                    stream.write(struct.pack(fmt, value))
                with self.assertRaises(ValueError):
                    inspect_map(path)

    def scenario(self, placements=0, quotas=0):
        data, layout = native_cache()
        # Large enough for the complete placement array, not merely a count.
        data.extend(bytes(0x40000 - len(data)))
        struct.pack_into('>I', data, 8, len(data))
        schema = load_schema(type('Native', (), {'mcc': False})(), 'scnr')
        fields = {f.get('name'): f for f in schema}
        for label, count, relative in (('Scenery', placements, 0x10000),
                                       ('Map Variant Vehicle Palette', quotas, 0x6000)):
            field = fields[label]
            stride = int(field.get('elementSize'), 0)
            struct.pack_into('>III', data, layout.scenario + int(field.get('offset'), 0),
                             count, layout.base + relative, 0)
            for index in range(count):
                at = layout.start + relative + index * stride
                if label == 'Scenery':
                    struct.pack_into('>h', data, at, -1)
                else:
                    # Repeated rows still each consume a Forge palette slot.
                    struct.pack_into('>I', data, at + 12, 0x12340002)
        return data

    def inspect(self, data):
        path = self.directory / 'native.map'
        path.write_bytes(data)
        cache = Cache(path)
        try:
            return inspect_native_budget(cache, path)
        finally:
            cache.close()

    def test_serialized_native_placement_and_quota_boundaries(self):
        report = self.inspect(self.scenario(640, 256))
        self.assertEqual(report['placements']['total'], 640)
        self.assertEqual(report['forge_quotas']['conservative_upper_bound'], 256)
        self.assertIs(require_native_budget(report), report)
        for placements, quotas, message in ((641, 256, 'placements 641 > 640'),
                                             (640, 257, 'quota bound 257 > 256')):
            with self.subTest(placements=placements, quotas=quotas):
                with self.assertRaisesRegex(ValueError, message):
                    require_native_budget(self.inspect(self.scenario(placements, quotas)))

    def test_failure_reports_all_three_budgets(self):
        report = self.inspect(self.scenario(641, 257))
        report['file'].update(within_limit=False, file_bytes=157286401,
                              cached_console_limit_bytes=157286400)
        with self.assertRaises(ValueError) as error:
            require_native_budget(report)
        self.assertIn('cache file 157286401 > 157286400', str(error.exception))
        self.assertIn('placements 641 > 640', str(error.exception))
        self.assertIn('quota bound 257 > 256', str(error.exception))

    def test_dlc_does_not_create_output_for_overbudget_source(self):
        from build_dlc_payload import build
        converted, stock = self.directory / 'converted', self.directory / 'stock'
        converted.mkdir(); (stock / 'info').mkdir(parents=True)
        source = converted / 'zanzibar.map'
        data = self.scenario(641, 0)
        source.write_bytes(data)
        output = self.directory / 'payload'
        with mock.patch('build_dlc_payload.resource_salt') as salt:
            with self.assertRaisesRegex(ValueError, 'placements 641 > 640'):
                build(converted, stock, output, [('zanzibar', 'test', 'Test', 1800)])
            salt.assert_not_called()
        self.assertFalse(output.exists())
        self.assertEqual(source.read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
