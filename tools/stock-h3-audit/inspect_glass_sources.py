"""Read original glass channel controls through unmodified Foundry/ManagedBlam."""
import base64
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name='Original glass control inspection'
project.project_path=str(KIT)
project.tags_directory=str(KIT/'tags')
project.data_directory=str(KIT/'data')
project.corinth=False
bpy.context.scene.nwo.scene_project=project.name
from io_scene_foundry.managed_blam.shader import ShaderTag
from io_scene_foundry.managed_blam import mb_init
mb_init()
families=json.loads((ROOT/'tools/stock-h3-audit/material_families.json').read_text())
rows=[]
for family in ['glass_interior','glass_exterior']:
    for path in families[family]['sources']:
        absolute=KIT/'tags'/path
        before=hashlib.sha256(absolute.read_bytes()).hexdigest()
        parameters={}
        with ShaderTag(path=path,tag_must_exist=True) as shader:
            for element in shader.block_parameters.Elements:
                name=element.SelectField('parameter name').GetStringData()
                if name not in ['base_map','opacity_texture','bump_map','environment_map','opacity_fresnel_coefficient']:continue
                bitmap=element.SelectField('bitmap').Path
                functions=[]
                for animation in element.SelectField(shader.function_parameters).Elements:
                    editor=animation.SelectField(shader.animated_function).Value
                    functions.append(dict(type=int(animation.SelectField('type').Value),
                        input=animation.SelectField('input name').GetStringData(),
                        range=animation.SelectField('range name').GetStringData(),
                        period=float(animation.SelectField('time period').Data),
                        master_type=editor.MasterType.value__,is_ranged=editor.IsRanged,
                        clamp_min=float(editor.ClampRangeMin),
                        data_base64=base64.b64encode(bytes(animation.SelectField('Struct:function/Data:data').GetData())).decode('ascii')))
                parameters[name]=dict(bitmap=None if bitmap is None else bitmap.RelativePathWithExtension,functions=functions)
        for name,expected in [('base_map',1),('opacity_texture',2),('opacity_fresnel_coefficient',1 if family=='glass_exterior' else 0)]:
            fs=parameters[name]['functions']
            assert len(fs)==1 and fs[0]['type']==(0 if name=='opacity_fresnel_coefficient' else 2)
            assert fs[0]['master_type']==0 and not fs[0]['is_ranged'] and fs[0]['input']==fs[0]['range']==''
            assert fs[0]['clamp_min']==expected,(path,name,fs)
        assert hashlib.sha256(absolute.read_bytes()).hexdigest()==before
        rows.append(dict(source=path,source_sha256=before,family=family,parameters=parameters))
        print('ORIGINAL_GLASS_CONTROLS_CHECKED',path,flush=True)
(OUT/'glass-native-source-controls.json').write_text(json.dumps(rows,indent=2)+'\n')
