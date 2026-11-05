"""Import the original projected-light texture through Foundry and official Tool."""
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek';REACH=ROOT/'work/editing-kits/hrek'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp'),('BLENDER_USER_CONFIG','profile/blender')]:env[key]=str(OUT/path)
source=json.loads((OUT/'original-placed-light-inputs.json').read_text(encoding='utf-8'))['gel']
assert sha(REACH/'tags'/source['source'])==source['sha256']
assert source['bitmaps']==[dict(width='512',height='128',format='11',**{'mipmap count':'9','curve':'3'})]
def run(command,label,cwd=ROOT):
    with (OUT/('light-gel-'+label+'.log')).open('wb') as log:
        result=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    assert result.returncode==0,label
image=(REACH/'data'/source['source']).with_suffix('.tiff')
target=r'levels\custom\battle_canyon_fresh\bitmaps\ca_bcreek_forerunner_lightgel.bitmap'
data=(KIT/'data'/target).with_suffix('.tif');tag=KIT/'tags'/target
template=KIT/'tags/shaders/default_bitmaps/bitmaps/color_white.bitmap';before=sha(template)
plan=dict(Kit=str(KIT),Bitmaps=[dict(Path=target,Usage='Diffuse Map',Format='24-bit Color + 8-bit Alpha',LinearSource=True,ClearOverride=True,MaxMipmapLevel=0)])
plan_path=OUT/'h3-light-gel-import-plan.json'
if '--verify-only' not in sys.argv:
    assert not tag.exists(),'Inspect existing light-gel checkpoint before rerunning'
    run([r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe','--background','--factory-startup','--python-exit-code','1',
         '--python',str(ROOT/'tools/stock-h3-audit/extract_reach_bitmaps.py'),'--',source['source']],'extract')
    shutil.copyfile(image,data);shutil.copyfile(template,tag)
    plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    run([str(OUT/'h3-api-probe/ApplyH3BitmapPlan.exe'),str(plan_path)],'settings')
    run([str(KIT/'tool.exe'),'bitmap_single',str(Path(target).with_suffix('.tif'))],'compile',KIT)
else:
    assert json.loads(plan_path.read_text(encoding='utf-8'))==plan and sha(image)==sha(data)
xml=OUT/'h3-light-gel.xml';run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(xml)],'read',KIT)
root=ET.fromstring(xml.read_text(encoding='utf-8',errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
b=root.find("block[@name='bitmaps']/element");fields={f.get('name'):f.get('value') for f in b.findall('field')}
assert (fields['width'],fields['height'],fields['mipmap count'],fields['curve'])==('512','128','9','linear'),fields
pixels=OUT/'light-gel-pixels';pixels.mkdir(exist_ok=True)
run([str(KIT/'tool.exe'),'export-bitmap-tga',target.rsplit('.',1)[0],str(pixels)+os.sep],'pixels',KIT)
sys.path.insert(0,str(OUT/'python-packages'))
from PIL import Image,ImageChops,ImageStat
files=list(pixels.glob('ca_bcreek_forerunner_lightgel_00_*.tga'));assert len(files)==1
a=Image.open(image).convert('RGBA');b=Image.open(files[0]).convert('RGBA');assert a.size==b.size==(512,128)
errors=ImageStat.Stat(ImageChops.difference(a,b)).mean
assert max(errors)==0,errors
assert sha(template)==before and sha(REACH/'tags'/source['source'])==source['sha256']
report=dict(source=source['source'],source_sha256=source['sha256'],image=str(image),image_sha256=sha(image),target=target,target_sha256=sha(tag),
    dimensions=[512,128],mipmaps=9,curve=fields['curve'],native_format=fields['format'],mean_RGBA_error=errors,
    limitation='Decoded source texture preserved; actual light projection remains for MCC review.')
(OUT/'h3-light-gel-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('LIGHT_GEL_VERIFIED',json.dumps(report),flush=True)
