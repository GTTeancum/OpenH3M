"""Use released Foundry face orientation and TIFF writer for H3 cube authoring.

Only rearranges unchanged texels into the cross consumed by H3's cube slicer.
No filtering, new cube decoder, equirectangular resampling or source edits.
"""
from pathlib import Path
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT,OUT,setup,sha
setup()
from io_scene_foundry.managed_blam.bitmap import BitmapTag
destination=OUT/'bitmap-cube-crosses';destination.mkdir(exist_ok=True)
report_path=OUT/'haven-cube-cross-sources.json';assert not report_path.exists()
source=json.loads((OUT/'haven-bitmap-sources.json').read_text())
rows=[]
# Same cross face positions as BitmapTag.cubemap_to_equirectangular's H3 path.
positions={'U':(0,0),'D':(0,2),'F':(0,1),'R':(1,1),'B':(2,1),'L':(3,1)}
for row in source['bitmaps']:
    frame=row['frames'][0]
    if frame['type']['value']!=2:continue
    original=ROOT/row['images'][0]['path'];assert sha(original)==row['images'][0]['sha256']
    image=bpy.data.images.load(str(original),check_existing=False)
    image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED'
    size=frame['width']['value'];assert tuple(image.size)==(size,size*6)
    values=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(values)
    strip=np.clip(np.rint(values.reshape((size*6,size,4))[::-1]*255),0,255).astype(np.uint8)
    bpy.data.images.remove(image)
    faces=BitmapTag._cubemap_faces_from_vertical_rgba(strip.tobytes(),size)
    cross=np.zeros((size*3,size*4,4),dtype=np.uint8)
    for face,(x,y) in positions.items():cross[y*size:(y+1)*size,x*size:(x+1)*size]=faces[face]
    path=destination/(Path(row['source']).stem+'.tiff');assert not path.exists()
    BitmapTag._write_rgba_tiff(str(path),size*4,size*3,cross.tobytes())
    # Reload through Blender to verify authored tile bytes, not merely file size.
    image=bpy.data.images.load(str(path),check_existing=False)
    image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED'
    values=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(values)
    decoded=np.clip(np.rint(values.reshape(cross.shape)[::-1]*255),0,255).astype(np.uint8)
    bpy.data.images.remove(image);assert np.array_equal(decoded,cross)
    for face,(x,y) in positions.items():assert np.array_equal(decoded[y*size:(y+1)*size,x*size:(x+1)*size],faces[face])
    assert sha(original)==row['images'][0]['sha256']
    rows.append(dict(source=row['source'],strip=str(original.relative_to(ROOT)),strip_sha256=sha(original),
        path=str(path.relative_to(ROOT)),sha256=sha(path),face_size=size,exact_face_tiles=True,
        orientation_method='Released Foundry _cubemap_faces_from_vertical_rgba; H3 cross positions from cubemap_to_equirectangular'))
report_path.write_text(json.dumps(dict(cubes=rows,source_unchanged=True,native_import_verified=False),indent=2)+'\n')
print('H4_CUBE_CROSSES_PREPARED',len(rows),flush=True)
