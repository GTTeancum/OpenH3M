"""Check native H3 bitmap exports against original extracted images; no edits."""
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
DEST=OUT/'wall-detail-trial'
PIXELS=DEST/'verified-pixels'
PIXELS.mkdir(exist_ok=True)
sys.path.insert(0,str(OUT/'python-packages'))
from PIL import Image, ImageChops, ImageStat
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
report=json.loads((DEST/'report.json').read_text())
results=[]
for row in report['imports']:
    result=subprocess.run([str(KIT/'tool.exe'),'export-bitmap-tga',row['target'].rsplit('.',1)[0],str(PIXELS)+os.sep],
        cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (PIXELS/(row['input']+'.log')).write_bytes(result.stdout)
    assert result.returncode==0
    files=sorted(PIXELS.glob(Path(row['target']).stem+'*.tga'))
    original=Image.open(row['source']).convert('RGBA')
    tree=ET.fromstring(Path(row['xml']).read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
    data=tree.find("block[@name='bitmaps']/element")
    saved={f.get('name'):f.get('value') for f in data.findall('field')}
    entry=dict(input=row['input'],source=row['source'],exports=[str(p) for p in files],
        source_size=original.size,source_ranges=original.getextrema(),format=saved['format'],
        curve=saved['curve'],mipmap_count=int(saved['mipmap count']))
    assert entry['mipmap_count']>0
    if row['input']!='environment_map':
        assert len(files)==1
        decoded=Image.open(files[0]).convert('RGBA')
        assert decoded.size==original.size
        entry['mean_absolute_RGBA_difference']=ImageStat.Stat(ImageChops.difference(original,decoded)).mean
        entry['h3_ranges']=decoded.getextrema()
        if row['input'] in ('base_map','detail_map'):
            assert entry['mean_absolute_RGBA_difference']==[0,0,0,0],entry
            assert saved['curve']=='linear'
        else:
            entry['limitation']='DXN stores XY. RGB differences do not establish normal fidelity; normal direction/strength remain unverified.'
    else:
        assert len(files)==6 and original.size==(512,384)
        assert saved['type']=='cube map' and saved['format']=='dxt5'
        # Compare the six native faces to the actual occupied source cross cells.
        # Transforms exist only in memory for measurement, not in imported assets.
        cells=[(0,0),(0,1),(1,1),(2,1),(3,1),(0,2)]
        transforms=[None,Image.Transpose.ROTATE_90,Image.Transpose.ROTATE_180,
                    Image.Transpose.ROTATE_270,Image.Transpose.FLIP_LEFT_RIGHT,
                    Image.Transpose.FLIP_TOP_BOTTOM,Image.Transpose.TRANSPOSE,Image.Transpose.TRANSVERSE]
        matches=[]
        for face in files:
            decoded=Image.open(face).convert('RGB')
            assert decoded.size==(128,128)
            choices=[]
            for x,y in cells:
                crop=original.crop((x*128,y*128,(x+1)*128,(y+1)*128)).convert('RGB')
                for transform in transforms:
                    comparison=crop if transform is None else crop.transpose(transform)
                    errors=ImageStat.Stat(ImageChops.difference(comparison,decoded)).mean
                    choices.append(dict(cell=[x,y],transform='identity' if transform is None else transform.name,mean_RGB_error=errors))
            best=min(choices,key=lambda r:sum(r['mean_RGB_error']))
            assert max(best['mean_RGB_error'])<4,best
            matches.append(dict(export=str(face),**best))
        assert len({tuple(m['cell']) for m in matches})==6
        entry['face_matches']=matches
        entry['limitation']='Face pixels and mapping measured; world-space reflection orientation and H3 shader appearance still need MCC review.'
    results.append(entry)
for path,expected in report['source_hashes'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
output=dict(source_and_stock_hashes_unchanged=True,bitmaps=results,
    limitation='Native Tool outputs inspected as data; not MCC visual acceptance.')
(DEST/'pixel-verification.json').write_text(json.dumps(output,indent=2)+'\n')
for r in results:print(r['input'],r.get('mean_absolute_RGBA_difference',r.get('face_matches')),flush=True)
