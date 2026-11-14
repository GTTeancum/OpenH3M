import struct
import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from dune_projectile import matches,update_root,NAME,TEMPLATE,SCENARIO,BUILD,SOURCE_SHA256

class DuneProjectileTests(unittest.TestCase):
    def source(self,scenario=SCENARIO):
        return SimpleNamespace(tags={0:{'group':'scnr'},1:{'group':'cntl','offset':100}},name=lambda k:[scenario,NAME][k],
            data=bytes(0xa0)+BUILD.encode().ljust(32,b'\0'),block=lambda o,s:{100:[200],544:[300]}.get(o,[]))
    def test_exact_scope_and_fingerprint(self):
        with patch('dune_projectile.hashlib.sha256',return_value=Mock(hexdigest=lambda:SOURCE_SHA256)):
            self.assertTrue(matches(self.source(),300,'cntl',TEMPLATE))
            self.assertFalse(matches(self.source(),301,'cntl',TEMPLATE))
            self.assertFalse(matches(self.source('other'),300,'cntl',TEMPLATE))
            self.assertFalse(matches(self.source(),300,'ltvl',TEMPLATE))
            self.assertFalse(matches(self.source(),300,'cntl','other'))
        with self.assertRaises(ValueError):matches(self.source(),300,'cntl',TEMPLATE)

class DuneContrailRootTests(unittest.TestCase):
    def fixture(self, aliases=('_0_8_1_0',), source_options=(0,1,1,0),
                native_option_count=4, native_system_count=None, template=TEMPLATE):
        source_root=0x80
        source_rows=[0x1000+i*0x26c for i in range(len(aliases))]
        blocks={(source_root,0x26c):source_rows}
        values={};post_datums={};particle_aliases={}
        for index,(row,alias) in enumerate(zip(source_rows,aliases)):
            post=0x4000+index*140
            option_rows=[0x6000+index*32+j*2 for j in range(len(source_options))]
            blocks[row+0x158,140]=[post]
            blocks[row+0x140,2]=option_rows
            values.update(zip(option_rows,source_options));post_datums[post+12]=9
            if alias is not None:particle_aliases[post]=(alias,None)
        def block(offset,stride):
            # Reject an incorrect source system stride rather than tolerating it.
            self.assertIn((offset,stride),blocks)
            return blocks[offset,stride]
        source=SimpleNamespace(block=block,unpack=lambda fmt,at:(values[at],),
                               u=lambda at:post_datums[at],name=lambda _:template)
        memory=bytearray(0x10000);target_rows=0x1000;option_pointers=[]
        for index in range(len(aliases)):
            p=0x8000+index*32;option_pointers.append(p)
            struct.pack_into('>III',memory,target_rows+index*0x26c+0x140,native_option_count,p,0)
            struct.pack_into('>4h',memory,p,0,1,1,0)
        reads=[];writes=[]
        def read(at,size):
            reads.append((at,size));return bytes(memory[at:at+size])
        def put(at,fmt,*values):
            writes.append((at,fmt,values));struct.pack_into('>'+fmt,memory,at,*values)
        builder=SimpleNamespace(read=read,put=put)
        importer=SimpleNamespace(source=source,builder=builder,
                                 materials=SimpleNamespace(particle_aliases=particle_aliases))
        count=len(aliases) if native_system_count is None else native_system_count
        payload=struct.pack('>III',count,target_rows,0)+b'unchanged-root-tail'
        return importer,source_root,payload,memory,reads,writes,option_pointers

    def test_exact_options_and_root_unchanged(self):
        i,root,payload,memory,reads,writes,pointers=self.fixture()
        before=bytes(memory)
        with patch('dune_projectile.matches',return_value=True) as scope:
            self.assertIs(update_root(i,root,payload),payload)
        scope.assert_called_once_with(i.source,0x4000,'cntl',TEMPLATE)
        self.assertEqual(struct.unpack_from('>4h',memory,pointers[0]),(0,8,1,0))
        self.assertEqual(writes,[(pointers[0],'4h',(0,8,1,0))])
        changed=[n for n,(a,b) in enumerate(zip(before,memory)) if a!=b]
        self.assertEqual(changed,[pointers[0]+3])

    def test_multi_system_native_stride(self):
        i,root,payload,memory,reads,writes,pointers=self.fixture(('_0_8_1_0','other','_0_8_1_0'))
        with patch('dune_projectile.matches',return_value=True):update_root(i,root,payload)
        self.assertEqual(reads,[(0x1000+0x140,8),(0x1000+2*0x26c+0x140,8)])
        self.assertEqual([w[0] for w in writes],[pointers[0],pointers[2]])
        self.assertEqual(struct.unpack_from('>4h',memory,pointers[1]),(0,1,1,0))

    def test_other_templates_or_missing_alias_noop(self):
        for alias,scope_match in [('other',True),(None,True),('_0_8_1_0',False)]:
            with self.subTest(alias=alias,scope_match=scope_match):
                i,root,payload,memory,reads,writes,_=self.fixture((alias,),template='other')
                before=bytes(memory)
                with patch('dune_projectile.matches',return_value=scope_match):
                    self.assertIs(update_root(i,root,payload),payload)
                self.assertEqual(bytes(memory),before);self.assertEqual(reads,[]);self.assertEqual(writes,[])

    def test_source_options_and_counts_fail_closed(self):
        for options in [(0,1,1),(0,1,1,0,0),(0,8,1,0),(1,1,1,0)]:
            with self.subTest(options=options):
                i,root,payload,memory,reads,writes,_=self.fixture(source_options=options)
                with patch('dune_projectile.matches',return_value=True),self.assertRaisesRegex(ValueError,'source options changed'):
                    update_root(i,root,payload)
                self.assertEqual(reads,[]);self.assertEqual(writes,[])

    def test_native_option_count_fail_closed(self):
        for count in (0,3,5):
            i,root,payload,memory,reads,writes,_=self.fixture(native_option_count=count)
            with self.subTest(count=count),patch('dune_projectile.matches',return_value=True),self.assertRaisesRegex(ValueError,'native option count changed'):
                update_root(i,root,payload)
            self.assertEqual(writes,[])

    def test_native_system_count_fail_closed(self):
        for count in (0,2):
            i,root,payload,memory,reads,writes,_=self.fixture(native_system_count=count)
            with self.subTest(count=count),patch('dune_projectile.matches',return_value=True),self.assertRaisesRegex(ValueError,'system count changed'):
                update_root(i,root,payload)
            self.assertEqual(reads,[]);self.assertEqual(writes,[])

if __name__=='__main__':unittest.main()
