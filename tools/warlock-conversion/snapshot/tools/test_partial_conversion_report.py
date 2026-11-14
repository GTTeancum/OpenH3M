from types import SimpleNamespace
import unittest
from partial_conversion_report import snapshot


class PartialConversionReportTests(unittest.TestCase):
    def test_retains_meaningful_reductions_without_serialization_claim(self):
        importer = SimpleNamespace(added=[dict(source='camera', group='cfxs',
            compatibility_notes=['Explicit SSAO omission']), dict(source='native', group='bitm')],
            materials=SimpleNamespace(report=[dict(source='shield', approximation=True,
                unrepresented_textures=['mask'], converted_source_animations=9),
                dict(source='exact', approximation=False, unrepresented_textures=[])]))
        report = snapshot(importer)
        self.assertEqual(report['total_records'], 2)
        self.assertEqual(report['records'][1]['converted_source_animations'], 9)
        self.assertEqual(report['records'][1]['unrepresented_textures'], ['mask'])
        self.assertIn('incomplete', report['scope'])
        self.assertFalse(report['truncated'])

    def test_bounded_and_safe_before_importer_initialization(self):
        self.assertEqual(snapshot(SimpleNamespace())['records'], [])
        importer = SimpleNamespace(added=[dict(source=str(n), differences=['a']) for n in range(5)])
        report = snapshot(importer, 2)
        self.assertEqual(len(report['records']), 2)
        self.assertEqual(report['total_records'], 5)
        self.assertTrue(report['truncated'])
        with self.assertRaises(ValueError):
            snapshot(importer, 0)

    def test_nested_candidate_visual_description_is_not_lost(self):
        notes = dict(difference='Brighter and differently patterned shield')
        importer = SimpleNamespace(materials=SimpleNamespace(report=[
            dict(source='shield', dune_spectre_candidate=notes)]))
        self.assertEqual(snapshot(importer)['records'][0]['dune_spectre_candidate'], notes)

    def test_scenario_omissions_survive_later_assembly_failure(self):
        importer = SimpleNamespace(scenario_compatibility_notes=[dict(source='dune',
            group='scnr', compatibility_notes=['Four inactive editor actors omitted'],
            inactive_editor_ai_omission={'preserved_slots': 4})])
        row = snapshot(importer)['records'][0]
        self.assertEqual(row['kind'], 'scenario')
        self.assertEqual(row['inactive_editor_ai_omission']['preserved_slots'], 4)
        self.assertIn('omitted', row['compatibility_notes'][0])


if __name__ == '__main__':
    unittest.main()
