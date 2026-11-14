"""Drop only unbound source placeholders, never a real or malformed object."""
from types import SimpleNamespace
import struct
import unittest
from scenario_forge import stage_forge, without_empty_entries


class EmptyForgeEntries(unittest.TestCase):
    def test_only_explicit_null_object_entries_are_removed(self):
        values = {12: 0x12340001, 60: 0xffffffff, 108: 0, 156: 0x90000003}
        cache = SimpleNamespace(u=lambda at: values[at])
        self.assertEqual(without_empty_entries(cache, [0, 48, 96, 144], 12), [0, 96, 144])
        # Zero remains for the normal salted-tag validation to reject.
        self.assertEqual(values[108], 0)

    def test_order_and_duplicates_are_preserved(self):
        cache = SimpleNamespace(u=lambda at: 0x12340001)
        rows = [144, 0, 48, 48]
        self.assertEqual(without_empty_entries(cache, rows, 12), rows)
        self.assertEqual(without_empty_entries(cache, [], 12), [])

    def test_valid_null_placeholder_is_recorded_for_both_layouts(self):
        from test_mcc_scenario_records import fixture
        from assemble_scenario import field
        for old in (True, False):
            with self.subTest(old=old):
                importer, source_schema, _ = fixture(old)
                importer.source_strings.text = lambda value: 'empty_label'
                sf = field(source_schema, 'Map Variant Weapon Palette')
                at = 0x1000 + int(sf.get('offset'), 0)
                struct.pack_into('<III', importer.source.data, at, 1, 0x3000 // 4, 0)
                struct.pack_into('<I', importer.source.data, 0x3000 + 12, 0xffffffff)
                result = stage_forge(importer)
                self.assertEqual(result['Map Variant Weapon Palette'], 0)
                self.assertEqual(importer.empty_forge_placeholders[0]['label'], 'empty_label')
                self.assertEqual(importer.empty_forge_placeholders[0]['index'], 0)


if __name__ == '__main__':
    unittest.main()
