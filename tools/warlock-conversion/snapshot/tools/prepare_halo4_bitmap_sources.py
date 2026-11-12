"""Prepare H4 images with existing Foundry extraction and official tag metadata.

Separate project data root preserves all preview images. No pixel edits or
custom bitmap decoder. Arrays/volumes remain explicit pending inputs.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT,OUT,KIT,setup,sha
scene=setup()
destination=OUT/'bitmap-sources'
destination.mkdir(exist_ok=True)
for project in bpy.context.preferences.addons['io_scene_foundry'].preferences.projects:
    if project.name==scene.nwo.scene_project:
        project.data_directory=str(destination)
from io_scene_foundry import utils
assert Path(utils.get_data_path())==destination
from io_scene_foundry.managed_blam import mb_init
from io_scene_foundry.managed_blam.bitmap import BitmapTag
mb_init()
from Corinth.Tags import TagPath
audit=json.loads((OUT/'haven-material-input-audit.json').read_text())
refs=defaultdict(list)
for material,row in audit['materials'].items():
    for name,param in row['parameters'].items():
        path=param['effective_static']
        if param['type']=='bitmap' and isinstance(path,str) and path.endswith('.bitmap'):
            refs[path.replace('\\','/')].append(dict(material=material,parameter=name,authored=param['authored']))
report_path=OUT/'haven-bitmap-sources.json'
assert not report_path.exists(),'Preserve earlier evidence before rerunning'
report=dict(method='Unmodified Foundry 1.9.19 BitmapTag.save_to_tiff and official Corinth metadata',
    status='running',source_audit_sha256=sha(OUT/'haven-material-input-audit.json'),bitmaps=[],
    limitation='Recognized effective bitmap inputs; source shader feature usage, H3 import, stock reuse and appearance require verification.')
def field(element,selector):
    f=element.SelectField(selector)
    value=int(f.Value) if hasattr(f,'Value') else int(f.Data)
    result=dict(value=value)
    if hasattr(f,'Items'):
        result['name']=next(str(i.EnumName) for i in f.Items if int(i.EnumIndex)==value)
    return result
for relative,users in sorted(refs.items()):
    source=KIT/'tags'/relative
    row=dict(source=relative,users=users,images=[])
    if not source.is_file():
        row['status']='missing_source_tag';report['bitmaps'].append(row);continue
    before=sha(source);row['source_sha256']=before
    try:
        with BitmapTag(path=TagPath.FromPathAndExtension(*relative.rsplit('.',1)),tag_must_exist=True) as bitmap:
            row['usage']=field(bitmap.tag,'LongEnum:Usage')
            row['frames']=[{name:field(element,selector) for name,selector in
                [('width','ShortInteger:width'),('height','ShortInteger:height'),('type','CharEnum:type'),
                 ('format','ShortEnum:format'),('curve','CharEnum:curve'),('mipmap_count','CharInteger:mipmap count')]}
                for element in bitmap.block_bitmaps.Elements]
            if len(row['frames'])!=1 or row['frames'][0]['type']['value'] not in (0,2):
                row['status']='pending_non_single_2d_or_cube'
            else:
                normal=bitmap.used_as_normal_map()
                row.update(normal_map=normal,normal_type=str(bitmap.normal_type()),gamma=bitmap.get_gamma_value(),
                    blue_channel_fix_argument=normal,
                    extraction_note='Upstream extractor handles decoding; normal inputs bypass its color-space conversion. Preserve this distinction in H3 import.')
                result=Path(bitmap.save_to_tiff(blue_channel_fix=normal))
                assert result.is_relative_to(destination) and result.is_file()
                expected=(destination/relative).with_suffix('.tiff')
                paths={result,expected}
                for image in sorted(paths):
                    assert image.is_file(),image
                    row['images'].append(dict(path=str(image.relative_to(ROOT)),sha256=sha(image),bytes=image.stat().st_size))
                row['status']='extracted'
    except Exception as exc:
        row.update(status='extraction_error',error=str(exc))
    assert sha(source)==before,relative
    row['source_unchanged']=True
    report['bitmaps'].append(row)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('H4_BITMAP_SOURCE',relative,row['status'],row.get('error',''),flush=True)
report['status']='inventory_finished'
report['counts']=dict(Counter(r['status'] for r in report['bitmaps']))
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('H4_BITMAP_SOURCE_RESULT',json.dumps(report['counts']),flush=True)
