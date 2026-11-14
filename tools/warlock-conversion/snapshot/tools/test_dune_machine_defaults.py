import struct
import unittest
from types import SimpleNamespace
import xml.etree.ElementTree as ET
from tag_metadata import MetadataConverter


class DuneMachineDefaultsTests(unittest.TestCase):
    def convert(self, scenario=r'levels\multi\dune\dune', kind=1,
                path=r'mach:levels\objects\multi\dune\base_lights\base_lights'):
        data=bytearray(0x194)
        struct.pack_into('<H',data,0x190,kind)
        source=SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:scenario,
                               unpack=lambda f,a:struct.unpack_from('<'+f,data,a))
        converter=MetadataConverter(source,None,None,None,None)
        src=ET.fromstring('<plugin baseSize="0"/>')
        dst=ET.fromstring('<plugin baseSize="2"><enum16 name="Collision Response" offset="0"/></plugin>')
        return converter.convert(0,src,dst,path)
    def test_platform_gets_native_zero_default(self):
        self.assertEqual(self.convert(),bytes(2))
    def test_other_scenario_does_not_get_default(self):
        with self.assertRaises(ValueError):self.convert(scenario='other')
    def test_changed_type_fails(self):
        with self.assertRaises(ValueError):self.convert(kind=2)
    def test_unknown_machine_not_defaulted(self):
        with self.assertRaises(ValueError):self.convert(path=r'mach:levels\objects\multi\dune\new_machine')


if __name__ == '__main__':unittest.main()
