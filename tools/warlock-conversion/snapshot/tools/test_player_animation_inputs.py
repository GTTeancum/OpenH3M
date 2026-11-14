"""Missing native animation inputs must fail explicitly, never silently omit."""
from pathlib import Path
from types import SimpleNamespace
import unittest

from player_animations import add_shade_mode


class PlayerAnimationInputs(unittest.TestCase):
    def test_missing_guardian_has_actionable_error(self):
        name = r'objects\characters\masterchief\masterchief'
        for candidates in ({}, {('jmad', name): [(Path('armory.map'), 1)]}):
            importer = SimpleNamespace(builder=None,
                native_assets=SimpleNamespace(candidates=candidates))
            with self.subTest(candidates=candidates), self.assertRaisesRegex(
                    ValueError, r'Shade animation donor guardian\.map is required'):
                add_shade_mode(importer, name, 0, None)


if __name__ == '__main__':
    unittest.main()
