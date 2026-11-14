"""Primary-only payloads must never advertise secondary high-resolution data."""
import struct
import unittest
from encode_bitmap import encode_bitmap_base, encode_cubemap_base, mip_size

class Source:
 c=None
 def __init__(self,w,h,count,fmt,kind):
  self.i=dict(width=w,height=h,mips=count,format=fmt,kind=kind,curve=0)
  size=sum(mip_size(max(1,w>>n),max(1,h>>n),fmt) for n in range(count))
  self.raw=bytes((n*37)%256 for n in range(size*(6 if kind==2 else 1)))
 def info(self,tag):return [self.i]
 def pixels(self,tag,index=0):return self.raw

class PrimaryDescriptorTests(unittest.TestCase):
 def check_descriptor(self,result,count,kind):
  record,control,raw=result
  self.assertEqual(control[47],0)
  self.assertEqual(control[45],count)
  self.assertEqual(control[46],kind)
  self.assertEqual(struct.unpack_from('>I',control,0)[0],len(raw))
  self.assertEqual(record[20]+1,count)

 def test_2d_strict_single_and_chains(self):
  for fmt in (11,14,16,22):
   for count in (1,4):
    with self.subTest(fmt=fmt,count=count):
     self.check_descriptor(encode_bitmap_base(Source(8,8,count,fmt,0),0,preserve_authored_mips=True),count,0)

 def test_legacy_single_and_retained_chain(self):
  for fmt in (11,14,16,22):
   source=Source(32,32,6,fmt,0)
   self.check_descriptor(encode_bitmap_base(source,0),1,0)
   self.check_descriptor(encode_bitmap_base(source,0,preserve_color_mips=True,preserve_bc_mips=True,preserve_normal_mips=True),6,0)

 def test_cube_primary_descriptor_unchanged(self):
  for count in (1,4):
   for strict in (False,True):
    self.check_descriptor(encode_cubemap_base(Source(8,8,count,16,2),0,preserve_mips=True,preserve_authored_mips=strict),count,2)

class SingleCubeStrideTests(unittest.TestCase):
 def test_independent_tagtool_actual_descriptor_when_available(self):
  import hashlib,json,subprocess,tempfile
  from pathlib import Path
  root=Path(__file__).resolve().parents[4]
  oracle=root/'work/mcc-ten-conversion/mip-oracle/bin/NativeValidate.dll'
  dotnet=root/'work/forge-world/tools/dotnet/dotnet'
  if not oracle.exists() or not dotnet.exists():self.skipTest('Independent TagTool decoder is not installed')
  with tempfile.TemporaryDirectory(dir=oracle.parent.parent) as folder:
   work=Path(folder);primary=work/'primary.bin';secondary=work/'secondary.bin';job=work/'job.json'
   secondary.write_bytes(b'')
   for fmt in (11,14,15,16):
    source=Source(8,8,1,fmt,2)
    record,control,raw=encode_cubemap_base(source,0,preserve_authored_mips=True)
    primary.write_bytes(raw)
    job.write_text(json.dumps(dict(primary=str(primary),secondary=str(secondary),width=8,height=8,depth=control[44],mips=control[45],kind=control[46],high=control[47],gpu=int.from_bytes(control[48:52],'big'))))
    result=subprocess.run([str(dotnet),str(oracle),str(job)],check=True,capture_output=True,text=True,timeout=20)
    actual=[{k:r[k] for k in ('face','level','length','sha256')} for r in json.loads(result.stdout)]
    size=mip_size(8,8,fmt)
    expected=[dict(face=face,level=0,length=size,sha256=hashlib.sha256(source.raw[face*size:(face+1)*size]).hexdigest()) for face in range(6)]
    self.assertEqual(actual,expected)

 def test_every_face_uses_native_allocation_not_tight_buffer(self):
  from xbox_bitmap import untile_base
  for width in (1,8,24,33,64,128):
   for fmt in (11,14,15,16):
    for strict in (False,True):
     with self.subTest(width=width,fmt=fmt,strict=strict):
      source=Source(width,width,1,fmt,2)
      record,control,raw=encode_cubemap_base(source,0,max_dimension=width,preserve_authored_mips=strict)
      # Independent integer ceil formulation for native slice allocation.
      blocks=width if fmt==11 else (width+3)//4
      block_bytes={11:4,14:8,15:16,16:16}[fmt]
      stride=(((((blocks+31)//32)*32)**2*block_bytes+4095)//4096)*4096
      size=mip_size(width,width,fmt)
      self.assertEqual(len(raw),6*stride)
      self.assertEqual(struct.unpack_from('>I',control,0)[0],6*stride)
      self.assertEqual(record[20],0);self.assertEqual(control[45:48],bytes([1,2,0]))
      for face in range(6):
       self.assertEqual(untile_base(raw[face*stride:(face+1)*stride],width,width,fmt),source.raw[face*size:(face+1)*size])

if __name__=='__main__':unittest.main()
