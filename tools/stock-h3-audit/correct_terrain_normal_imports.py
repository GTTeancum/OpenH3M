"""Correct existing trial RGB normals using official H3 Tool import settings."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
DEST=OUT/'terrain-normal-verification'
DEST.mkdir(exist_ok=True)
sys.path.insert(0,str(OUT/'python-packages'))
from PIL import Image, ImageChops, ImageStat
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
trial=json.loads((OUT/'terrain-trial-report.json').read_text())
rows=[]
def tool(*args):
    result=subprocess.run([str(KIT/'tool.exe'),*args],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (DEST/(Path(args[1]).stem+'-'+args[0]+'.log')).write_bytes(result.stdout)
    assert result.returncode==0, result.stdout.decode(errors='replace')
    if args[0]=='patch-tag-field':
        assert b'field successfully patched' in result.stdout
for tag,info in trial['imports'].items():
    inputs=[b['input'] for b in trial['bindings'] if b['reference']==tag.rsplit('.',1)[0]+',bitm']
    if not any('bump_map' in name for name in inputs):
        continue
    source=Path(info['source'])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==info['image_sha256']
    tool('patch-tag-field',tag,'bitmap_block_struct[0].Usage','ZBrush Bump Map (from Bump Map)')
    tool('bitmap_single',str(Path(tag).with_suffix('.tif')))
    exported=DEST/(Path(tag).stem+'.xml')
    tool('export-tag-to-xml',str(KIT/'tags'/tag),str(exported))
    tree=ET.fromstring(exported.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
    usage=tree.find("field[@name='Usage']").get('value')
    assert usage=='ZBrush Bump Map (from Bump Map)', usage
    tool('export-bitmap-tga',tag.rsplit('.',1)[0],str(DEST)+os.sep)
    original=Image.open(source).convert('RGB')
    decoded=Image.open(DEST/(Path(tag).stem+'_00_00.tga')).convert('RGB')
    assert original.size==decoded.size
    rows.append(dict(tag=tag,source=str(source),usage=usage,xml=str(exported),
                     size=original.size,
                     mean_absolute_RGB_difference=ImageStat.Stat(ImageChops.difference(original,decoded)).mean,
                     limitation='Official import mode and dimensions verified. DXN output is not byte-identical RGB; normal shading still needs MCC review.'))
assert len(rows)==3
(DEST/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
print('CORRECTED_RGB_NORMAL_IMPORTS',len(rows),flush=True)
