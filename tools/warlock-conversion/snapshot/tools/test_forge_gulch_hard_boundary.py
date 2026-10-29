import unittest
import numpy as np
from forge_gulch_boundary import BOUNDARY
from forge_gulch_hard_boundary import append_surfaces, extend_mopp
from forge_collision_mesh import surface_loops, positions
from audit_forge_camera_collision import crossings
from forge_mopp import terminals
from collision_physics import retail_mopp


class HardBoundaryTests(unittest.TestCase):
    def test_each_segment_blocks_both_directions_without_render_material(self):
        arrays = [[] for _ in range(8)]
        proof = append_surfaces(arrays)
        arrays[6] = [tuple(-1 if v == 65535 else v for v in row) for row in arrays[6]]
        xyz = positions(arrays)
        triangles = np.array([xyz[loop] for loop in surface_loops(arrays)])
        self.assertEqual(proof['surface_count'], 16)
        self.assertTrue(all(s[2] == -1 and s[5] == 1 for s in arrays[5]))
        for a, b in zip(BOUNDARY, BOUNDARY[1:]):
            midpoint = (np.array(a)+b)/2
            for height in (-30, 0, 65, 185):
                p = [*midpoint, height]
                q = list(p)
                p[1] -= 2
                q[1] += 2
                for start, end in ((p,q),(q,p)):
                    hits = crossings(triangles, list(range(16)), [
                        {'position':start,'seconds':0}, {'position':end,'seconds':1}])
                    self.assertTrue(hits, (a,b,height))

    def test_mopp_keeps_old_keys_and_adds_native_wildcard_category(self):
        divider = {'surface_first':100, 'surface_count':16}
        old = b'\x0b\x40\x00\x00\x12\x30'
        result = extend_mopp(old, (0,0,-100,32768), (-50,200), divider)
        self.assertTrue(result.endswith(old))
        keys = [k for _,_,k in terminals(retail_mopp(result))]
        self.assertCountEqual(keys, [0x40000012]+[0x20050000+i for i in range(100,116)])

    def test_rejects_world_outside_branch_domain(self):
        with self.assertRaises(ValueError):
            extend_mopp(b'\x30', (0,0,0,32768), (-1,100),
                        {'surface_first':1,'surface_count':16})


if __name__ == '__main__':
    unittest.main()
