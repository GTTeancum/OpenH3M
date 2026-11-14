import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from dune_spectre import matches,NAME,SCENARIO,BUILD,SOURCE_SHA256

class DuneSpectreTests(unittest.TestCase):
    def source(self,scenario=SCENARIO):
        return SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:scenario,data=bytes(0xa0)+BUILD.encode().ljust(32,b'\0'))
    def test_scope(self):
        self.assertFalse(matches(self.source('other'),'rmhg',NAME,'_0_3_1_0_0_4_0'))
        self.assertFalse(matches(self.source(),'rmhg','other','_0_3_1_0_0_4_0'))
        self.assertFalse(matches(self.source(),'rmsh',NAME,'_0_3_1_0_0_4_0'))
    def test_source_fingerprint(self):
        with self.assertRaises(ValueError):matches(self.source(),'rmhg',NAME,'_0_3_1_0_0_4_0')
        with patch('dune_spectre.hashlib.sha256',return_value=Mock(hexdigest=lambda:SOURCE_SHA256)):
            self.assertTrue(matches(self.source(),'rmhg',NAME,'_0_3_1_0_0_4_0'))
            with self.assertRaises(ValueError):matches(self.source(),'rmhg',NAME,'other')

if __name__=='__main__':unittest.main()
