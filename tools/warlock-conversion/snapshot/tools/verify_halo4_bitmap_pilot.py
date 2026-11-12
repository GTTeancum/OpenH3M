"""Read native exported pixels through Blender, without editing images."""
from pathlib import Path
from array import array
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT,OUT,sha
def pixels(path):
    im=bpy.data.images.load(str(path),check_existing=False)
    im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED'
    values=array('f',[0])*len(im.pixels);im.pixels.foreach_get(values)
    result=(tuple(im.size),np.clip(np.rint(np.asarray(values)*255),0,255).astype(np.uint8).tobytes())
    bpy.data.images.remove(im)
    return result
all_mode='--all' in sys.argv
name='ordinary-2d' if all_mode else 'pilot'
path=OUT/'bitmap-import'/(name+'.json');pilot=json.loads(path.read_text())
assert pilot['status']=='native_import_and_metadata_pass'
rows=[]
for row in pilot['images']:
    source=ROOT/row['source_image'];target=ROOT/row['export']
    assert sha(source)==row['source_image_sha256'] and sha(target)==row['export_sha256']
    a,original=pixels(source);b,native=pixels(target);assert a==b and len(original)==len(native)
    count=len(original)//4
    delta=np.abs(np.frombuffer(original,dtype=np.uint8).astype(np.int16)-np.frombuffer(native,dtype=np.uint8).astype(np.int16)).reshape((-1,4))
    mean=delta.mean(axis=0).tolist()
    maximum=delta.max(axis=0).tolist()
    channels=2 if row['normal_map'] else 4
    rows.append(dict(source=row['source'],target=row['target'],size=a,normal=row['normal_map'],
        mean_RGBA_error=mean,max_RGBA_error=maximum,channel_check_pass=max(mean[:channels])<=4,
        limitation='Normal XY preservation only; in-engine direction/strength still needs shading verification.' if row['normal_map'] else 'Decoded color/alpha check; final material rendering still pending.'))
    print('H4_BITMAP_PIXEL_CHECK',len(rows),row['source'],rows[-1]['channel_check_pass'],flush=True)
stock=[]
for stock_name in ('color_white','default_vector'):
    p=OUT/'stock-bitmap-candidates/original-construct'/(stock_name+'.dds')
    size,data=pixels(p)
    stock.append(dict(tag='shaders/default_bitmaps/bitmaps/'+stock_name+'.bitmap',source_cache='C:/X360/ISOs/H3M/maps/construct.map',
        extracted_dds_sha256=sha(p),size=size,ranges=[(min(data[c::4]),max(data[c::4])) for c in range(4)]))
assert stock[0]['ranges']==[(255,255)]*4
stock[1]['exact_neutral_xy_match']=stock[1]['ranges'][:2]==[(128,128)]*2
result=dict(images=rows,original_stock_defaults=stock,pixel_channel_checks_pass=all(r['channel_check_pass'] for r in rows),
    actual_rendering_verified=False)
dest=OUT/'bitmap-import'/(name+'-pixel-verification.json');assert not dest.exists()
dest.write_text(json.dumps(result,indent=2)+'\n')
print('H4_BITMAP_PIXELS',len(rows),'passed',result['pixel_channel_checks_pass'],flush=True)
