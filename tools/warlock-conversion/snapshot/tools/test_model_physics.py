"""Check child-shape width conversion without accepting runtime pointers."""
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

from model_physics import convert_model_physics


class ListShapeTests(unittest.TestCase):
    def convert(self, words):
        reference = Path(__file__).resolve().parents[1] / 'reference'
        schemas = [next(n for n in ET.parse(reference / kind / 'phmo.xml').getroot()
                        if n.get('name') == 'List Shapes')
                   for kind in ('mcc', 'plugins')]
        payload = struct.pack('<8I', *words)
        source = SimpleNamespace(unpack=lambda fmt, at: struct.unpack_from('<' + fmt, payload, at))
        return convert_model_physics(SimpleNamespace(source=source), 0, *schemas,
                                     'phmo:fixture/List Shapes[0]')

    def test_compiler_fill_does_not_change_child_shape(self):
        words = [0x10006, 0, 0, 0xcbcbcbcb, 2, 0, 0, 0]
        expected = struct.pack('>HHIII', 6, 1, 0, 0xcbcbcbcb, 2)
        self.assertEqual(self.convert(words), expected)
        words[5:] = [0xcbcbcbcb] * 3
        self.assertEqual(self.convert(words), expected)

    def test_official_compiler_tail_and_collision_filter(self):
        # Tail observed in the official compiled folding-chair shape.
        words = [0x10002, 0, 0x12345678, 224, 0,
                 0x5f006e, 0x680063, 0x690061]
        self.assertEqual(self.convert(words),struct.pack('>HHIII',2,1,0x12345678,224,0))

    def test_runtime_pointer_high_word_is_rejected(self):
        with self.assertRaises(ValueError):
            self.convert([6, 1, 0, 0, 2, 0, 0, 0])


class TriangleShapeTests(unittest.TestCase):
    def test_vertices_welding_and_pointer_validation(self):
        reference=Path(__file__).resolve().parents[1]/'reference'
        schemas=[next(n for n in ET.parse(reference/kind/'phmo.xml').getroot()
                      if n.get('name')=='Triangles') for kind in ('mcc','plugins')]
        payload=bytearray(144)
        struct.pack_into('<hbb',payload,0x44,23,2,1)
        struct.pack_into('<II',payload,0x48,0x60000,0x12345678)
        struct.pack_into('<Q',payload,0x30,144)
        vertices=(1.,2.,3.,0.,4.,5.,6.,0.,7.,8.,9.,0.,0.,0.,1.,0.)
        struct.pack_into('<16f',payload,0x50,*vertices)
        source=SimpleNamespace(unpack=lambda fmt,at:struct.unpack_from('<'+fmt,payload,at))
        conv=SimpleNamespace(source=source,strings=SimpleNamespace(translate=lambda value,target:value),target_strings=None)
        out=convert_model_physics(conv,0,*schemas,'phmo:fixture/Triangles[0]')
        self.assertEqual(len(out),128)
        self.assertEqual(struct.unpack_from('>I',out,0x28)[0],128)
        self.assertEqual(struct.unpack_from('>16f',out,0x40),vertices)
        self.assertEqual(struct.unpack_from('>hbb',out,0x34),(23,2,1))
        self.assertEqual(out[0x38:0x40],bytes(8))
        struct.pack_into('<Q',payload,0x20,1<<32)
        with self.assertRaises(ValueError):convert_model_physics(conv,0,*schemas,'phmo:fixture/Triangles[0]')


if __name__ == '__main__':
    unittest.main()
