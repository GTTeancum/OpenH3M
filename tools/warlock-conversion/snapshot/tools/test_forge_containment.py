"""Regression checks for divider coverage of the original containment shell."""
import unittest
from forge_gulch_containment import split_vertical_extent, triangles


def row(vertices):
    return [0.]*8 + [component for vertex in vertices for component in vertex]


class ContainmentExtentTests(unittest.TestCase):
    def test_island_pushes_inward_and_preserves_outer_shell(self):
        outer = row([(-130., 0., -147.), (184., 0., 75.), (0., 1., 0.)])
        class Source:
            def block(self, at, stride):
                return [100] if at == 16 else [200]
            def unpack(self, fmt, at):
                return (0, 0) if fmt == 'hh' else tuple(outer)
        gulch, _ = triangles(Source(), 0, 'gulch')
        island, _ = triangles(Source(), 0, 'island')
        self.assertEqual(island[0], gulch[0])
        self.assertEqual(len(island), 17)
        for a, b in zip(gulch[1:], island[1:]):
            self.assertLess(a[1], 0)
            self.assertGreater(b[1], 0)
            for x, y in zip(a[:4], b[:4]):
                self.assertAlmostEqual(x, -y)

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
