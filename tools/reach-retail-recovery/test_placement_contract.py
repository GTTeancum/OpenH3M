import unittest,struct
from placement_contract import apply_automatic_ownership
class Contract(unittest.TestCase):
 def setUp(self):
  self.s=bytearray(0xdc);self.n=bytearray(0xb4);self.s[0x3c:0x44]=self.n[0x38:0x40]=bytes.fromhex('aabbccddffff0601');self.s[0x55]=2;self.n[0x33]=2
 def test_move(self):
  before=bytes(self.n);out=apply_automatic_ownership(self.s,self.n,{1:1});self.assertEqual({i for i,(a,b) in enumerate(zip(before,out)) if a!=b},{0x33,0x51});self.assertEqual(out[0x32:0x34],b'\0\0');self.assertEqual(out[0x50:0x52],b'\0\2');self.assertEqual(bytes(self.n),before)
 def test_remap(self):
  self.s[0x55]=5;self.n[0x33]=0;out=apply_automatic_ownership(self.s,self.n,{0:1,2:3});self.assertEqual(out[0x50:0x52],b'\0\x0a')
 def test_fail(self):
  for off,val in ((0x33,1),(0x35,1),(0x55,0),(0x3d,0x57)):
   row=self.s.copy();row[off]=val
   with self.assertRaises(ValueError):apply_automatic_ownership(row,self.n,{1:1})
  for m in ({},{1:-1},{1:16},{1:True}):
   with self.assertRaises(ValueError):apply_automatic_ownership(self.s,self.n,m)
  self.n[0x33]=1
  with self.assertRaises(ValueError):apply_automatic_ownership(self.s,self.n,{1:1})
if __name__=='__main__':unittest.main()
