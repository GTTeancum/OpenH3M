"""Explicit null placement preservation never drops or renumbers records."""
import struct
import unittest
import xml.etree.ElementTree as ET
from assemble_scenario import prepare


class Fixture:
    def __init__(self):
        self.tags = {0: {'group':'scnr','offset':0,'salt':1},
                     1: {'group':'bloc','offset':300,'salt':1}}
        self.data = bytearray(400)
        for at, palette in [(100,0),(104,-1),(108,0)]:
            struct.pack_into('<hh', self.data, at, palette, -1)
        struct.pack_into('<I', self.data, 212, 0x10001)
    def name(self, index): return ['scenario','crate'][index]
    def unpack(self, fmt, at): return struct.unpack_from('<'+fmt,self.data,at)
    def u(self, at): return self.unpack('I',at)[0]
    def block(self, at, stride): return {10:[100,104,108],20:[200],30:[]}[at]


class NullPlacementTests(unittest.TestCase):
    def setUp(self):
        self.cache = Fixture()
        self.schema = ET.fromstring('''<plugin>
          <tagblock name="Crates" offset="10" elementSize="4">
            <int16 name="Palette Index" offset="0"/><int16 name="Name Index" offset="2"/>
          </tagblock>
          <tagblock name="Crates Palette" offset="20" elementSize="48"/>
          <tagblock name="Object Names" offset="30" elementSize="36"/>
        </plugin>''')
    def run_prepare(self, allowed):
        return prepare(self.cache,self.cache,self.schema,self.schema,
                       placements={'Crates':('Crates Palette',10)},preserved_null_placements=allowed)
    def test_preserves_index_and_native_null_sentinel(self):
        result = self.run_prepare({('Crates',1)})
        self.assertEqual(result['unresolved'],[])
        self.assertEqual(result['arrays']['Crates'],(3,struct.pack('>6h',0,-1,-1,-1,0,-1)))
        self.assertEqual(result['arrays']['Crates Palette'][0],1)
    def test_null_is_not_generally_accepted(self):
        with self.assertRaises(ValueError): self.run_prepare(set())
    def test_named_or_tagged_null_fails(self):
        for palette,name in [(-1,0),(0,-1)]:
            struct.pack_into('<hh',self.cache.data,104,palette,name)
            with self.assertRaises(ValueError): self.run_prepare({('Crates',1)})


if __name__ == '__main__': unittest.main()
