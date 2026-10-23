"""Focused checks for boundary coverage and retail collision encoding."""
import struct
import unittest
import numpy as np
from forge_gulch_boundary import classify_bounds
from partition_forge_collision import active_tree, partition


class ForgePartitionTests(unittest.TestCase):
    def test_boundary_keeps_canyon_and_coast_but_not_island(self):
        # Authored landmark coordinates, independently selected from material bounds.
        points = np.array([[-55., -120., 5.], [0., -150., 10.],
                           [50., 50., 10.], [-23., -15., 10.]])
        gulch, world = classify_bounds(points, points)
        self.assertEqual(gulch.tolist(), [True, True, False, True])
        self.assertEqual(world.tolist(), [False, False, True, False])

    def test_crossing_box_is_kept_on_both_sides(self):
        gulch, world = classify_bounds([[-40., 65., 0.]], [[-20., 90., 1.]])
        self.assertTrue(gulch[0] and world[0])

    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            active_tree([(0, -1)], [])

    def test_removed_face_and_reversed_plane_roundtrip(self):
        # Two disjoint triangles, one in each halfspace. Keep the negative-X
        # face; its plane orientation must move from bit 31 into retail plane bit 15.
        arrays = [
            [(0, -2147483648, -2147483647)],
            [(1., 0., 0., 0.), (0., 0., 1., 0.)],
            [(0, 0, 1, 0), (0, 0, 1, 1)],
            [(1, -2147483648), (1, -2147483647)], [],
            [(-2147483647, 0, 2, -1, -1, 0, 0), (1, 3, 3, -1, -1, 0, 0)],
            [(0, 1, 1, -1, 0, -1), (1, 2, 2, -1, 0, -1), (2, 0, 0, -1, 0, -1),
             (3, 4, 4, -1, 1, -1), (4, 5, 5, -1, 1, -1), (5, 3, 3, -1, 1, -1)],
            [(-2., 0., 0., 0, 0), (-1., 0., 0., 1, 0), (-1., 1., 0., 2, 0),
             (1., 0., 0., 3, 0), (2., 0., 0., 4, 0), (1., 1., 0., 5, 0)],
        ]
        payloads, maps, report = partition(arrays, [True, False])
        self.assertEqual(maps['surfaces'], {0: 0})
        surface = struct.unpack('>2H3h2B', payloads[5])
        self.assertEqual(surface[5], 0)
        self.assertEqual(surface[0], 0x8000)
        node = struct.unpack('>Q', payloads[0])[0]
        self.assertEqual((node >> 16) & 0xffffff, 0x800000)
        self.assertEqual((node >> 40) & 0xffffff, 0xffffff)
        self.assertEqual(report['surface_loops_roundtrip_verified'], 1)
        self.assertEqual(report['spatial_queries_roundtrip_verified'], 2048)


if __name__ == '__main__':
    unittest.main()
