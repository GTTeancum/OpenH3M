"""Regression checks for divider coverage of the original containment shell."""
import unittest
from forge_gulch_containment import split_vertical_extent


def row(vertices):
    return [0.]*8 + [component for vertex in vertices for component in vertex]


class ContainmentExtentTests(unittest.TestCase):
    def test_deep_shell_cannot_leave_underpass(self):
        original = [row([(-130., 0., -147.35463), (184., 0., 75.), (0., 1., 0.)])]
        bottom, top = split_vertical_extent(original)
        self.assertLessEqual(bottom, -151.35463)
        self.assertGreaterEqual(top, 79.)

    def test_tall_shell_extends_above_previous_limit(self):
        original = [row([(-130., 0., -20.), (184., 0., 210.), (0., 1., 0.)])]
        self.assertEqual(split_vertical_extent(original), (-40., 214.))

    def test_new_source_cannot_silently_exceed_endpoints(self):
        original = [row([(-251., 0., -20.), (184., 0., 75.), (0., 1., 0.)])]
        with self.assertRaisesRegex(ValueError, 'endpoints'):
            split_vertical_extent(original)
