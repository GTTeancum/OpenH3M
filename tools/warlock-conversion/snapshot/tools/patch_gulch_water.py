"""Patch Gulch's water, waterfalls and driftwood without rebuilding its terrain."""
import argparse,hashlib,json,struct,xml.etree.ElementTree as ET
from pathlib import Path
from cache_reader import Cache
from map_builder import MapBuilder
from cache_registry import CacheRegistry
from tag_importer import TagImporter
from native_assets import NativeAssets
from build_scenario_checkpoint import resource_salt
ROOT=Path(__file__).resolve().parents[4]
NAMES={r'levels\multi\forge_halo\shaders\forge_driftwood_bark'} | {
 r'levels\multi\forge_halo\shaders\water\forge_halo_'+v for v in
 ('waterfall_upper_small','waterfall_upper_big','waterfall_lower_small','waterfall_lower_big',
  'ocean_water','puddles','tide_pool_water','cave_water')}
def build(basis,source,disc,xex,output,report):
 for p in (output,report):
  if not p.resolve().is_relative_to(ROOT) or p.exists():raise ValueError('Use new repository-local outputs')
 digest=hashlib.sha256(basis.read_bytes()).hexdigest()
 if digest!='764fb94278b8df323f52f221dd2b9bce4f4b486a02052d9ce7cce4379f19bc0a':
  raise ValueError('Expected accepted lighting/scenery Gulch basis')
 s=Cache(source,True);b=MapBuilder(basis,0x200000);c=b.cache
 r=CacheRegistry(b,resource_salt(xex));i=TagImporter(s,r,disc_maps=disc)
 i.native_assets=NativeAssets(i,disc);i.materials.native_assets=i.native_assets;i.stock_forge_palette=True
 i.materials.preserve_normal_mips=True;i.materials.opaque_prototype=r'objects\vehicles\scorpion\shaders\scorpion_guts'
 result={'basis_sha256':digest,'replaced':[]}
 try:
  def tables(cache,kind):
   f=next(f for f in ET.parse(i.reference/kind/'sbsp.xml').getroot() if f.get('name')=='Materials')
   return [cache.block(t['offset']+int(f.get('offset'),0),int(f.get('elementSize'),0)) for t in cache.tags.values() if t['group']=='sbsp']
  src,dst=tables(s,'mcc'),tables(c,'plugins')
  if [len(v) for v in src]!=[87,29] or list(map(len,src))!=list(map(len,dst)):raise ValueError('BSP materials changed')
  mapping={}
  for ss,dd in zip(src,dst):
   for sr,dr in zip(ss,dd):
    sd=s.u(sr+12);td=c.u(dr+12)
    if sd==0xffffffff or s.name(sd&65535) not in NAMES:continue
    if sd in mapping and mapping[sd]!=td:raise ValueError('Conflicting material binding')
    mapping[sd]=td
  if len(mapping)!=9:raise ValueError('Missing requested environment materials')
  for sd,td in mapping.items():
   group=s.tags[sd&65535]['group'];old=c.tags[td&65535]
   if old['group']!=group or old['salt']!=td>>16:raise ValueError('Invalid old material')
   _,new=i.water.shader(sd) if group=='rmw ' else i.materials.shader(sd)
   address=struct.unpack_from('>I',r.tags,(new&65535)*8+4)[0]
   size=64 if group=='rmw ' else 68
   start=r.address(old['offset'])-b.base
   b.meta[start:start+size]=b.read(address,size)
   result['replaced'].append({'source':s.name(sd&65535),'preserved_datum':hex(td)})
  manifests=c.block(r.manifest_field,120)
  if len(manifests)!=2 or b.read(r.address(manifests[0]),120)!=b.read(r.address(manifests[1]),120):raise ValueError('Expected shared BSP residency union')
  i.finalize();p=r.address(manifests[1])-b.base;b.meta[p:p+120]=b.read(r.address(manifests[0]),120)
  payload=b.finish(r.salt);output.write_bytes(payload)
  result.update(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),materials=i.materials.report,
                status='built; native visual and animation verification required')
  report.write_text(json.dumps(result,indent=2)+'\n');print(output,len(payload),result['sha256'])
 finally:b.close();s.close()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('basis','source','disc','xex','output','report'):p.add_argument('--'+n,type=Path,required=True)
 build(**vars(p.parse_args()))
