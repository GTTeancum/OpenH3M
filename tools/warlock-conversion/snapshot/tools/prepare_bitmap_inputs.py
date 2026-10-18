import json,hashlib
from pathlib import Path
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
R=Path.cwd();c=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map',True);source=BitmapSource(c)
a=json.loads((R/'.local/reports/mcc-visual-data.json').read_text());materials=next(b['materials'] for b in a['9178:sbsp']['blocks'] if b['name']=='Materials');ids=sorted({int(t['datum'],16)&65535 for m in materials for t in m['textures'] if t['name']})
report={'textures':[],'validated_payloads':[]}
for i in ids:report['textures'].append({'tag':i,'name':c.name(i),'bitmaps':source.info(i)})
for i in (0x2a42,0x2a45,0x2a43):
 payload=source.pixels(i);report['validated_payloads'].append({'tag':i,'name':c.name(i),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
(R/'.local/reports/bitmap-conversion-inputs.json').write_text(json.dumps(report,indent=2));print('Unique texture tags',len(ids));print('Formats',sorted({b['format'] for t in report['textures'] for b in t['bitmaps']}));print(json.dumps(report['validated_payloads'],indent=2));c.close()
