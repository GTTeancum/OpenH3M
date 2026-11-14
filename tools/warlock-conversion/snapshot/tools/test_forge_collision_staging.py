"""Geometry-only staging preserves polygons and keeps native output guards."""
import copy
import struct
import unittest
from forge_collision_staging import stage_geometry, verify_polygons
from forge_partition_cache import validate_native
from partition_forge_collision import partition
from rebuild_forge_collision import FORMATS


def triangle():
    return [[(0,-2147483648,-1)],[(0.,0.,1.,0.)],[(0,0,1,0)],
        [(0,-2147483648)],[],[(0,0,2,-1,-1,0,0)],
        [(0,1,1,-1,0,-1),(1,2,2,-1,0,-1),(2,0,0,-1,0,-1)],
        [(0.,0.,0.,0,0),(1.,0.,0.,1,0),(0.,1.,0.,2,0)]]


def decode(payloads):
    return [list(struct.iter_unpack('>'+fmt,p)) for fmt,p in zip(FORMATS,payloads)]


class StagingTests(unittest.TestCase):
    def test_geometry_identical_to_old_native_staging(self):
        src=triangle()
        before,oldmaps,_=partition(src,[True])
        after,maps,report=stage_geometry(src,[True])
        for n in (1,5,6,7):self.assertEqual(before[n],after[n])
        for name in ('surfaces','edges','vertices'):self.assertEqual(maps[name],oldmaps[name])
        for n in (0,2,3,4):self.assertEqual(after[n],b'')
        self.assertEqual(report['surface_loops_roundtrip_verified'],1)

    def test_unbounded_source_plane_and_signed_orientation(self):
        src=triangle();src[1]=[(0.,0.,1.,0.)]*70000
        src[5][0]=(-2147413649,0,2,-1,-1,0,0) # sign bit plus plane 69999
        data,maps,_=stage_geometry(src,[True]);a=decode(data)
        self.assertEqual(a[5][0][0],32768)
        self.assertEqual(len(a[1]),1)
        self.assertEqual(maps['planes'],{69999:0})
        verify_polygons(src,a,maps)

    def test_empty_selection_and_ambiguous_orientation_rejected(self):
        with self.assertRaises(ValueError):stage_geometry(triangle(),[False])
        src=triangle();src[5][0]=(0,0,2,-1,-1,128,0)
        with self.assertRaisesRegex(ValueError,'Ambiguous'):stage_geometry(src,[True])

    def test_geometry_tampering_rejected(self):
        src=triangle();data,maps,_=stage_geometry(src,[True]);a=decode(data)
        a[7][0]=(2.,0.,0.,0,0)
        with self.assertRaisesRegex(ValueError,'vertex cycle'):verify_polygons(src,a,maps)

    def test_native_final_budgets_and_cycles_still_rejected(self):
        arrays=[[],[],[],[],[],[],[],[]]
        bad=copy.deepcopy(arrays);bad[1]=[(0.,0.,1.,0.)]*32769
        with self.assertRaisesRegex(ValueError,'budgets'):validate_native(bad,b'')
        bad=copy.deepcopy(arrays);bad[0]=[(0xffffff<<40,)];bad[1]=[(0.,0.,1.,0.)]
        with self.assertRaisesRegex(ValueError,'Cyclic'):validate_native(bad,b'')
        bad=copy.deepcopy(arrays);bad[2]=[(0,0,0,0)]
        with self.assertRaisesRegex(ValueError,'cluster'):validate_native(bad,b'\xff')

if __name__=='__main__':unittest.main()
