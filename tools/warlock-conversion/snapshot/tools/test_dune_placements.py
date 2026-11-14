import struct
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from dune_placements import validate_empty_graph, validate_row, corrections
from scenario_placements import convert_record


class DunePlacementTests(unittest.TestCase):
    def test_every_navigation_container_must_be_empty(self):
        validate_empty_graph([0]*8)
        for index in range(8):
            counts=[0]*8;counts[index]=1
            with self.assertRaises(ValueError):validate_empty_graph(counts)
        with self.assertRaises(ValueError):validate_empty_graph([])
    def test_other_map_gets_no_corrections(self):
        source=SimpleNamespace(tags={0:{'group':'scnr','offset':0}},name=lambda k:'other')
        self.assertEqual(corrections(SimpleNamespace(source=source),None),({},[]))
    def test_changed_source_row_rejected(self):
        for key,size in [(('Controls',0),120),(('Machines',4),136),(('Machines',5),136)]:
            with self.assertRaises(ValueError):validate_row(key,bytes(size))
    def test_explicit_zero_defaults_and_no_other_data_change(self):
        src=ET.fromstring('<plugin elementSize="2"><int16 name="Name" offset="0"/></plugin>')
        dst=ET.fromstring('<plugin elementSize="6"><int16 name="Name" offset="0"/><int16 name="Custom Object Name Index" offset="2"/><int16 name="Unknown" offset="4"/></plugin>')
        cache=SimpleNamespace(unpack=lambda fmt,at:(7,))
        result=convert_record(cache,0,src,dst,correction={'defaults':{('Custom Object Name Index',0):0,('Unknown',0):0}})
        self.assertEqual(result,struct.pack('>3h',7,0,0))
        with self.assertRaises(ValueError):convert_record(cache,0,src,dst)
    def test_only_explicit_nested_block_is_cleared(self):
        schema=ET.fromstring('<plugin elementSize="12"><tagblock name="Pathfinding References" offset="0" elementSize="4"/></plugin>')
        cache=SimpleNamespace(u=lambda at:1)
        self.assertEqual(convert_record(cache,0,schema,schema,correction={'zero_nested':{'Pathfinding References'}}),bytes(12))
        with self.assertRaises(ValueError):convert_record(cache,0,schema,schema)


if __name__ == '__main__':unittest.main()
