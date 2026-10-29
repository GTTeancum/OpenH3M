import unittest
import numpy as np
from audit_forge_camera_collision import crossings


class CameraCollisionTests(unittest.TestCase):
    def probe(self, a, b):
        triangle = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
        return crossings(triangle, [17], [{'seconds': 10., 'position': a},
                                         {'seconds': 12., 'position': b}])

    def test_crossing_from_both_sides(self):
        for start, end in ((1., -1.), (-1., 1.)):
            hits = self.probe([.25, .25, start], [.25, .25, end])
            self.assertEqual(hits, [{'seconds': 11., 'position': [.25, .25, 0.], 'surface': 17}])

    def test_outside_triangle_is_not_plane_hit(self):
        self.assertEqual(self.probe([.75, .75, 1.], [.75, .75, -1.]), [])

    def test_parallel_and_short_segments_do_not_hit(self):
        self.assertEqual(self.probe([0., 0., 1.], [1., 0., 1.]), [])
        self.assertEqual(self.probe([.25, .25, 1.], [.25, .25, .1]), [])


if __name__ == '__main__':
    unittest.main()
