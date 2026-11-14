"""Per-side cache restore requires exact source identity and artifact hashes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from forge_partition_cache import save, restore


class CacheTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[4]/'.local/build-temp'
        base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
        self.root=Path(self.temp.name);self.work=self.root/'work';self.folder=self.root/'saved'
        (self.work/'temp').mkdir(parents=True)
        (self.work/'temp/collision-overlaid.output').write_bytes(b'geometry')
        (self.work/'temp/collision-clusters.bin').write_bytes(b'clusters')
        (self.work/'rebuild-cache.json').write_text(json.dumps(dict(
            result_sha256=hashlib.sha256(b'geometry').hexdigest(),
            clusters_sha256=hashlib.sha256(b'clusters').hexdigest())))
        self.identity={'side':'gulch','source_sha256':'source-a','preparation_sources':{'boundary':'approved'}}
        save(self.folder,self.work,self.identity)
    def tearDown(self):self.temp.cleanup()
    def test_restore_valid_identity(self):
        (self.work/'temp/collision-overlaid.output').write_bytes(b'other-side')
        self.assertTrue(restore(self.folder,self.work,self.identity))
        self.assertEqual((self.work/'temp/collision-overlaid.output').read_bytes(),b'geometry')
    def test_wrong_side_or_source_or_boundary_not_restored(self):
        for key,value in [('side','island'),('source_sha256','source-b'),('preparation_sources',{'boundary':'changed'})]:
            other=dict(self.identity);other[key]=value
            self.assertFalse(restore(self.folder,self.work,other))
    def test_tampered_artifact_not_restored(self):
        (self.folder/'collision-overlaid.output').write_bytes(b'corruption')
        self.assertFalse(restore(self.folder,self.work,self.identity))
    def test_inner_builder_hash_also_required(self):
        p=self.folder/'rebuild-cache.json';p.write_text('{}')
        manifest=self.folder/'partition-cache.json';r=json.loads(manifest.read_text())
        r['files']['rebuild-cache.json']=hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(r))
        self.assertFalse(restore(self.folder,self.work,self.identity))

if __name__=='__main__':unittest.main()
