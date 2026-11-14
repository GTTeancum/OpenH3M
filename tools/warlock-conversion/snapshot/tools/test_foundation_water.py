"""Narrow Foundation water selection and no-loss parameter layout checks."""
import unittest
from types import SimpleNamespace
from water_materials import (FOUNDATION_SCENARIO, FOUNDATION_WATER,
    FOUNDATION_VARIANT, foundation_water_mapping, validate_foundation_water_layout,
    VARIANTS)


class FoundationWaterTests(unittest.TestCase):
    def source(self, scenario=FOUNDATION_SCENARIO):
        return SimpleNamespace(tags={0: {'group': 'scnr'}}, name=lambda k: scenario)

    def test_exact_identity_only(self):
        self.assertTrue(foundation_water_mapping(self.source(), FOUNDATION_WATER, FOUNDATION_VARIANT))
        for scenario, material, variant in [
            ('other', FOUNDATION_WATER, FOUNDATION_VARIANT),
            (FOUNDATION_SCENARIO, 'other', FOUNDATION_VARIANT),
            (FOUNDATION_SCENARIO, FOUNDATION_WATER, '_0_1_1_1_2_0_1_1')]:
            self.assertFalse(foundation_water_mapping(self.source(scenario), material, variant))
        self.assertNotIn(FOUNDATION_VARIANT, VARIANTS)

    def test_exact_layout_and_extra_mask_only(self):
        constants = [str(i) for i in range(37)]
        textures = ['wave_displacement_array', 'wave_slope_array', 'watercolor_texture',
                    'environment_map', 'foam_texture', 'foam_texture_detail']
        target = textures[:1] + ['global_shape_texture'] + textures[1:]
        validate_foundation_water_layout(constants, constants, textures, target)
        for sc, tc, st, tt in [(constants, constants[::-1], textures, target),
            (constants[:-1], constants[:-1], textures, target),
            (constants, constants, textures[::-1], target),
            (constants, constants, textures, textures),
            (constants, constants, textures, target + ['unknown'])]:
            with self.assertRaises(ValueError):
                validate_foundation_water_layout(sc, tc, st, tt)

    def test_zero_painted_foam_identity(self):
        # Both-foam differs only by max(auto, blue). Pow(saturate(x),
        # Foundation's positive exponent) is nonnegative; ripple max is shared.
        for height in [-100, 0, .1, .5, 1, 100]:
            auto = min(1, max(0, height)) ** 2
            for ripple in [0, .2, 1]:
                self.assertEqual(max(auto, ripple), max(max(auto, 0), ripple))


if __name__ == '__main__':
    unittest.main()
