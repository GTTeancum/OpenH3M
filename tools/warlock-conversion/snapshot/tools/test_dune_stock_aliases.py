"""Exact native H3 selection; never broad-strip H2 prefixes or unique assets."""
import unittest
from generational_assets import DUNE_STOCK_EQUIVALENTS, stock_aliases


class DuneStockAliasesTests(unittest.TestCase):
    def test_all_audited_entries_are_explicit_native_roots(self):
        aliases = stock_aliases()
        self.assertEqual(len(DUNE_STOCK_EQUIVALENTS), 24)
        for source, target in DUNE_STOCK_EQUIVALENTS.items():
            self.assertEqual(aliases[source], target)
            self.assertTrue(source[1].startswith('h2\\'))
            self.assertFalse(target[1].startswith('h2\\'))
            self.assertIsNone(target[2])

    def test_five_vehicle_equivalents(self):
        aliases = stock_aliases()
        for src, dst in [('ghost', 'ghost'), ('warthog', 'warthog'),
                         ('scorpion', 'scorpion'), ('wraith', 'wraith'),
                         ('h2_banshee', 'banshee')]:
            self.assertEqual(aliases['vehi', f'h2\\objects\\vehicles\\{src}\\{src}'],
                             ('vehi', f'objects\\vehicles\\{dst}\\{dst}', None))

    def test_mounted_turrets_remain_vehicles_not_detached_weapons(self):
        aliases = stock_aliases()
        for source, target in [('h_turret_ap\\h_turret_ap', 'machinegun_turret'),
                               ('c_turret_ap\\c_turret_ap', 'plasma_cannon'),
                               ('c_turret_ap\\h2a_c_turret\\h2a_c_turret', 'plasma_cannon')]:
            self.assertEqual(aliases['vehi', 'h2\\objects\\vehicles\\' + source],
                ('vehi', f'objects\\weapons\\turret\\{target}\\{target}', None))

    def test_unique_vehicles_and_similar_unknown_names_are_not_aliased(self):
        aliases = stock_aliases()
        for name in ['spectre', 'creep', 'ghost_custom', 'warthog_custom']:
            self.assertNotIn(('vehi', f'h2\\objects\\vehicles\\{name}\\{name}'), aliases)
        self.assertNotIn(('scen', r'h2\scenarios\objects\multi\dune\dune_gate\dune_gate'), aliases)

    def test_foundation_golf_ball_uses_native_vehicle_root(self):
        name = r'objects\levels\dlc\shared\golf_ball\golf_ball'
        self.assertEqual(stock_aliases()['bloc', name], ('vehi', name, None))

    def test_existing_alias_and_fresh_result_are_preserved(self):
        key = ('weap', r'h2\objects\weapons\rifle\battle_rifle\battle_rifle')
        self.assertEqual(stock_aliases()[key],
            ('weap', r'objects\weapons\rifle\battle_rifle\battle_rifle', None))
        changed = stock_aliases()
        changed.pop(key)
        self.assertIn(key, stock_aliases())


if __name__ == '__main__':
    unittest.main()
