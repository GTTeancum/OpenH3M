"""MOPP relocation tests exercise branch-local offsets and spatial branches."""
import unittest
from forge_mopp import terminals, remap_surfaces


def leaf(key):
    # Reoffset32 plus a compact terminal verifies accumulated keys are decoded.
    return b'\x0b'+(key-1).to_bytes(4,'big')+b'\x31'


def branch(left, right):
    return bytes((0x10,20,30,len(left)))+left+right


class ForgeMoppTests(unittest.TestCase):
    def test_partition_preserves_classes_and_instances(self):
        source=leaf(16<<26 | 2)
        for kind,index in reversed([(k,0) for k in range(8,13)]+[(13,1)]):
            source=branch(leaf(kind<<26 | index), source)
        rewritten=remap_surfaces(source,{1:0},2,3)
        self.assertEqual([k for _,_,k in terminals(rewritten)], [13<<26,16<<26 | 2])
        self.assertEqual(rewritten[:3],source[:3])
        identity=remap_surfaces(source,{0:0,1:1},2,3)
        self.assertEqual([k for _,_,k in terminals(source)],[k for _,_,k in terminals(identity)])

    def test_bad_jump_is_rejected(self):
        with self.assertRaises(ValueError): terminals(b'\x05\xff')

    def test_unknown_shape_class_is_rejected(self):
        with self.assertRaises(ValueError): remap_surfaces(leaf(17<<26),{0:0},1,1)

if __name__=='__main__': unittest.main()
