"""Reuse the existing H3 API/Tool bitmap workflow for isolated Haven inputs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'
DEST=OUT/'bitmap-import'
DEST.mkdir(exist_ok=True)
env=os.environ.copy()
for key,suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    env[key]=str(OUT/'h3-authoring'/suffix)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(exe,args,log):
    assert not log.exists(),log
    with log.open('wb') as stream:
        result=subprocess.run([str(exe),*map(str,args)],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
    text=log.read_text(errors='replace')
    assert result.returncode==0 and '-ERROR-' not in text and '-FATAL-' not in text,(log,text[-1500:])
inventory=json.loads((OUT/'haven-bitmap-sources.json').read_text())
all_rows={r['source']:r for r in inventory['bitmaps']}
normal=next(p for p,r in all_rows.items() if p.endswith('_normal.bitmap') and p.replace('_normal.bitmap','_diff.bitmap') in all_rows and r['frames'][0]['format']['name']=='dxn')
selected=[normal.replace('_normal.bitmap','_diff.bitmap'),normal]
all_mode='--all' in sys.argv
special_mode='--special' in sys.argv
cube_pilot='--cube-pilot' in sys.argv
cube_defaults='--cube-defaults' in sys.argv
assert sum((all_mode,special_mode,cube_pilot,cube_defaults))<=1
reused_defaults={'default_control.bitmap','default_diff.bitmap','default_spec.bitmap','default_normal.bitmap'}
if all_mode:
    selected=[p for p,r in all_rows.items() if r['frames'][0]['type']['value']==0
        and r['frames'][0]['format']['name']!='a2r10g10b10'
        and not (p.startswith('shaders/default_bitmaps/') and Path(p).name in reused_defaults)]
    assert len(selected)==66
if special_mode or cube_pilot or cube_defaults:
    selected=[p for p,r in all_rows.items() if r['frames'][0]['type']['value']==2 or r['frames'][0]['format']['name']=='a2r10g10b10']
    assert len(selected)==5
    if cube_pilot:selected=selected[:1]
    if cube_defaults:selected=[p for p in selected if all_rows[p]['frames'][0]['type']['value']==2]
report_path=DEST/('cube-defaults.json' if cube_defaults else 'special.json' if special_mode else 'cube-pilot.json' if cube_pilot else 'ordinary-2d.json' if all_mode else 'pilot.json');assert not report_path.exists()
report=dict(status='running',method='Existing official H3 API settings and Tool bitmap_single/export-bitmap-tga',images=[],
    limitation='Native import pilot; decoded pixel/channel and actual shading verification remain required.')
previous={r['source']:r for r in json.loads((DEST/'pilot.json').read_text())['images']} if all_mode else {}
if special_mode:
    prior=json.loads((DEST/'cube-pilot.json').read_text())
    assert prior['status']=='native_import_and_metadata_pass'
    previous={r['source']:r for r in prior['images']}
for index,source in enumerate(selected):
    if source in previous:
        old=previous[source]
        assert sha(KIT/'tags'/old['target'])==old['target_sha256']
        for item in old.get('exports',[dict(path=old.get('export'),sha256=old.get('export_sha256'))]):
            assert sha(ROOT/item['path'])==item['sha256']
        report['images'].append(old)
        continue
    row=all_rows[source];frame=row['frames'][0];assert row['status']=='extracted' and frame['type']['value'] in (0,2)
    cube=frame['type']['value']==2
    assert sha(KIT.parent/'h4ek/tags'/source)==row['source_sha256']
    image=ROOT/row['images'][0]['path'];assert sha(image)==row['images'][0]['sha256']
    if cube:
        crosses=json.loads((OUT/'haven-cube-cross-sources.json').read_text())
        cross=next(r for r in crosses['cubes'] if r['source']==source)
        assert cross['strip_sha256']==sha(image) and cross['exact_face_tiles']
        image=ROOT/cross['path'];assert sha(image)==cross['sha256']
    identifier=('h4_cube_native_' if cube_defaults else 'h4_cube_' if cube else 'h4_')+hashlib.sha256(source.encode()).hexdigest()[:12]
    relative=Path('levels/custom/haven_h4/bitmaps')/identifier
    data=(KIT/'data'/relative).with_suffix('.tif');data.parent.mkdir(parents=True,exist_ok=True)
    assert not data.exists() and not (KIT/'tags'/relative).with_suffix('.bitmap').exists()
    shutil.copyfile(image,data);assert sha(data)==sha(image)
    if cube:
        # Start from a stock native cube so the slicer is selected before Tool
        # encounters the source's six-face strip. The pixels are imported below.
        donor=KIT/'tags/shaders/default_bitmaps/bitmaps/default_dynamic_cube_map.bitmap'
        shutil.copyfile(donor,(KIT/'tags'/relative).with_suffix('.bitmap'))
    else:run(KIT/'tool.exe',['bitmap_single',str(relative.with_suffix('.tif'))],DEST/(identifier+'-initial.log'))
    normal_map=row['normal_map'];curve=frame['curve']['value']
    settings=dict(Path=str(relative.with_suffix('.bitmap')),Usage='Cube Map (Reflection Map)' if cube else 'ZBrush Bump Map (from Bump Map)' if normal_map else 'Diffuse Map',
        Format='Use Default (defined by usage)' if normal_map else
            {'dxt1':'DXT1','dxt5':'DXT5 (Compressed Color + Compressed 8-bit Alpha)','a8r8g8b8':'24-bit Color + 8-bit Alpha','a2r10g10b10':'24-bit Color + 8-bit Alpha'}[frame['format']['name']],
        LinearSource=not normal_map and curve==3,Curve='sRGB' if not normal_map and curve!=3 else None,
        SourceGamma=2.2,MaxMipmapLevel=frame['mipmap_count']['value']+1)
    if cube_defaults:
        # Reuse the existing Reach authoring workflow for legacy-color cubes:
        # native Cube Map usage, no explicit gamma override on extracted TIFFs.
        assert cube and curve==1
        settings.update(ClearOverride=True,Curve=None,SourceGamma=0,LinearSource=False)
    plan=DEST/(identifier+'-plan.json');plan.write_text(json.dumps(dict(Kit=str(KIT),Bitmaps=[settings]),indent=2)+'\n')
    run(OUT/'h3-api/ApplyHavenBitmapPlan.exe',[plan],DEST/(identifier+'-settings.log'))
    run(KIT/'tool.exe',['bitmap_single',str(relative.with_suffix('.tif'))],DEST/(identifier+'-import.log'))
    tag=(KIT/'tags'/relative).with_suffix('.bitmap');before=sha(tag)
    xml=DEST/(identifier+'.xml')
    run(KIT/'tool.exe',['export-tag-to-xml',tag,xml],DEST/(identifier+'-metadata.log'))
    root=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
    element=root.find("block[@name='bitmaps']/element");assert element is not None
    saved={f.get('name'):f.get('value') for f in element.findall('field')}
    if cube:assert saved['type']=='cube map',saved
    assert int(saved['width'])==frame['width']['value'] and int(saved['height'])==frame['height']['value']
    assert int(saved['mipmap count'])==frame['mipmap_count']['value'],saved
    pixels=DEST/(identifier+'-pixels');pixels.mkdir()
    run(KIT/'tool.exe',['export-bitmap-tga',str(relative),str(pixels)+os.sep],DEST/(identifier+'-pixels.log'))
    exports=sorted(pixels.glob('*.tga'));assert len(exports)==(6 if cube else 1) and sha(tag)==before,(source,exports)
    report['images'].append(dict(source=source,source_image=str(image.relative_to(ROOT)),source_image_sha256=sha(image),
        target=str(relative.with_suffix('.bitmap')),target_sha256=before,settings=settings,saved=saved,
        export=str(exports[0].relative_to(ROOT)),export_sha256=sha(exports[0]),normal_map=normal_map,
        exports=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in exports],cube_map=cube,
        precision_limitation='Source 10-bit RGB is represented by the released extractor as 8-bit RGBA; native rendering and quantization acceptance remain pending.' if frame['format']['name']=='a2r10g10b10' else None,
        original_normal_type=row['normal_type'],source_format=frame['format'],source_curve=frame['curve']))
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('H4_NATIVE_BITMAP_IMPORTED',source,saved['format'],saved['curve'],flush=True)
report['status']='native_import_and_metadata_pass'
report_path.write_text(json.dumps(report,indent=2)+'\n')
