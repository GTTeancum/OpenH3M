"""Independent handedness and invalid-input checks for Reach world conversion."""
import struct
import unittest
from reach_world_vertices import convert_world_vertices


class ReachWorldVerticesTests(unittest.TestCase):
    def test_handedness_and_half_uv(self):
        for handedness, expected_y in ((0, -1023), (1, 1023)):
            payload=struct.pack('<4f2e8h', 12.5, -3, 8, handedness, .25, -2,
                                0, 0, 32767, 0, 32767, 0, 0, 0)
            result=convert_world_vertices(payload, 1)
            self.assertEqual(struct.unpack_from('>5f', result), (12.5, -3, 8, .25, -2))
            # normal Z cross tangent X = binormal Y; W chooses its sign.
            packed=struct.unpack_from('>I', result, 28)[0]
            y=(packed >> 10)&2047
            if y & 1024:y-=2048
            self.assertEqual(y, expected_y)
            self.assertEqual(packed & 1023, 0)
            self.assertEqual(packed >> 21, 0)

    def test_bad_payload(self):
        with self.assertRaises(ValueError):convert_world_vertices(bytes(35), 1)
        payload=bytearray(36)
        struct.pack_into('<f',payload,12,.5)
        with self.assertRaises(ValueError):convert_world_vertices(payload, 1)
        struct.pack_into('<f',payload,12,0)
        struct.pack_into('<f',payload,0,float('nan'))
        with self.assertRaises(ValueError):convert_world_vertices(payload, 1)

if __name__=='__main__':unittest.main()
