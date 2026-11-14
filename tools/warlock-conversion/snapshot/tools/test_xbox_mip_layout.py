"""Independent scalar XG address oracle and Xenia guest-layout regressions.

Primary references: xenia-project/xenia src/xenia/gpu/texture_util.cc,
GetPackedMipOffset and GetGuestTextureLayout, commit
95a5c3ee250f80c3b9d139658649d9ffb6db3eec (reviewed 2026-11-14).
The oracle uses scalar XG macro/micro algebra, never production addresses().
"""
import unittest
import hashlib
import numpy as np
from test_xbox_bitmap import scalar_address
from xbox_mip_chain import layout, tile_chain, cube_layout, tile_cube_chain


def oracle(w, h, count, bpb, extent):
    lw, lh = (w-1).bit_length(), (h-1).bit_length()
    packed_level = max(0, min(lw, lh)-4)
    offset = 0
    result = []
    for level in range(count):
        bw = (max(1,w >> level)+extent-1)//extent
        bh = (max(1,h >> level)+extent-1)//extent
        storage_level = min(level, packed_level)
        sw = w if level == 0 else max(1,(1 << lw) >> storage_level)
        sh = h if level == 0 else max(1,(1 << lh) >> storage_level)
        pitch = ((sw+extent-1)//extent+31)//32*32
        rows = ((sh+extent-1)//extent+31)//32*32
        x = y = 0
        if level >= packed_level:
            p = level-packed_level
            if p < 3:
                if lw > lh: y=16 >> p
                else: x=16 >> p
            elif lw > lh: x=(1 << (lw-packed_level)) >> (p-2)
            else: y=(1 << (lh-packed_level)) >> (p-2)
        x //= extent; y //= extent
        result.append(np.array([[offset+scalar_address(x+i,y+j,pitch,bpb.bit_length()-1)
                                 for i in range(bw)] for j in range(bh)],dtype=np.uint32))
        if level < packed_level: offset += (pitch*rows*bpb+4095)//4096*4096
    return result


class LayoutTests(unittest.TestCase):
    def test_independent_oracle_no_overlap_roundtrip(self):
        for w,h in ((768,384),(33,65),(80,260),(17,31),(24,32),(8,8),
                    (2,2),(1,16),(16,1),(80,8),(8,80),(128,2),(32,32),(256,128)):
            for fmt,bpb,e,swap in ((11,4,1,4),(22,2,1,2),(26,4,1,4),(28,8,1,2),
                                  (14,8,4,2),(15,16,4,2),(16,16,4,2),(33,16,4,2)):
                with self.subTest(w=w,h=h,fmt=fmt):
                    count=max(w,h).bit_length()
                    rows,size=layout(w,h,count,bpb,e)
                    expected=oracle(w,h,count,bpb,e)
                    seen=set()
                    for (pos,n),ref in zip(rows,expected):
                        np.testing.assert_array_equal(pos,ref)
                        self.assertEqual(pos.size*bpb,n)
                        for a in pos.flat:
                            self.assertNotIn(int(a),seen)
                            seen.add(int(a))
                            self.assertLessEqual(int(a)+bpb,size)
                    payload=bytes((i*37+i//251)%256 for i in range(sum(n for _,n in rows)))
                    raw=np.frombuffer(tile_chain(payload,w,h,count,fmt),dtype=np.uint8)
                    recovered=b''.join(raw[ref.reshape(-1,1)+np.arange(bpb)].reshape(-1,swap)[:,::-1].tobytes() for ref in expected)
                    self.assertEqual(payload,recovered)

    def test_cube_small_and_npot(self):
        for w in (2,8,24,33,64):
            for fmt,bpb,e in ((11,4,1),(14,8,4),(16,16,4)):
                faces,size=cube_layout(w,w.bit_length(),fmt)
                seen=set()
                for face in faces:
                    for pos,n in face:
                        self.assertEqual(pos.size*bpb,n)
                        for address in pos.flat:
                            self.assertNotIn(int(address),seen)
                            seen.add(int(address))
                            self.assertLessEqual(int(address)+bpb,size)
                payload=bytes((i*23+i//197)%256 for i in range(sum(n for f in faces for _,n in f)))
                raw=np.frombuffer(tile_cube_chain(payload,w,w.bit_length(),fmt),dtype=np.uint8)
                swap=4 if fmt==11 else 2
                recovered=b''.join(raw[p.reshape(-1,1)+np.arange(bpb)].reshape(-1,swap)[:,::-1].tobytes() for f in faces for p,n in f)
                self.assertEqual(payload,recovered)

    def test_legacy_pot_address_fingerprints(self):
        # Captured from pre-change HEAD, not computed by the new implementation.
        cases = ((32,32,2,1,8192,'5c3babd9dd7c604fd86b9081147ed00b9c512cb2529b77bd48dd9c6e8febd539'),
                 (256,128,16,4,73728,'f1e78617f40187c8e74983bfb2b28640e71372f15669b09d7edbc08b9070f8e2'),
                 (128,512,4,1,352256,'fca6bb40bb0eeb07bf68c7db1f8f2546c68d82475da2339d64462ce07064f322'))
        for w,h,b,e,size,digest in cases:
            rows,actual=layout(w,h,max(w,h).bit_length(),b,e)
            self.assertEqual(actual,size)
            self.assertEqual(hashlib.sha256(b''.join(p.astype('<u4').tobytes() for p,n in rows)).hexdigest(),digest)

    def test_count_and_payload_rejected_not_truncated(self):
        for count in (0,1,7):
            with self.assertRaises(ValueError): layout(33,17,count)
        with self.assertRaises(ValueError): tile_chain(b'\0'*16,8,8,4,16)
        for w,h in ((0,4),(-1,8),(8193,4)):
            with self.assertRaises(ValueError): layout(w,h,3)

if __name__=='__main__':unittest.main()
