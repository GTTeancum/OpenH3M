"""Spatial invariants for the retail collision/visibility intersection."""
import unittest

from forge_visibility_overlay import hull, overlay, split
from itertools import product
from scipy.spatial import ConvexHull


def locate(nodes, planes, clusters, point):
    node = 0
    while node < 0x800000:
        plane, back, front = nodes[node]
        normal = planes[plane]
        node = front if sum(a*b for a, b in zip(point, normal)) >= normal[3] else back
    return None if node == 0xffffff else clusters[node & 0x7fffff]


class VisibilityOverlayTests(unittest.TestCase):
    def test_oblique_clip_conserves_volume_and_halfspaces(self):
        cube = hull(list(product((-1., 1.), repeat=3)))
        back, front = split(cube, (1., 2., 3., .25))
        self.assertAlmostEqual(ConvexHull(back[0]).volume + ConvexHull(front[0]).volume, 8.)
        self.assertLessEqual(max(back[0] @ [1., 2., 3.] - .25), 1e-12)
        self.assertGreaterEqual(min(front[0] @ [1., 2., 3.] - .25), -1e-12)

    def test_visibility_split_preserves_solid_and_collision_references(self):
        # x < 0 is solid; x >= 0 is an empty collision cell crossing y = 0.
        refs = (0, 0, 3, 17)
        nodes, planes, leaves, clusters, report = overlay(
            [[0, 0xffffff, 0x800000]], [(1., 0., 0., 0.)], [refs],
            [[0, -0x80000000, -0x7fffffff]], [(0., 1., 0., 0.)],
            [[-0x80000000, -0x7fffffff]], [4, 9], ([-1., -1., -1.], [1., 1., 1.]))
        self.assertEqual(locate(nodes, planes, clusters, (-.5, -.5, 0.)), None)
        self.assertEqual(locate(nodes, planes, clusters, (-.5, .5, 0.)), None)
        self.assertEqual(locate(nodes, planes, clusters, (.5, -.5, 0.)), 4)
        self.assertEqual(locate(nodes, planes, clusters, (.5, .5, 0.)), 9)
        self.assertEqual(leaves, [refs, refs])
        self.assertEqual(report['out_of_bounds_cells'], 0)

    def test_equal_cluster_cuts_collapse_without_duplicate_leaves(self):
        nodes, planes, leaves, clusters, _ = overlay(
            [[0, 0xffffff, 0x800000]], [(1., 0., 0., 0.)], [(0, 0, 1, 2)],
            [[0, -0x80000000, -0x7fffffff]], [(0., 1., 0., 0.)],
            [[-0x80000000, -0x7fffffff]], [7, 7], ([-1., -1., -1.], [1., 1., 1.]))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(leaves), 1)
        self.assertEqual(clusters, bytes([7]))


if __name__ == '__main__':
    unittest.main()
