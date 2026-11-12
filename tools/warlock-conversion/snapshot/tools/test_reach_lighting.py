import unittest
import numpy as np
from reach_lighting import decode_static_lighting

class ReachLightingTests(unittest.TestCase):
    def test_packed_colors_exhaustive(self):
        # Enumerate all combinations of the two bytes carrying indirect RGB.
        source=np.zeros((65536,6),dtype='u1')
        source[:,1]=np.arange(65536,dtype='u4')&255
        source[:,2]=np.arange(65536,dtype='u4')>>8
        source[:,3:6]=[0,128,255]
        decoded=decode_static_lighting(source.tobytes(),4.0)
        for i in range(65536):
            bits=int(source[i,1]) | (int(source[i,2])<<8)
            channels=[(bits>>1)&31,(bits>>6)&31,(bits>>11)&31]
            expected=[(v/31)**2*4 for v in channels]
            np.testing.assert_allclose(decoded['indirect_color'][i],expected,rtol=1e-14)
        np.testing.assert_allclose(decoded['direct_color'][0],[0,(128/255)**2*4,4])

    def test_direction_mask_and_padding(self):
        out=decode_static_lighting(bytes([128,1,0,0,0,0,0xcd,0xcd]),1)
        np.testing.assert_array_equal(out['direction'],[[0,0,1]])
        self.assertEqual(out['analytical_mask'][0],1)
        with self.assertRaises(ValueError):decode_static_lighting(bytes([127,0,0,0,0,0]),1)
        with self.assertRaises(ValueError):decode_static_lighting(bytes(7),1)
        with self.assertRaises(ValueError):decode_static_lighting(bytes(6),float('nan'))

if __name__=='__main__':unittest.main()
