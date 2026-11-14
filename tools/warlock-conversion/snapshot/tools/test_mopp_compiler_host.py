"""Platform adapter must preserve the exact compiler and reject unknown loaders."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import forge_gulch_containment as m


class MoppCompilerHostTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[4]/'.local/build-temp'
        base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base);self.work=Path(self.temp.name)
        self.compiler=self.work/'mopp.exe';self.a=self.work/'input';self.b=self.work/'output'
    def tearDown(self):self.temp.cleanup()
    def test_windows_exact_original_command(self):
        command,flags=m.compiler_command(self.compiler,self.a,self.b,self.work,'nt')
        self.assertEqual(command,[str(self.compiler),'generate-collision-mopp',str(self.a),str(self.b)])
        self.assertEqual(flags,0x08000000)
    @mock.patch('platform.system',return_value='Linux')
    @mock.patch('platform.machine',return_value='x86_64')
    def test_linux_uses_only_verified_loader_and_same_command(self,*_):
        loader=self.work/'tools/wibo-x86_64';loader.parent.mkdir();loader.write_bytes(b'test-fixture')
        with mock.patch.object(m,'LOADER_SHA256',hashlib.sha256(b'test-fixture').hexdigest()):
            command,flags=m.compiler_command(self.compiler,self.a,self.b,self.work,'posix')
        self.assertEqual(command,[str(loader),str(self.compiler),'generate-collision-mopp',str(self.a),str(self.b)])
        self.assertEqual(flags,0)
    @mock.patch('platform.system',return_value='Linux')
    @mock.patch('platform.machine',return_value='x86_64')
    def test_existing_tampered_loader_fails_without_execution(self,*_):
        loader=self.work/'tools/wibo-x86_64';loader.parent.mkdir();loader.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Unverified'):m.compiler_command(self.compiler,self.a,self.b,self.work,'posix')
    @mock.patch('platform.system',return_value='Linux')
    @mock.patch('platform.machine',return_value='x86_64')
    def test_download_hash_checked_before_install(self,*_):
        with mock.patch('urllib.request.urlopen') as get:
            get.return_value.read.return_value=b'changed'
            with self.assertRaisesRegex(ValueError,'pinned official'):m.compiler_command(self.compiler,self.a,self.b,self.work,'posix')
        self.assertFalse((self.work/'tools/wibo-x86_64').exists())
    @mock.patch('platform.system',return_value='Darwin')
    def test_unsupported_host_is_explicit(self,*_):
        with self.assertRaisesRegex(ValueError,'requires Windows'):m.compiler_command(self.compiler,self.a,self.b,self.work,'posix')

if __name__=='__main__':unittest.main()
