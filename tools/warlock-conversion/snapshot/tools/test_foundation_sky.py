import unittest
from types import SimpleNamespace
from foundation_sky import (SCENARIO, MATERIAL, SOURCE_OPTIONS, TARGET_OPTIONS,
                            TEXTURES, CONSTANTS, select_foundation_clouds)


class FoundationSkyTests(unittest.TestCase):
    def source(self, scenario=SCENARIO):
        return SimpleNamespace(tags={0: {'group': 'scnr'}}, name=lambda k: scenario)

    def test_only_inert_mask_differs(self):
        self.assertEqual([i for i, (s, t) in enumerate(zip(SOURCE_OPTIONS, TARGET_OPTIONS))
                          if s != t], [3])
        self.assertEqual(TARGET_OPTIONS[7], 5)
        self.assertTrue(select_foundation_clouds(self.source(), MATERIAL,
                        SOURCE_OPTIONS, TEXTURES, CONSTANTS))

    def test_exact_map_and_material_only(self):
        self.assertFalse(select_foundation_clouds(self.source('other'), MATERIAL,
                         SOURCE_OPTIONS, TEXTURES, CONSTANTS))
        self.assertFalse(select_foundation_clouds(self.source(), 'other',
                         SOURCE_OPTIONS, TEXTURES, CONSTANTS))

    def test_options_and_parameters_fail_closed(self):
        for index in range(13):
            changed = SOURCE_OPTIONS[:]
            changed[index] += 1
            with self.assertRaises(ValueError):
                select_foundation_clouds(self.source(), MATERIAL, changed, TEXTURES, CONSTANTS)
        with self.assertRaises(ValueError):
            select_foundation_clouds(self.source(), MATERIAL, SOURCE_OPTIONS, TEXTURES[::-1], CONSTANTS)
        with self.assertRaises(ValueError):
            select_foundation_clouds(self.source(), MATERIAL, SOURCE_OPTIONS, TEXTURES, CONSTANTS[:-1])


if __name__ == '__main__':
    unittest.main()
