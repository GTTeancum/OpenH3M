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

    def test_unknown_padding_and_pointer_are_rejected(self):
        for words in ([6, 1, 0, 0, 2, 0, 0, 0],
                      [6, 0, 0, 0, 2, 0xcbcbcbcb, 0, 0]):
            with self.assertRaises(ValueError):
                self.convert(words)


if __name__ == '__main__':
    unittest.main()
