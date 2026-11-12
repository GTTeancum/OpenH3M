import unittest
from reach_mesh_split import split_triangle_ranges

class SplitTests(unittest.TestCase):
 def test_crossing_subpart(self):
  indices=list(range(18))
  parts=[dict(first=0,count=18,subpart_start=0,subpart_count=2,material=7)]
  subs=[dict(first=0,count=12,part=0),dict(first=12,count=6,part=0)]
  result=split_triangle_ranges(indices,parts,subs,9)
  self.assertEqual([i for r in result for i in r['indices']],indices)
  self.assertEqual([[(s['first'],s['count'],s['source_subpart']) for s in r['subparts']] for r in result], [[(0,9,0)],[(0,3,0),(3,6,1)]])
  self.assertTrue(all(r['parts'][0]['material']==7 for r in result))
  self.assertEqual(subs[0]['count'],12)
 def test_invalid_topology(self):
  with self.assertRaises(ValueError):split_triangle_ranges([0,1],[],[])
  with self.assertRaises(ValueError):split_triangle_ranges([0,1,65536],[],[])

if __name__=='__main__':unittest.main()
