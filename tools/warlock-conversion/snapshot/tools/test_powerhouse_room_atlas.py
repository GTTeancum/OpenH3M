import unittest
import numpy as np
from powerhouse_room_atlas import raster_mask, encode_c0, decode_c0


class RoomAtlasTests(unittest.TestCase):
    def test_c0_encoding_matches_shader_equation(self):
        values=np.array([[[.25,.24,.22],[-.25,.1,.2],[0.,0.,0.]]])
        a,b=encode_c0(values,53.18854)
        np.testing.assert_allclose(decode_c0(a.astype(float)/255,b.astype(float)/255,53.18854),values,atol=.003)

    def test_mask_uses_world_positions_and_preserves_distant_uvs(self):
        xyz=np.array([[121.,225.,43.],[127.,225.,43.],[121.,228.,43.]])
        uv=np.array([[.25,.25],[.75,.25],[.25,.75]])
        triangles=np.array([[0,1,2]])
        mask=raster_mask([(xyz,uv,triangles,'room')],32,32)
        self.assertEqual(mask[10,10],1.)
        self.assertEqual(mask[0,0],0.)
        self.assertEqual(mask[31,31],0.)
        empty=raster_mask([(xyz+100,uv,triangles,'outside')],32,32)
        self.assertFalse(np.any(empty))
        with self.assertRaises(ValueError):
            raster_mask([(xyz,uv,triangles,'room'),(xyz+100,uv,triangles,'outside')],32,32)


if __name__=='__main__':
    unittest.main()
