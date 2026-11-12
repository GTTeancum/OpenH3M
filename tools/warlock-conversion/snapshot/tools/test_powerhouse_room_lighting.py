import unittest
import numpy as np
from powerhouse_room_lighting import weights, fill_vertices


class RoomLightingTests(unittest.TestCase):
    def test_boundary_and_center(self):
        points = np.array([[118.,226.,43.], [119.,226.,43.],
                           [119.5,226.,43.], [124.,226.,43.]])
        np.testing.assert_array_equal(weights(points), [0.,0.,.5,1.])

    def test_only_selected_ambient_changes(self):
        raw = bytearray(range(60))
        raw[4:8] = bytes([252,30,40,50])
        raw[24:28] = raw[4:8]
        raw[44:48] = raw[4:8]
        weight = np.array([0.,.5,1.])
        out = fill_vertices(bytes(raw), weight, .25)
        self.assertEqual(out[:20], raw[:20])
        for vertex in (1,2):
            start = vertex*20
            self.assertEqual(out[start:start+4], raw[start:start+4])
            self.assertEqual(out[start+8:start+20], raw[start+8:start+20])
            row = np.frombuffer(out[start:start+20],np.int8)
            actual = row[[7,6,5]]/127*np.exp2(float(row[4])/4)
            expected = np.array([50,40,30])/127*.5 + .25*weight[vertex]*np.array([1.,.96,.88])
            np.testing.assert_allclose(actual, expected, atol=.003)
        self.assertEqual(fill_vertices(bytes(raw),weight,0),raw)

    def test_invalid_fill_is_rejected(self):
        for amount in (-.1,.6):
            with self.assertRaises(ValueError):
                fill_vertices(bytes(20),np.ones(1),amount)


if __name__=='__main__':
    unittest.main()
