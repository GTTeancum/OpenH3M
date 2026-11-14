import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from dune_sky_bitmap import resolution, NAME, PIXEL_SHA256
from dune_flare import BUILD, SCENARIO

class DuneSkyTests(unittest.TestCase):
    def source(self, scenario=SCENARIO, build=BUILD):
        return SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:scenario,
            data=bytes(0xa0)+build.encode().ljust(32,b'\0'))
    def bitmap(self):
        return SimpleNamespace(info=lambda t:[dict(width=2048,height=2048,format=11,mips=1)],pixels=lambda t:bytes(16777216))
    def test_scope(self):
        self.assertIsNone(resolution(self.source('other'),NAME,None,0))
        self.assertIsNone(resolution(self.source(),'other',None,0))
    def test_layout_and_pixels_fail_closed(self):
        with self.assertRaises(ValueError):resolution(self.source(build='other'),NAME,self.bitmap(),0)
        with self.assertRaises(ValueError):resolution(self.source(),NAME,self.bitmap(),0)
        b=self.bitmap();b.info=lambda t:[dict(width=1024,height=2048,format=11,mips=1)]
        with self.assertRaises(ValueError):resolution(self.source(),NAME,b,0)
    def test_exact_verified_layout(self):
        with patch('dune_sky_bitmap.hashlib.sha256',return_value=Mock(hexdigest=lambda:PIXEL_SHA256)):
            self.assertEqual(resolution(self.source(),NAME,self.bitmap(),0),2048)

if __name__=='__main__':unittest.main()
