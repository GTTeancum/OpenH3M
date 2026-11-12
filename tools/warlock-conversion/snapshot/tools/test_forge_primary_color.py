import struct
import unittest
from forge_primary_color import reroute


class PrimaryColorTests(unittest.TestCase):
    def test_register_and_unrelated_routes_preserved(self):
        routes=[struct.pack('>HBB',7,2,0),struct.pack('>HBB',19,5,3),struct.pack('>HBB',4,8,0)]
        p=bytearray(28);struct.pack_into('>H',p,8,2<<10);struct.pack_into('>H',p,20,2|(1<<10))
        struct.pack_into('>I',p,24,3)
        passes,data,changes=reroute([p],routes,5)
        def entries(usage):
            packed=struct.unpack_from('>H',passes,usage*2)[0];start,count=packed&1023,packed>>10
            return [data[i*4:i*4+4] for i in range(start,start+count)]
        self.assertEqual(entries(4),[routes[0]])
        self.assertEqual(entries(10),[routes[2],struct.pack('>HBB',19,14,3)])
        self.assertEqual(passes[24:],p[24:])
        self.assertEqual(changes[0]['register'],19)

    def test_missing_color_rejected(self):
        with self.assertRaises(ValueError):reroute([bytes(28)],[],5)


if __name__=='__main__':unittest.main()
