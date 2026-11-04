"""Inspect every imported wall-family texture using official native exports."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
parser=argparse.ArgumentParser()
parser.add_argument('--family',choices=sorted(json.loads(Path(__file__).with_name('material_families.json').read_text())),default='wall')
parser.add_argument('--reuse-exports',action='store_true',help='Compare existing native exports without rerunning export commands')
args=parser.parse_args()
DEST=OUT/(args.family+'-family')
PIXELS=DEST/'verified-pixels'
PIXELS.mkdir(exist_ok=True)
sys.path.insert(0,str(OUT/'python-packages'))
from PIL import Image,ImageChops,ImageStat
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
report=json.loads((DEST/'report.json').read_text())
source_settings={v['tag']:v for v in json.loads((OUT/(args.family+'-family-bitmap-settings.json')).read_text())}
results=[]
problems=[]
for index,(path,entry) in enumerate(report['images'].items()):
    log=PIXELS/(Path(path).stem+'.log')
    if not args.reuse_exports:
        run=subprocess.run([str(KIT/'tool.exe'),'export-bitmap-tga',entry['target'].rsplit('.',1)[0],str(PIXELS)+os.sep],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        log.write_bytes(run.stdout)
        assert run.returncode==0,path
    output=log.read_bytes()
    assert b'failed to save' not in output,path
    source=Image.open(entry['source']).convert('RGBA')
    files=sorted(PIXELS.glob(Path(path).stem+'_00_*.tga'))
    target=KIT/'tags'/entry['target']
    assert files and all(p.stat().st_mtime_ns>=target.stat().st_mtime_ns for p in files),'Native exports are stale: '+path
    role=entry['roles'][0]
    row=dict(source=path,target=entry['target'],role=role,source_curve=entry['source_curve'],h3_curve=entry['saved']['curve'],exports=[str(f) for f in files],native_direct_save_fallback=b'attempting to save directly' in output)
    row['target_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    row['source_mipmaps']=int(source_settings[path]['bitmaps'][0]['mipmap count'])
    row['h3_mipmaps']=int(entry['saved']['mipmap count'])
    assert row['h3_mipmaps']==row['source_mipmaps'],('Mipmap count differs',path,row['source_mipmaps'],row['h3_mipmaps'])
    if role=='environment_map':
        assert len(files)==6,path
        size=source.width//4
        assert source.size==(size*4,size*3)
        matches=[]
        for face in files:
            decoded=Image.open(face).convert('RGB');assert decoded.size==(size,size)
            choices=[]
            for x,y in [(0,0),(0,1),(1,1),(2,1),(3,1),(0,2)]:
                cell=source.crop((x*size,y*size,(x+1)*size,(y+1)*size)).convert('RGB')
                for operation in [None,*Image.Transpose]:
                    comparison=cell if operation is None else cell.transpose(operation)
                    errors=ImageStat.Stat(ImageChops.difference(comparison,decoded)).mean
                    choices.append(dict(cell=[x,y],operation='identity' if operation is None else operation.name,mean_RGB_error=errors))
            best=min(choices,key=lambda c:sum(c['mean_RGB_error']))
            matches.append(dict(export=str(face),**best))
            if max(best['mean_RGB_error'])>4:problems.append(dict(bitmap=path,reason='cube pixel difference',face=str(face),errors=best))
        assert len({tuple(m['cell']) for m in matches})==6,path
        row['face_matches']=matches
        row['limitation']='Cube faces checked; world-space orientation and reflection response await MCC rendering.'
    else:
        assert len(files)==1,path
        decoded=Image.open(files[0]).convert('RGBA');assert source.size==decoded.size
        row['source_ranges']=source.getextrema();row['h3_ranges']=decoded.getextrema()
        row['mean_RGBA_error']=ImageStat.Stat(ImageChops.difference(source,decoded)).mean
        if role in ('bump_map','bump_detail_map'):
            row['limitation']='DXN direction and strength not established by RGB differences. Native-source comparison and MCC shading checks remain required.'
        elif max(row['mean_RGBA_error'])>4:
            problems.append(dict(bitmap=path,reason='color or alpha difference',errors=row['mean_RGBA_error']))
    results.append(row)
    if index%10==0:print('TEXTURES_CHECKED',index+1,'of',len(report['images']),flush=True)
for path,expected in report['source_hashes'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
output=dict(source_hashes_unchanged=True,textures=results,color_alpha_problems=problems,
    limitation='Pixel evidence only. No map compilation, visual acceptance or 360 conversion.')
(DEST/'pixel-verification.json').write_text(json.dumps(output,indent=2)+'\n')
print('WALL_TEXTURE_CHECKS',len(results),'color/alpha issues',len(problems),flush=True)
assert not problems,problems
