import struct
import unittest
from unittest.mock import patch
import numpy as np
import decal_bitmap as d

class Cache:
    tags={0:{'offset':0},1:{'offset':200}}
    data=bytearray(512)
    data[121]=data[321]=3
    def u(self,offset):return 0
    def block(self,offset,stride):return [offset+4]

class Source:
    c=Cache()
    def __init__(self,infos,payloads):self.infos=infos;self.payloads=payloads
    def info(self,tag):return [self.infos[tag]]
    def pixels(self,tag,index=0):return self.payloads[tag]

def capture(source,tag,**kw):
    assert kw==dict(max_dimension=8192,preserve_authored_mips=True)
    return source.info(tag)[0],source.pixels(tag),kw

def info(w,h,n,fmt=11):return dict(width=w,height=h,mips=n,format=fmt,kind=0)
def colors(w,h,n):
    return b''.join(bytes((10+i,20+i,30+i,40+i))*max(1,w>>i)*max(1,h>>i) for i in range(n))

class DecalTests(unittest.TestCase):
    def test_nearest_real_encoder_preserves_diffuse_curve_and_all_levels(self):
        from xbox_bitmap import untile_base
        from xbox_mip_chain import layout
        for curve,gpu in ((1,0x18287fb2),(3,0x18280186),(5,0x18287fb2)):
            for w,h,n in ((4,4,1),(4,4,3),(65,33,7)):
                with self.subTest(curve=curve,width=w,height=h,mips=n):
                    source=Source([info(w,h,n)]*2,[colors(w,h,n)]*2)
                    source.c=Cache();source.c.data=bytearray(Cache.data)
                    source.c.data[121]=curve
                    source.c.data[321]=3 if curve!=3 else 1
                    mask=bytearray(source.payloads[1]);mask[3::4]=bytes(v+50 for v in mask[3::4])
                    source.payloads=[source.payloads[0],bytes(mask)]
                    expected=bytearray(source.payloads[0]);expected[3::4]=mask[3::4]
                    # Exercise the actual encoder and native tiler, not capture().
                    record,control,tiled=d.bake(source,0,1,(1,1))
                    self.assertEqual(struct.unpack_from('>HH',record,4),(w,h))
                    self.assertEqual(record[20:22],bytes((n-1,curve)))
                    self.assertEqual(control[45:48],bytes((n,0,0)))
                    self.assertEqual(struct.unpack_from('>I',control,48)[0],gpu)
                    self.assertEqual(struct.unpack_from('>I',control,0)[0],len(tiled))
                    if n==1:
                        actual=untile_base(tiled,w,h,11)
                    else:
                        rows,total=layout(w,h,n,4,1);self.assertEqual(len(tiled),total)
                        raw=np.frombuffer(tiled,dtype=np.uint8)
                        actual=b''.join(raw[pos.reshape(-1,1)+np.arange(4)][:,::-1].tobytes() for pos,_ in rows)
                    self.assertEqual(actual,expected)

    @patch.object(d,'encode_bitmap_base',side_effect=capture)
    def test_bc_full_npot_chain_exact(self,enc):
        w,h,n=768,384,10
        color=bytes.fromhex('ffff000000000000')
        maskalpha=bytes.fromhex('ff00000000000000')
        a=[];b=[];expected=[]
        for i in range(n):
            blocks=((max(1,w>>i)+3)//4)*((max(1,h>>i)+3)//4)
            a.append(color*blocks);b.append((maskalpha+color)*blocks)
            expected.append((maskalpha+color)*blocks)
        out,payload,_=d.combine_bc_alpha(Source([info(w,h,n,14),info(w,h,n,16)],[b''.join(a),b''.join(b)]),0,1)
        self.assertEqual((out['width'],out['height'],out['mips']),(w,h,n))
        self.assertEqual(payload,b''.join(expected))

    @patch.object(d,'encode_bitmap_base',side_effect=capture)
    def test_nearest_every_authored_level_no_cap(self,enc):
        w,h,n=768,384,10
        a=colors(w,h,n);b=colors(w,h,n)
        out,payload,_=d.bake(Source([info(w,h,n),info(w,h,n)],[a,b]),0,1,(1,1))
        self.assertEqual(out['width'],768);self.assertEqual(out['mips'],10)
        self.assertEqual(payload,a)

    @patch.object(d,'encode_bitmap_base',side_effect=capture)
    def test_derived_chain_stops_at_authored_count(self,enc):
        s=Source([info(64,32,2),info(32,16,3)],[colors(64,32,2),colors(32,16,3)])
        out,payload,_=d.combine_resampled_alpha(s,0,1)
        self.assertEqual((out['width'],out['height'],out['mips']),(64,32,3))
        self.assertEqual(len(payload),sum(max(1,64>>i)*max(1,32>>i)*4 for i in range(3)))
        out,payload,_=d.bake(s,0,1,(1,1))
        self.assertEqual(out['mips'],3)
        # Last RGB derives from final existing color level, alpha from mask2.
        self.assertEqual(payload[-4:],bytes((11,21,31,42)))

    @patch.object(d,'encode_bitmap_base',side_effect=capture)
    def test_bilinear_base_not_capped_and_partial_chain_not_extended(self,enc):
        s=Source([info(768,384,2),info(768,384,2)],[colors(768,384,2)]*2)
        out,payload,_=d.combine_resampled_alpha(s,0,1)
        self.assertEqual((out['width'],out['height'],out['mips']),(768,384,2))
        self.assertEqual(len(payload),(768*384+384*192)*4)
        self.assertEqual(payload[3],40)
        self.assertEqual(payload[-1],41)

    def test_reject_count_mismatch_and_extra_or_missing_payload(self):
        for payload in (b'\0'*15,b'\0'*17):
            s=Source([info(4,4,1,16)]*2,[payload,b'\0'*16])
            for f in (d.combine_bc_alpha,d.combine_resampled_alpha):
                with self.assertRaisesRegex(ValueError,'payload'):f(s,0,1)
            with self.assertRaisesRegex(ValueError,'payload'):d.bake(s,0,1,(1,1))
        s=Source([info(4,4,1,16),info(4,4,2,16)],[b'\0'*16,b'\0'*32])
        with self.assertRaisesRegex(ValueError,'mip counts'):d.combine_bc_alpha(s,0,1)

if __name__=='__main__':unittest.main()
