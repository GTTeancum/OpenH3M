import unittest,struct
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from tag_metadata import MetadataConverter

class DuneModelFlagTests(unittest.TestCase):
    def convert(self,value=2,scenario=r'levels\multi\dune\dune'):
        data=bytes([value])+bytes(23)
        source=SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:scenario,unpack=lambda f,a:struct.unpack_from('<'+f,data,a))
        src=ET.fromstring('<tagblock name="Permutations" elementSize="24"><flags8 name="Flags" offset="0"><bit name="Copy States To All Permutations" index="0"/></flags8></tagblock>')
        dst=ET.fromstring('<tagblock name="Permutations" elementSize="36"><flags8 name="Flags" offset="0"><bit name="Copy States To All Permutations" index="0"/></flags8></tagblock>')
        for n in range(1,24):
            for schema in (src,dst):ET.SubElement(schema,'uint8',name=f'Byte{n}',offset=str(n))
        for n in range(24,36):ET.SubElement(dst,'int8',name=f'Runtime State Permutation Index {n-24}',offset=str(n))
        return MetadataConverter(source,None,None,None,None).convert(0,src,dst,r'hlmt:h2\objects\vehicles\creep\creep/Variants[1]/Regions[1]/Permutations[0]')
    def test_bit_preserved(self):self.assertEqual(self.convert()[0],2)
    def test_other_map_or_unknown_bits_reject(self):
        with self.assertRaises(ValueError):self.convert(scenario='other')
        with self.assertRaises(ValueError):self.convert(value=4)

if __name__=='__main__':unittest.main()
