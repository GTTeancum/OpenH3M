import unittest,struct
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from tag_metadata import MetadataConverter

class DuneTurretUITests(unittest.TestCase):
    def convert(self,scenario=r'levels\multi\dune\dune',value=0,path=r'weap:h2\objects\vehicles\spectre\plasma_turret\weapon\plasma_turret'):
        data=bytearray(20);struct.pack_into('<I',data,0,value)
        source=SimpleNamespace(data=data,tags={0:{'group':'scnr'}},name=lambda k:scenario)
        src=ET.fromstring('<plugin baseSize="20"><uint32 name="Private Use Font Icon" offset="0"/><uint32 name="Private Use Font Icon (Dual)" offset="4"/><vector3 name="First Person Weapon Offset Override" offset="8"/></plugin>')
        dst=ET.fromstring('<plugin baseSize="4"><int16 name="OLD Message Index" offset="0"/><int16 name="Sort Order" offset="2"/></plugin>')
        return MetadataConverter(source,None,None,None,None).convert(0,src,dst,path)
    def test_native_empty_ui(self):self.assertEqual(self.convert(),bytes(4))
    def test_creep_turret(self):
        self.assertEqual(self.convert(path=r'weap:h2\objects\vehicles\creep\plasma_turret\weapons\creep_turret'),bytes(4))
    def test_wrong_map_or_nondefault_rejected(self):
        with self.assertRaises(ValueError):self.convert(scenario='other')
        with self.assertRaises(ValueError):self.convert(value=1)

if __name__=='__main__':unittest.main()
