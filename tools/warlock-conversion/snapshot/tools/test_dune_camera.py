from types import SimpleNamespace
import unittest
from dune_camera import SCENARIO, BUILD, SSAO, allow_native_camera


class DuneCameraTests(unittest.TestCase):
    def source(self, scenario=SCENARIO):
        data = bytearray(0x400)
        data[0xa0:0xa0 + len(BUILD)] = BUILD
        data[0x2e4:0x2f4] = SSAO
        return SimpleNamespace(data=data, tags={0: {'group': 'scnr'}}, name=lambda k: scenario)

    def test_exact_audited_ssao_is_explicit_fallback(self):
        self.assertTrue(allow_native_camera(self.source(), SCENARIO, 0x200, 0xe4))

    def test_no_other_map_effect_or_grading_is_allowed(self):
        self.assertFalse(allow_native_camera(self.source('other'), SCENARIO, 0x200, 0xe4))
        self.assertFalse(allow_native_camera(self.source(), 'other', 0x200, 0xe4))
        for offset in (0xf4, 0x144):
            self.assertFalse(allow_native_camera(self.source(), SCENARIO, 0x200, offset))

    def test_changed_build_or_ssao_fails_closed(self):
        for offset in [0xa0, *range(0x2e4, 0x2f4)]:
            source = self.source()
            source.data[offset] ^= 1
            with self.assertRaises(ValueError):
                allow_native_camera(source, SCENARIO, 0x200, 0xe4)


if __name__ == '__main__':
    unittest.main()
