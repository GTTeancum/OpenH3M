import sys,json,struct
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
source=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
report={'source':[],'native_candidates':[]}
def tagname(c,d):return c.name(d&65535) if d != 0xffffffff else None
for i,t in source.tags.items():
 if t['group']!='lens' or 's3d_sky' not in source.name(i):continue
 a=t['offset'];entry={'name':source.name(i),'occlusion_index':source.unpack('i',a+8)[0],'flags':source.unpack('H',a+52)[0],'bitmap':tagname(source,source.u(a+48)),'reflections':[]}
 for r in source.block(a+68,156):
  row={'flags':source.unpack('H',r)[0],'bitmap':tagname(source,source.u(r+20)),'image':source.unpack('H',r+4)[0],'rotation_axis_bounds':source.unpack('4f',r+24),'color':source.unpack('5f',r+136),'curves':{}}
  for name,off in [('radius',56),('x',76),('y',96),('brightness',116)]:
   size=source.u(r+off);p=source.pointer(source.u(r+off+12));raw=bytes(source.data[p:p+size]);row['curves'][name]={'raw':raw.hex(),'bounds':struct.unpack_from('<2f',raw,4)}
  entry['reflections'].append(row)
 report['source'].append(entry)
source.close()
for file in sorted(Path('C:/X360/ISOs/H3M/maps').glob('*.map')):
 if file.name in ('shared.map','campaign.map'):continue
 c=Cache(file)
 for i,t in c.tags.items():
  if t['group']=='lens':
   a=t['offset'];report['native_candidates'].append({'map':file.name,'name':c.name(i),'bitmap':tagname(c,c.u(a+44)),'reflections':c.u(a+64)})
 c.close()
Path('work/sky-bridge/lens-audit.json').write_text(json.dumps(report,indent=2))
print('source flares',len(report['source']),'native flares',len(report['native_candidates']))
print('native names',sorted(set(r['name'] for r in report['native_candidates'])))
