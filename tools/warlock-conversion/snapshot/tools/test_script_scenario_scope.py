"""Reviewed source identities do not bypass compiled-script validation."""
from types import SimpleNamespace
import unittest
from unittest import mock

from scenario_scripts import prepare_scripts


class ScriptScenarioScope(unittest.TestCase):
    def importer(self, name, build='Jan  3 2024 10:08:58'):
        data = bytearray(0xC0)
        data[0xA0:0xA0+len(build)] = build.encode('ascii')
        source = SimpleNamespace(tags={0: {'group': 'scnr'}}, name=lambda _: name,
                                 file=SimpleNamespace(name='source.map'), data=data)
        return SimpleNamespace(source=source)

    def test_foundation_runs_audit_and_rejects_bad_script_graph(self):
        errors = {'unsupported': [], 'opcode_name_mismatches': [], 'graph': {'errors': ['bad handle']}}
        with mock.patch('scenario_scripts.audit', return_value=errors) as audit:
            with self.assertRaisesRegex(ValueError, 'script graph or opcode audit failed'):
                prepare_scripts(self.importer(r'halo_2\levels\foundation\foundation'), None, None, None, 0)
        audit.assert_called_once_with('source.map', 'U14')

    def test_dune_uses_reviewed_u13_and_still_rejects_bad_script_graph(self):
        errors = {'unsupported': [], 'opcode_name_mismatches': [], 'graph': {'errors': ['bad handle']}}
        with mock.patch('scenario_scripts.audit', return_value=errors) as audit:
            with self.assertRaisesRegex(ValueError, 'script graph or opcode audit failed'):
                prepare_scripts(self.importer(r'levels\multi\dune\dune',
                    'Jun 27 2023 08:39:36'), None, None, None, 0)
        audit.assert_called_once_with('source.map', 'U13')

    def test_dune_rejects_unreviewed_build(self):
        with mock.patch('scenario_scripts.audit') as audit:
            with self.assertRaisesRegex(ValueError, 'Dune script build has not been audited'):
                prepare_scripts(self.importer(r'levels\multi\dune\dune'), None, None, None, 0)
        audit.assert_not_called()

    def test_unreviewed_foundation_namespace_is_not_accepted(self):
        for name in (r'unknown\foundation', r'levels\multi\foundation\foundation', r'unknown\dune'):
            with self.subTest(name=name), mock.patch('scenario_scripts.audit') as audit:
                with self.assertRaisesRegex(ValueError, 'has not been audited'):
                    prepare_scripts(self.importer(name), None, None, None, 0)
                audit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
