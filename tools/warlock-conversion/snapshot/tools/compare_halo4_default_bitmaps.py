"""Numerically inspect extracted images with Blender; no image edits/captures."""
from pathlib import Path
from array import array
import hashlib
import json
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT,OUT,sha
source=json.loads((OUT/'haven-bitmap-sources.json').read_text())
stock=json.loads((OUT/'stock-bitmap-candidates/inventory.json').read_text())
def inspect(row):
    path=ROOT/row['path'];assert sha(path)==row['sha256']
    image=bpy.data.images.load(str(path),check_existing=False)
    image.colorspace_settings.name='Non-Color'
    pixels=array('f',[0])*len(image.pixels);image.pixels.foreach_get(pixels)
    rgba=bytes(max(0,min(255,round(v*255))) for v in pixels)
    channels=[rgba[c::4] for c in range(4)]
    ranges=[(min(c),max(c)) for c in channels]
    result=dict(path=row['path'],sha256=row['sha256'],size=list(image.size),
        decoded_rgba_sha256=hashlib.sha256(rgba).hexdigest(),ranges=ranges,
        constant_rgba=[v[0] for v in ranges] if all(lo==hi for lo,hi in ranges) else None)
    bpy.data.images.remove(image)
    return result
targets=[]
for row in stock['candidates']:
    targets.append(dict(tag=row['tag'],images=[inspect(im) for im in row['images']]))
sources=[]
for row in source['bitmaps']:
    if not row['source'].startswith('shaders/default_bitmaps/'):continue
    image=inspect(row['images'][0]);matches=[]
    for target in targets:
        if image['constant_rgba'] is not None and all(i['constant_rgba']==image['constant_rgba'] for i in target['images']):
            matches.append(dict(tag=target['tag'],match='same constant RGBA across all faces'))
        elif len(target['images'])==1 and image['size']==target['images'][0]['size'] and image['decoded_rgba_sha256']==target['images'][0]['decoded_rgba_sha256']:
            matches.append(dict(tag=target['tag'],match='same dimensions and decoded RGBA'))
    sources.append(dict(source=row['source'],curve=row['frames'][0]['curve'],image=image,candidates=matches))
report=dict(method='Native Blender Non-Color image reads, RGBA8 numeric comparison',sources=sources,stock=targets,
    reuse_accepted=False,limitation='Candidate comparison only; confirm original-disc/shared resource identity, source/target curves, shader channel use and native sampling before substitution.')
path=OUT/'haven-default-bitmap-comparison.json';assert not path.exists()
path.write_text(json.dumps(report,indent=2)+'\n')
print('H4_DEFAULT_BITMAP_COMPARISON',json.dumps([dict(source=r['source'],constant=r['image']['constant_rgba'],candidates=r['candidates']) for r in sources]),flush=True)
