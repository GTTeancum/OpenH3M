"""Strict authored chains: independent expected linear bytes, no dropped levels."""
import struct
import unittest
from unittest.mock import patch
from encode_bitmap import encode_bitmap_base, encode_cubemap_base, mip_size

class Source:
 def __init__(self,fmt,pixels,w=4,h=2,count=3):
  self.metadata=dict(format=fmt,width=w,height=h,mips=count,kind=0,curve=0)
  self.payload=pixels
 def info(self,tag):return [self.metadata]
 def pixels(self,tag,index=0):return self.payload

class AuthoredMipTests(unittest.TestCase):
 def encode(self,source,**kwargs):
  with patch('xbox_mip_chain.tile_chain',side_effect=lambda payload,*args:payload) as tile:
   result=encode_bitmap_base(source,0,preserve_authored_mips=True,**kwargs)
  self.assertEqual(tile.call_count,1)
  self.assertEqual(result[0][20],source.metadata['mips']-1)
  self.assertEqual(result[1][45],source.metadata['mips'])
  return result,tile.call_args.args

 def test_every_uncompressed_level_expands_independently(self):
  # 4x2, 2x1, 1x1: unique samples in each level, not repeated base pixels.
  for fmt in (0,1,3,10,11):
   with self.subTest(fmt=fmt):
    raw=bytearray();expected=bytearray()
    for n in range(11):
     y,a,b,g,r=17+n,91+n,3+n,25+n,49+n
     if fmt==0:raw+=bytes([a]);expected+=bytes([255,255,255,a])
     elif fmt==1:raw+=bytes([y]);expected+=bytes([y,y,y,255])
     elif fmt==3:raw+=bytes([y,a]);expected+=bytes([y,y,y,a])
     else:raw+=bytes([b,g,r,a]);expected+=bytes([b,g,r,255 if fmt==10 else a])
    result,args=self.encode(Source(fmt,bytes(raw)))
    self.assertEqual(result[2],expected);self.assertEqual(args[-1],11)

 def test_opaque_applies_to_all_expanded_levels(self):
  raw=bytes(range(22))
  result,_=self.encode(Source(3,raw),opaque_alpha=True)
  expected=b''.join(bytes([raw[n],raw[n],raw[n],255]) for n in range(0,22,2))
  self.assertEqual(result[2],expected)

 def test_v16u16_quantization_all_levels(self):
  values=[-32768,-32767,-16384,-258,-129,0,129,258,16384,32767,512]*2
  raw=struct.pack('<22h',*values)
  result,args=self.encode(Source(29,raw))
  # Python scalar rounding is independent of the production numpy path.
  expected=struct.pack('22b',*(max(-127,min(127,round(max(v,-32767)*127/32767))) for v in values))
  self.assertEqual(result[2],expected);self.assertEqual(args[-1],22)

 def test_normal_and_wide_formats_keep_every_byte(self):
  for fmt in (22,26,28):
   with self.subTest(fmt=fmt):
    size=sum(mip_size(max(1,4>>n),max(1,2>>n),fmt) for n in range(3))
    raw=bytes(i%256 for i in range(size));result,args=self.encode(Source(fmt,raw))
    self.assertEqual(result[2],raw);self.assertEqual(args[-1],fmt)

 def test_dxn_bias_all_blocks_all_levels(self):
  raw=bytes(range(48));expected=bytearray(raw)
  for b in range(0,48,16):
   for j in (0,1,8,9):expected[b+j]^=128
  result,_=self.encode(Source(33,raw));self.assertEqual(result[2],expected)

 def test_zero_blue_all_bc3_levels(self):
  raw=bytes(range(48));expected=bytearray(raw)
  for b in range(0,48,16):
   for j in (8,10):expected[b+j]&=0xe0
  result,_=self.encode(Source(16,raw),zero_blue=True);self.assertEqual(result[2],expected)

 def test_bc_opaque_all_levels(self):
  # BC1 white endpoints and selector 0: independent expected BGRA white.
  block=struct.pack('<HHI',0xffff,0,0)
  result,args=self.encode(Source(14,block*3),opaque_alpha=True)
  self.assertEqual(result[2],b'\xff'*44);self.assertEqual(args[-1],11)

 def test_no_silent_fallback_for_small_npot(self):
  source=Source(1,bytes(range(18)),w=5,h=3,count=3) # 15+2+1
  _,args=self.encode(source);self.assertEqual(args[1:4],(5,3,3))
  with patch('xbox_mip_chain.tile_chain',side_effect=ValueError('unsupported layout')):
   with self.assertRaisesRegex(ValueError,'unsupported layout'):
    encode_bitmap_base(source,0,preserve_authored_mips=True)

 def test_real_tiler_retains_all_expanded_levels(self):
  from xbox_mip_chain import layout
  import numpy as np
  w=h=32;count=6
  size=sum(max(1,w>>n)*max(1,h>>n) for n in range(count))
  raw=bytes((n*17)%256 for n in range(size))
  expected=b''.join(bytes([v,v,v,255]) for v in raw)
  record,control,tiled=encode_bitmap_base(Source(1,raw,w,h,count),0,preserve_authored_mips=True)
  rows,total=layout(w,h,count,4,1);decoded=[]
  tiled_array=np.frombuffer(tiled,dtype=np.uint8)
  for positions,length in rows:
   blocks=tiled_array[positions.reshape(-1,1)+np.arange(4)]
   decoded.append(blocks[:,::-1].tobytes())
  self.assertEqual(b''.join(decoded),expected)
  self.assertEqual(len(tiled),total);self.assertEqual(record[20]+1,count);self.assertEqual(control[45],count)

 def test_native_fetch_bound_rejected_before_tiling(self):
  source=Source(1,b'',w=8193,h=1,count=1)
  with self.assertRaisesRegex(ValueError,'dimensions'):
   encode_bitmap_base(source,0,max_dimension=8193,preserve_authored_mips=True)

 def test_rejects_trailing_truncated_invalid_or_dropping(self):
  for payload in (bytes(10),bytes(12)):
   with self.assertRaisesRegex(ValueError,'length mismatch'):
    encode_bitmap_base(Source(1,payload),0,preserve_authored_mips=True)
  for kwargs in ({'max_dimension':2},{'resize_blend':True}):
   with self.assertRaises(ValueError):encode_bitmap_base(Source(1,bytes(11)),0,preserve_authored_mips=True,**kwargs)
  with self.assertRaisesRegex(ValueError,'mip count'):
   encode_bitmap_base(Source(1,bytes(12),count=4),0,preserve_authored_mips=True)

