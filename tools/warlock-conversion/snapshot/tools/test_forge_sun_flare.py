import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from forge_sun_flare import encode_authored_image
from encode_bitmap import mip_size
from xbox_mip_chain import layout

class AuthoredFlareImages(unittest.TestCase):
    def source(self,w=128,h=128,count=8,fmt=11):
        info=dict(width=w,height=h,mips=count,format=fmt,kind=0,curve=0)
        size=sum(mip_size(max(1,w>>n),max(1,h>>n),fmt) for n in range(count))
        payload=bytes((n*13+7)&255 for n in range(size))
        return SimpleNamespace(info=lambda _: [info],pixels=lambda *_:payload),payload
    def test_complete_chains(self):
        for fmt in (11,14,15,16):
            for w,h,count in ((128,128,8),(1024,512,11)):
                with self.subTest(fmt=fmt,w=w):
                    source,pixels=self.source(w,h,count,fmt)
                    record,control,raw=encode_authored_image(source,0,0)
                    bpb=4 if fmt==11 else 8 if fmt==14 else 16
                    rows,_=layout(w,h,count,bpb,1 if fmt==11 else 4)
                    buf=np.frombuffer(raw,dtype=np.uint8)
                    decoded=b''.join(buf[pos.reshape(-1,1)+np.arange(bpb)].reshape(-1,4 if fmt==11 else 2)[:,::-1].tobytes() for pos,n in rows)
                    self.assertEqual(decoded,pixels)
                    self.assertEqual(record[20]+1,count)
    def test_reject_unreviewed(self):
        for args in ((2048,128,1,11),(128,128,8,0),(16,16,5,11),(100,128,7,11),(128,128,9,11)):
            source,_=self.source(*args)
            with self.subTest(args=args),self.assertRaises(ValueError):encode_authored_image(source,0,0)
    def test_reject_encoder_loss(self):
        source,_=self.source()
        with patch('forge_sun_flare.encode_bitmap_base',return_value=(bytes(48),b'',b'')):
            with self.assertRaises(ValueError):encode_authored_image(source,0,0)

if __name__=='__main__':unittest.main()
