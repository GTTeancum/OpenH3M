import unittest
from types import SimpleNamespace
from dune_decal import matches, encode, SCENARIO, NAME, TEMPLATE, BUILD

class DuneDecalTests(unittest.TestCase):
    def source(self,scenario=SCENARIO,build=BUILD):
        return SimpleNamespace(tags={0:{'group':'scnr'},1:{'group':'decs','offset':100}},
            name=lambda k:[scenario,NAME][k],
            block=lambda offset,stride:{120:[200],248:[300]}.get(offset,[]),
            data=bytes(0xa0)+build.encode().ljust(32,b'\0'))
    def test_exact_post_scope(self):
        self.assertTrue(matches(self.source(),300,'decs',TEMPLATE))
        self.assertFalse(matches(self.source(),301,'decs',TEMPLATE))
        self.assertFalse(matches(self.source('other'),300,'decs',TEMPLATE))
        self.assertFalse(matches(self.source(),300,'prt3',TEMPLATE))
        self.assertFalse(matches(self.source(),300,'decs','other'))
        with self.assertRaises(ValueError):matches(self.source(build='other'),300,'decs',TEMPLATE)
    def test_combines_every_npot_and_tiny_authored_level(self):
        from dune_decal import join_bc3_chains
        from encode_bitmap import mip_size
        for w,h,count in ((768,384,10),(7,3,3),(1,1,1)):
            sizes=[mip_size(max(1,w>>n),max(1,h>>n),16) for n in range(count)]
            base=bytes((i*17+11)%256 for i in range(sum(sizes)))
            mask=bytes((i*23+97)%256 for i in range(sum(sizes)))
            result=join_bc3_chains(base,mask,w,h,count)
            expected=b''.join(mask[o:o+8]+base[o+8:o+16] for o in range(0,len(base),16))
            self.assertEqual(result,expected)
            self.assertEqual(len(result),sum(sizes))
            for broken in (base[:-1],base+b'\0'):
                with self.assertRaises(ValueError):join_bc3_chains(broken,mask,w,h,count)

    def test_actual_source_full_chain_roundtrip_when_available(self):
        from pathlib import Path
        import numpy as np
        from cache_reader import Cache
        from mcc_bitmap_source import BitmapSource
        from dune_decal import NAMES,join_bc3_chains
        from xbox_mip_chain import layout
        path=Path(__file__).resolve().parents[5]/'references/halo3/mcc-final/extracted/dune.map'
        if not path.exists():self.skipTest('Exact Dune source not installed')
        source=Cache(path,True)
        try:
            bitmaps=BitmapSource(source)
            tags=[next(k for k,t in source.tags.items() if t['group']=='bitm' and source.name(k)==name) for name in NAMES]
            record,control,payload=encode(bitmaps,*tags)
            expected=join_bc3_chains(*(bitmaps.pixels(k) for k in tags),768,384,10)
            rows,size=layout(768,384,10,16,4);decoded=[]
            tiled=np.frombuffer(payload,dtype=np.uint8)
            for positions,length in rows:
                blocks=tiled[positions.reshape(-1,1)+np.arange(16)]
                decoded.append(blocks.reshape(-1,2)[:,::-1].tobytes())
            self.assertEqual(b''.join(decoded),expected)
            self.assertEqual(len(payload),size)
            self.assertEqual(record[20]+1,10);self.assertEqual(control[45],10)
        finally:source.close()

    def test_bitmap_guard(self):
        with self.assertRaises(ValueError):encode(SimpleNamespace(c=SimpleNamespace(name=lambda k:'other')),1,2)

if __name__=='__main__':unittest.main()