class AuthoredCubeTests(unittest.TestCase):
 def test_all_faces_levels_metadata_and_control(self):
  for fmt in (11,14,15,16):
   with self.subTest(fmt=fmt):
    size=sum(mip_size(max(1,8>>n),max(1,8>>n),fmt) for n in range(4))
    raw=bytes((i*29)%256 for i in range(size*6))
    source=Source(fmt,raw,w=8,h=8,count=4);source.metadata['kind']=2;source.c=None
    with patch('xbox_mip_chain.tile_cube_chain',side_effect=lambda payload,*args:payload) as tile:
     record,control,payload=encode_cubemap_base(source,0,preserve_authored_mips=True)
    self.assertEqual(payload,raw);self.assertEqual(tile.call_args.args,(raw,8,4,fmt))
    self.assertEqual(record[20],3);self.assertEqual(control[45],4)
    self.assertEqual(struct.unpack_from('>HH',record,4),(8,8))
    self.assertEqual(struct.unpack_from('>HH',control,40),(8,8))
    self.assertEqual(struct.unpack_from('>I',control,0)[0],len(raw))
    with self.assertRaisesRegex(ValueError,'dropping is forbidden'):
     encode_cubemap_base(source,0,max_dimension=4,preserve_authored_mips=True)
    source.payload=raw[:-1]
    with self.assertRaisesRegex(ValueError,'size mismatch'):
     encode_cubemap_base(source,0,preserve_authored_mips=True)

if __name__=='__main__':unittest.main()
