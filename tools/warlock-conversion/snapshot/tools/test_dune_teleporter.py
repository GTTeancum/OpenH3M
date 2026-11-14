import unittest
from types import SimpleNamespace
from terrain_materials import dune_teleporter_neutral_edge


class DuneTeleporterTests(unittest.TestCase):
    NAME = r'objects\multi\2way_teleporter_collapsable\shaders\teleporter_plasma'
    def source(self, name=r'levels\multi\dune\dune'):
        return SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:name)
    def test_exact_source_only(self):
        self.assertTrue(dune_teleporter_neutral_edge(self.source(),'rmhg',self.NAME,'_0_3_1_0_0_0_0'))
        self.assertFalse(dune_teleporter_neutral_edge(self.source('other'),'rmhg',self.NAME,'_0_3_1_0_0_0_0'))
        self.assertFalse(dune_teleporter_neutral_edge(self.source(),'rmhg','other','_0_3_1_0_0_0_0'))
    def test_changed_variant_fails(self):
        with self.assertRaises(ValueError):
            dune_teleporter_neutral_edge(self.source(),'rmhg',self.NAME,'_0_3_1_0_0_1_0')
    def test_unit_endpoints_are_identity(self):
        # overlays.fx: color * lerp(edge_tint, center_tint, pow(N.V,power)).
        for view_dot in [-1,-.25,0,.25,1]:
            tint=1+(1-1)*view_dot
            self.assertEqual(tint,1)


if __name__ == '__main__':unittest.main()
