import unittest
from types import SimpleNamespace
from dune_assets import native_aliases, SCENARIO, SOURCES, LIFT, LIFT_DIFFERENCE, TURRET_SOURCE, TURRET_TARGET


class DuneAssetsTests(unittest.TestCase):
    def source(self, name=SCENARIO):
        return SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:name)
    def test_exact_map_and_audited_light_volumes_only(self):
        aliases=native_aliases(self.source())
        self.assertEqual(len(aliases),3)
        self.assertEqual(aliases['ltvl',TURRET_SOURCE],('ltvl',TURRET_TARGET,None))
        for name in SOURCES:
            self.assertEqual(aliases['ltvl',name],('ltvl',LIFT,None))
            self.assertNotIn(('effe',name),aliases)
            self.assertNotIn(('mach',name),aliases)
        self.assertEqual(native_aliases(self.source('other')), {})
    def test_visual_difference_is_explicit(self):
        self.assertNotEqual(LIFT_DIFFERENCE['source'], LIFT_DIFFERENCE['native'])
        self.assertIn('timing',LIFT_DIFFERENCE['preserved'])


if __name__ == '__main__': unittest.main()
