"""Native RenderBsp relocation preserves all eight collision arrays."""
import struct
import unittest
from types import SimpleNamespace
from bsp_collision_resource import convert_bsp_collision

class RenderBspConversion(unittest.TestCase):
    def test_nested_geometry_arrays_and_pointers(self):
        source=SimpleNamespace(c=SimpleNamespace(mcc=True),root=0,data=bytearray(1024),raw=[],fix={})
        source.unpack=lambda fmt,at:struct.unpack_from('<'+fmt,source.data,at)
        instance,render=48,256
        struct.pack_into('<I',source.data,24,1);source.fix[28]=0x20000000+instance
        struct.pack_into('<I',source.data,instance+0x74,1);source.fix[instance+0x78]=0x20000000+render
        formats=('Q','4I','BBHI','2H','3I2H','5H2B','6H','3I2H')
        samples=((0x800000ffffff0001,),(0x3f800000,0,0,0x40000000),(3,1,2,0),
                 (4,0xffff),(0x3f800000,0,0,0x8001,0xffff),(1,2,3,4,5,6,7),
                 (1,2,3,4,5,6),(0x3f800000,0x40000000,0,5,0xffff))
        at=512
        for n,(fmt,row) in enumerate(zip(formats,samples)):
            struct.pack_into('<I',source.data,render+n*12,1);source.fix[render+n*12+4]=0x20000000+at
            struct.pack_into('<'+fmt,source.data,at,*row);at+=struct.calcsize(fmt)+16
        result=convert_bsp_collision(source);control=result['control'];fix=dict(result['fixups'])
        native_instance=fix[16]&0x1fffffff
        self.assertEqual(struct.unpack_from('>I',control,12)[0],1)
        self.assertEqual(struct.unpack_from('>I',control,native_instance+0x74)[0],1)
        native_render=fix[native_instance+0x78]&0x1fffffff
        for n,(fmt,row) in enumerate(zip(formats,samples)):
            self.assertEqual(struct.unpack_from('>I',control,native_render+n*12)[0],1)
            pointer=fix[native_render+n*12+4]
            self.assertEqual(pointer>>29,2)
            self.assertEqual(struct.unpack_from('>'+fmt,result['raw'],pointer&0x1fffffff),row)
        self.assertEqual(len(fix),10)

if __name__=='__main__':unittest.main()
