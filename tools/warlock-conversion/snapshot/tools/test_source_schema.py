"""Regression checks for incompatible MCC layouts and malformed references."""
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

from cache_reader import Cache
from source_schema import REFERENCE, MCC_2022_BUILD, load_schema, profile, schema_path, validate_tree


def source(build=MCC_2022_BUILD, mcc=True):
    data = bytearray(0xC0)
    data[0xA0:0xA0 + len(build)] = build.encode('ascii')
    return SimpleNamespace(mcc=mcc, data=data)


def field(schema, name):
    return next(n for n in schema if n.get('name') == name)


class SourceSchemaTests(unittest.TestCase):
    def test_2022_scenario_keeps_preupdate_palette_and_environment_layouts(self):
        schema = load_schema(source(), 'scnr')
        self.assertEqual(schema.get('baseSize'), '0x7B8')
        for name, offset, stride in (
            ('Structure BSPs', '0x14', '0x6C'),
            ('Scenery Palette', '0xC8', '0x30'),
            ('Map Variant Weapon Palette', '0x1F4', '0x30'),
            ('Zone Sets', '0x54', '0x24'),
            ('Scenario Cluster Data', '0x534', '0x68'),
        ):
            node = field(schema, name)
            self.assertEqual((node.get('offset'), node.get('elementSize')), (offset, stride))

    def test_modern_and_retail_schema_selection_preserved(self):
        modern = source('May 30 2023 12:00:00')
        native = source(mcc=False)
        self.assertEqual(profile(modern), 'mcc')
        self.assertEqual(schema_path(modern, 'scnr'), REFERENCE / 'mcc/scnr.xml')
        self.assertEqual(schema_path(native, 'scnr'), REFERENCE / 'plugins/scnr.xml')
        self.assertEqual(schema_path(source(), 'scen'), REFERENCE / 'plugins/scen.xml')
        self.assertEqual(schema_path(source(), 'mode'), REFERENCE / 'mcc/mode.xml')

    def test_annotations_do_not_leak_to_other_schema_consumers(self):
        schema = load_schema(source(), 'scnr')
        schema.clear()
        self.assertEqual(load_schema(source(), 'scnr').get('baseSize'), '0x7B8')

    def test_unknown_groups_do_not_fall_back_to_newer_layouts(self):
        with self.assertRaises(ValueError):
            load_schema(source(), 'nope')
        with self.assertRaises(ValueError):
            load_schema(source(), '../scnr')

    def test_retained_2022_overrides_match_pinned_upstream_blobs(self):
        manifest = json.loads((REFERENCE / 'mcc-2022/manifest.json').read_text(encoding='utf-8'))
        for item in manifest['files']:
            path = REFERENCE / item['schema']
            self.assertTrue(path.is_file(), item['file'])
            if item['schema'].startswith('mcc-2022/'):
                # Git may check text out with CRLF; the pinned upstream blobs use LF.
                data = path.read_bytes().replace(b'\r\n', b'\n')
                blob = b'blob ' + str(len(data)).encode('ascii') + b'\0' + data
                self.assertEqual(hashlib.sha1(blob).hexdigest(), item['git_blob'], item['file'])

    def fixture(self):
        cache = Cache.__new__(Cache)
        cache.data = bytearray(0x200)
        cache.mcc, cache.endian, cache.base, cache.start = True, '<', 0, 0
        cache.tags = {3: dict(group='scen', salt=0xABCD, offset=0x180)}
        struct.pack_into('<II', cache.data, 0, 1, 0x100 // 4)
        cache.data[0x100:0x104] = b'necs'
        struct.pack_into('<I', cache.data, 0x10C, 0xABCD0003)
        schema = ET.fromstring('<plugin><tagblock name="Objects" offset="0" elementSize="16">'
                               '<tagRef name="Object" offset="0" /></tagblock></plugin>')
        return cache, schema

    def test_nested_references_are_validated(self):
        cache, schema = self.fixture()
        report = validate_tree(cache, 0, schema)
        self.assertTrue(report['valid'])
        self.assertEqual(report['counts']['tag_references'], 1)
        struct.pack_into('<I', cache.data, 0x10C, 0xABCE0003)
        report = validate_tree(cache, 0, schema)
        self.assertFalse(report['valid'])
        self.assertIn('Objects[0]/Object', report['errors'][0]['field'])

    def test_wrong_group_and_out_of_bounds_block_are_rejected(self):
        cache, schema = self.fixture()
        cache.data[0x100:0x104] = b'paew'
        self.assertFalse(validate_tree(cache, 0, schema)['valid'])
        struct.pack_into('<I', cache.data, 0, 10000)
        report = validate_tree(cache, 0, schema)
        self.assertFalse(report['valid'])
        self.assertIn('bounds', report['errors'][0]['error'])

    def test_native_packed_simulation_references_have_no_group_prefix(self):
        cache, _ = self.fixture()
        cache.mcc, cache.endian = False, '>'
        struct.pack_into('>I', cache.data, 0, 0xABCD0003)
        schema = ET.fromstring('<plugin><tagRef name="Tag" offset="0" withGroup="false" /></plugin>')
        report = validate_tree(cache, 0, schema)
        self.assertTrue(report['valid'])
        self.assertEqual(report['counts']['tag_references'], 1)


if __name__ == '__main__':
    unittest.main()
