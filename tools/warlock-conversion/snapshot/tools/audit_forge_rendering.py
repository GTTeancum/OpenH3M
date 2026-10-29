"""Read-only rendering inventory against stock H3; no map mutations or launches."""
import collections,json,struct,sys
from pathlib import Path
import xml.etree.ElementTree as E
from cache_reader import Cache
from resource_reader import Resource
ROOT=Path(__file__).resolve().parents[4]
REF=Path(__file__).resolve().parents[1]/'reference'

def inspect(path,mcc=False):
 c=Cache(path,mcc); schema=E.parse(REF/('mcc' if mcc else 'plugins')/'sbsp.xml').getroot()
 def rows(root,name):
  f=next(f for f in schema if f.get('name')==name)
  return c.block(root+int(f.get('offset'),0),int(f.get('elementSize'),0))
 result={'bsps':[],'lighting':[]}
 try:
  for t in c.tags.values():
   if t['group']!='sbsp':continue
   root=t['offset'];clusters=rows(root,'Clusters');leaves=rows(root,'Unknown Raw Leaves' if mcc else 'Leaves')
   mats=rows(root,'Materials');portals=rows(root,'Cluster Portals')
   result['bsps'].append({'clusters':len(clusters),'leaves':len(leaves),'leaf_clusters':dict(collections.Counter(c.data[r] for r in leaves)),
    'portals':[c.unpack('hhi',p) for p in portals],
    'cluster_bounds':[c.unpack('6f',r) for r in clusters],
    'cluster_meshes':[c.unpack('h',r+(0xd8 if mcc else 0x9c))[0] for r in clusters],
    'instances':len(rows(root,'Instanced Geometry Instances')),
    'material_groups':dict(collections.Counter(c.tags[c.u(r+12)&65535]['group'] for r in mats if c.u(r+12)!=0xffffffff))})
  roots=([t['offset'] for t in c.tags.values() if t['group']=='Lbsp'] if mcc else
   [b for t in c.tags.values() if t['group']=='sLdT' for b in c.block(t['offset']+4,436)])
  for root in roots:
   resource=Resource(c,c.u(root+0x1ac),{'maps\\shared.map':ROOT/'../../maps/shared.map'})
   vertices=resource.buffers('vertex');indices=resource.buffers('index')
   meshes=[]; errors=[]
   for n,m in enumerate(c.block(root+0x134,76)):
    parts=[c.unpack('hhHHhHBBH',p) for p in c.block(m,16)]
    subparts=[c.unpack('HHhH',p) for p in c.block(m+12,8)]
    slots=c.unpack('8h',m+24);ix=c.unpack('h',m+40)[0]
    record={'parts':parts,'subparts':subparts,'vertex_slots':slots,'index_slot':ix,'flags_types':c.unpack('4B',m+44),'primitive':c.data[m+48]}
    meshes.append(record)
    for slot in slots:
     if slot < -1 or slot>=len(vertices):errors.append([n,'vertex binding',slot])
    if ix < -1 or ix>=len(indices):errors.append([n,'index binding',ix])
    if parts and ix>=0:
     size=resource.unpack('I',indices[ix]+4)[0]//2
     for p in parts:
      if p[2]+p[3]>size:errors.append([n,'part index range',p[2],p[3],size])
      if p[4]<0 or p[4]+p[5]>len(subparts):errors.append([n,'part subpart range'])
     for p in subparts:
      if p[0]+p[1]>size or not 0<=p[2]<len(parts):errors.append([n,'subpart range'])
   result['lighting'].append({'flags':c.unpack('H',root)[0],'geometry_flags':c.u(root+0x130),
    'clusters':[c.unpack('2h',r) for r in c.block(root+0x10c,4)],
    'instances':[c.unpack('4h',r) for r in c.block(root+0x118,8)],
    'compression':[c.unpack('HH10f',r) for r in c.block(root+0x140,44)],
    'mesh_mopp_count':c.u(root+0x170),'subpart_visibility_count':c.u(root+0x188),
    'vertex_formats':dict(collections.Counter(str(resource.unpack('HH',p+4)) for p in vertices)),
    'decoded_resource_bytes':sum(map(len,resource.raw)), 'meshes':meshes,'binding_errors':errors})
  return result
 finally:c.close()

if __name__=='__main__':
 report={name:inspect(ROOT/'../../maps'/f'{name}.map') for name in ('sandbox','zanzibar','riverworld','sidewinder','chill','guardian')}
 report['source']=inspect(r'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map',True)
 report['candidate']=inspect(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work/forge-world/sandbox-sky.map')
 differences=[]
 for bi,(s,d) in enumerate(zip(report['source']['lighting'],report['candidate']['lighting'])):
  for key in ('flags','geometry_flags','clusters','instances','compression','mesh_mopp_count','subpart_visibility_count','meshes'):
   if s[key]!=d[key]:differences.append([bi,key])
 report['source_candidate_differences']=differences
 (ROOT/'work/forge-world/render-reference-audit.json').write_text(json.dumps(report,indent=2))
 for name,data in report.items():
  if name=='source_candidate_differences':print(name,data);continue
  print(name,{'clusters':[b['clusters'] for b in data['bsps']],'instances':[b['instances'] for b in data['bsps']],
   'meshes':[len(b['meshes']) for b in data['lighting']], 'binding_errors':[len(b['binding_errors']) for b in data['lighting']],
   'mopps':[b['mesh_mopp_count'] for b in data['lighting']], 'visibility':[b['subpart_visibility_count'] for b in data['lighting']]})
