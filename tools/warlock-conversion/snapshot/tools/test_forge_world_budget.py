"""Regression checks for budgeted terrain mask conversion (no game assets)."""
import struct
import unittest
from encode_bitmap import encode_bitmap_base
from xbox_bitmap import untile_base


class BlendSource:
    def __init__(self):
        self.c=self
        self.tags={0:{'offset':0}}
        self.data=bytes(64)
    def info(self,tag):
        return [{'width':8,'height':8,'format':16,'mips':1}]
    def block(self,offset,stride):return [0]
    def unpack(self,fmt,offset):return (0,)
    def pixels(self,tag,index=0):
        # White RGB with zero alpha. Premultiplied resizing would lose RGB.
        return (bytes(8)+b'\xff\xff\xff\xff'+bytes(4))*4


class BlendBudgetTests(unittest.TestCase):
    def test_missing_mip_still_rejected_by_default(self):
        with self.assertRaisesRegex(ValueError,'no mip'):
            encode_bitmap_base(BlendSource(),0,max_dimension=4)
    def test_independent_blend_channels_survive_resize(self):
        record,control,tiled=encode_bitmap_base(BlendSource(),0,max_dimension=4,resize_blend=True)
        self.assertEqual(struct.unpack_from('>HH',record,4),(4,4))
        self.assertEqual(struct.unpack_from('>H',record,12)[0],11)
        self.assertEqual(untile_base(tiled,4,4,11),b'\xff\xff\xff\x00'*16)


if __name__=='__main__':unittest.main()
