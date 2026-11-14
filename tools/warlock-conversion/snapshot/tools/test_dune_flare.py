import unittest
from types import SimpleNamespace
from dune_flare import matches, validate_fingerprint, NAME, SCENARIO, BUILD, SOURCE_SHA256


class DuneFlareTests(unittest.TestCase):
    def source(self, name=SCENARIO):
        return SimpleNamespace(tags={0:{'group':'scnr'}},name=lambda k:name)
    def test_scope(self):
        self.assertTrue(matches(self.source(),NAME))
        self.assertFalse(matches(self.source('other'),NAME))
        self.assertFalse(matches(self.source(),'other'))
    def test_exact_fingerprint_only(self):
        values=[BUILD,SOURCE_SHA256,17,9,24]
        validate_fingerprint(*values)
        for index,replacement in enumerate(['other','0'*64,18,8,0]):
            changed=values[:];changed[index]=replacement
            with self.assertRaises(ValueError):validate_fingerprint(*changed)


if __name__ == '__main__':unittest.main()
