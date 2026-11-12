"""Read exported H3 cube faces/glass pixels; do not render or edit images."""
from pathlib import Path
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT,OUT,sha
def pixels(path):
    im=bpy.data.images.load(str(path),check_existing=False)
    im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED'
    w,h=im.size;data=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(data)
    bpy.data.images.remove(im)
    return np.clip(np.rint(data.reshape((h,w,4))[::-1]*255),0,255).astype(np.int16)
name='cube-defaults' if '--cube-defaults' in sys.argv else 'special'
report=json.loads((OUT/'bitmap-import'/(name+'.json')).read_text())
assert report['status']=='native_import_and_metadata_pass'
positions={'U':(0,0),'D':(0,2),'F':(0,1),'R':(1,1),'B':(2,1),'L':(3,1)}
rows=[]
for row in report['images']:
    source=ROOT/row['source_image'];assert sha(source)==row['source_image_sha256']
    original=pixels(source);checks=[]
    for index,export in enumerate(row['exports']):
        path=ROOT/export['path'];assert sha(path)==export['sha256'];native=pixels(path)
        if row['cube_map']:
            size=int(row['saved']['width']);assert native.shape==(size,size,4)
            candidates=[]
            for face,(x,y) in positions.items():
                tile=original[y*size:(y+1)*size,x*size:(x+1)*size]
                for flipped in (False,True):
                    for turns in range(4):
                        expected=np.rot90(tile[:,::-1] if flipped else tile,turns)
                        delta=np.abs(native-expected)
                        candidates.append(dict(face=face,mirror_x=flipped,quarter_turns=turns,
                            mean_RGBA_error=delta.mean(axis=(0,1)).tolist(),max_RGBA_error=delta.max(axis=(0,1)).tolist()))
            best=min(candidates,key=lambda c:max(c['mean_RGBA_error']))
            # Content preservation check only: selecting best alignment cannot
            # prove world-space orientation or distinguish symmetric cube faces.
            checks.append(dict(export_index=index,best_content_match=best,content_pass=max(best['mean_RGBA_error'])<=4))
        else:
            assert native.shape==original.shape
            delta=np.abs(native-original)
            checks.append(dict(mean_RGBA_error=delta.mean(axis=(0,1)).tolist(),max_RGBA_error=delta.max(axis=(0,1)).tolist(),
                content_pass=float(delta.mean(axis=(0,1)).max())<=4))
    rows.append(dict(source=row['source'],target=row['target'],cube_map=row['cube_map'],checks=checks,
        content_pass=all(c['content_pass'] for c in checks),precision_limitation=row['precision_limitation']))
    print('H4_SPECIAL_BITMAP_PIXELS',row['source'],rows[-1]['content_pass'],flush=True)
dest=OUT/'bitmap-import'/(name+'-pixel-verification.json');assert not dest.exists()
dest.write_text(json.dumps(dict(images=rows,all_content_checks_pass=all(r['content_pass'] for r in rows),
    cube_world_orientation_verified=False,actual_rendering_verified=False),indent=2)+'\n')
