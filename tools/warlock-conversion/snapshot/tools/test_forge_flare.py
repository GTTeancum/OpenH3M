import unittest
from types import SimpleNamespace
from forge_flare import matches,validate_fingerprint,NAME,SCENARIO,BUILD,SOURCE_SHA256
class ForgeFlareScope(unittest.TestCase):
    def importer(self):
        return SimpleNamespace(slot='sandbox',gulch_partition=([1],[1]),forge_partition_side='gulch',source=SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda _:SCENARIO))
    def test_scope(self):
        i=self.importer();self.assertTrue(matches(i,NAME))
        i.forge_partition_side='island';self.assertTrue(matches(i,NAME))
        for field,value in [('slot','zanzibar'),('gulch_partition',None),('forge_partition_side','other')]:
            i=self.importer();setattr(i,field,value);self.assertFalse(matches(i,NAME))
        self.assertFalse(matches(self.importer(),'other'))
        i=self.importer();i.source.name=lambda _:'other';self.assertFalse(matches(i,NAME))
    def test_fingerprint(self):
        args=[BUILD,SOURCE_SHA256,18,10,10];validate_fingerprint(*args)
        for n,v in enumerate(['other','0'*64,17,9,0]):
            a=args.copy();a[n]=v
            with self.assertRaises(ValueError):validate_fingerprint(*a)
if __name__=='__main__':unittest.main()
