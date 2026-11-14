from types import SimpleNamespace
import struct
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from dune_inactive_ai import (BUILD, SCENARIO, NOTE, NULL_REFERENCE, prepare,
                              clear_native_sector_pairs, sanitize_navigation,
                              palette_slot, remap_palettes, require_inactive_state,
                              reference_frame_schemas, validate_rows, validate_source)


class DuneInactiveAITests(unittest.TestCase):
    def source(self, name=SCENARIO, build=BUILD):
        return SimpleNamespace(tags={1: dict(group='scnr', offset=0)},
            name=lambda _: name, data=bytes(0xa0) + build.encode().ljust(32, b'\0'))

    def test_other_map_is_untouched_and_changed_source_fails_closed(self):
        self.assertIsNone(validate_source(self.source('another map'), None))
        with self.assertRaisesRegex(ValueError, 'exact audited source'):
            validate_source(self.source(), None)
        with self.assertRaisesRegex(ValueError, 'exact audited source'):
            validate_source(self.source(build='new build'), None)

    def test_activation_changes_are_rejected(self):
        original = [0, [0, 0], [-1, -1], [bytes(32), bytes(32)], [-1, -1]]
        require_inactive_state(*original)
        changes = [(0, 1 << 4), (1, [0, 1]), (1, [1, 0]), (1, [0]),
                   (2, [-1, 0]), (3, [bytes(32), b'spawn']), (4, [-1, 0])]
        for index, value in changes:
            with self.subTest(index=index, value=value):
                args = list(original)
                args[index] = value
                with self.assertRaisesRegex(ValueError, 'activation state'):
                    require_inactive_state(*args)

    def test_changed_rows_or_counts_cannot_reuse_editor_guard(self):
        for label, rows in [('Squads', []), ('Squads', [bytes(64)]),
                            ('Character Palette', [bytes(16)] * 3),
                            ('Fire-Teams', [bytes(95)])]:
            with self.subTest(label=label, count=len(rows)):
                with self.assertRaisesRegex(ValueError, 'records changed'):
                    validate_rows(label, rows)

    def schema(self, size='0x10', kind='tagRef'):
        return ET.fromstring(f'<plugin><tagblock name="Character Palette" '
            f'offset="0x3b0" elementSize="{size}"><{kind} name="Character" '
            f'offset="0" /></tagblock></plugin>')

    def test_exact_four_native_null_slots_and_applied_note(self):
        i = SimpleNamespace(source=self.source())
        with patch('dune_inactive_ai.validate_source', return_value={'verified': True}):
            result = prepare(i, None, self.schema())
        self.assertEqual(result, {'Character Palette': (4, NULL_REFERENCE * 4)})
        self.assertEqual(struct.unpack('>4I', NULL_REFERENCE), (0xffffffff, 0, 0, 0xffffffff))
        self.assertEqual(i.scenario_compatibility_notes[0]['compatibility_notes'], [NOTE])
        self.assertIn('Forced developer/debug spawning', NOTE)

    def test_native_schema_changes_reject_before_applied_note(self):
        for schema in (self.schema('32'), self.schema(kind='uint32')):
            i = SimpleNamespace(source=self.source())
            with patch('dune_inactive_ai.validate_source', return_value={'verified': True}):
                with self.assertRaisesRegex(ValueError, 'native character palette schema'):
                    prepare(i, None, schema)
            self.assertFalse(hasattr(i, 'scenario_compatibility_notes'))

    def test_unmatched_source_adds_no_palette_or_note(self):
        i = SimpleNamespace(source=self.source('another map'))
        self.assertIsNone(prepare(i, None, self.schema()))
        self.assertFalse(hasattr(i, 'scenario_compatibility_notes'))

    def test_unplaced_native_identity_appends_without_changing_existing_indices(self):
        old = b'weap' + bytes(8) + struct.pack('>I', 0x12345678) + bytes(32)
        index, count, payload, appended = palette_slot(old, 1, 'weap', 0x87654321)
        self.assertEqual((index, count, appended), (1, 2, True))
        self.assertEqual(payload[:48], old)
        self.assertEqual(struct.unpack_from('>I', payload, 60)[0], 0x87654321)
        self.assertEqual(palette_slot(payload, 2, 'weap', 0x87654321), (1, 2, payload, False))

    def test_ambiguous_or_malformed_native_palette_rejects(self):
        row = b'vehi' + bytes(8) + struct.pack('>I', 1) + bytes(32)
        for payload, count, group, datum in [(row, 2, 'vehi', 1),
                (row + row, 2, 'vehi', 1), (row, 1, 'weap', 1), (row, 1, 'vehi', 0xffffffff)]:
            with self.assertRaises(ValueError):
                palette_slot(payload, count, group, datum)

    def test_unscoped_importer_has_no_ai_palette_changes(self):
        self.assertEqual(remap_palettes(SimpleNamespace(), None, None, None), [])

    def test_reference_frame_id_is_not_relocated_as_a_tag(self):
        node = ET.fromstring('<tagblock name="Reference Frames" elementSize="16">'
                             '<datum name="Unique ID" offset="0" /></tagblock>')
        first, second = reference_frame_schemas(node, node)
        self.assertEqual(first[0].tag, 'uint32')
        self.assertEqual(second[0].tag, 'uint32')
        self.assertEqual(node[0].tag, 'datum')
        node.set('elementSize', '32')
        with self.assertRaisesRegex(ValueError, 'identity layout'):
            reference_frame_schemas(node, node)

    def builder(self):
        memory = bytearray(range(80))
        return SimpleNamespace(memory=memory,
            read=lambda at, length: bytes(memory[at:at + length]),
            put=lambda at, fmt, *values: struct.pack_into('>' + fmt, memory, at, *values))

    def test_sector_none_changes_only_the_verified_four_byte_pairs(self):
        builder = self.builder()
        builder.put(24, 'hh', 0, 660)
        builder.put(48, 'hh', 0, 46)
        old = bytes(builder.memory)
        clear_native_sector_pairs(builder, [(24, (0, 660)), (48, (0, 46))])
        expected = bytearray(old)
        expected[24:28] = expected[48:52] = b'\xff' * 4
        self.assertEqual(builder.memory, expected)

    def test_bad_late_sector_pair_prevents_all_writes(self):
        builder = self.builder()
        builder.put(24, 'hh', 0, 660)
        old = bytes(builder.memory)
        with self.assertRaisesRegex(ValueError, 'sector reference changed'):
            clear_native_sector_pairs(builder, [(24, (0, 660)), (48, (0, 46))])
        self.assertEqual(builder.memory, old)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            clear_native_sector_pairs(builder, [(24, (0, 660)), (26, (0, 46))])
        self.assertEqual(builder.memory, old)

    def test_sector_repair_requires_complete_empty_graph_proof(self):
        self.assertEqual(sanitize_navigation(SimpleNamespace(), None, None), [])
        for counts in (None, (0,) * 7, (0,) * 7 + (1,)):
            from dune_inactive_ai import SOURCE_SHA256
            i = SimpleNamespace(dune_inactive_ai_guard={'source_sha256': SOURCE_SHA256},
                                dune_empty_pathfinding_counts=counts)
            with self.assertRaisesRegex(ValueError, 'eight empty graph checks'):
                sanitize_navigation(i, None, None)


if __name__ == '__main__':
    unittest.main()
