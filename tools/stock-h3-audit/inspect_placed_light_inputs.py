"""Read source light functions and projected-texture metadata through Reach's API."""
import base64,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/hrek'
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:os.environ[key]=str(OUT/path)
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
callback=Bungie.ManagedBlamCrashCallback(lambda info:None)
parameters=Bungie.ManagedBlamStartupParameters();parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
paths=json.loads((OUT/'original-placed-lights.json').read_text(encoding='utf-8'));result=[]
gel=r'levels\dlc\cex_beaver_creek\bitmaps\ca_bcreek_forerunner_lightgel.bitmap'
try:
    for path in [p for p in paths if p.endswith('.light')]:
        before=sha(KIT/'tags'/path);t=Bungie.Tags.TagFile();t.Load(Bungie.Tags.TagPath.FromPathAndExtension(*path.rsplit('.',1)))
        functions={}
        try:
            for name in ('color','intensity'):
                e=t.SelectField('Struct:'+name).Elements[0];editor=e.SelectField('Custom:Mapping').Value
                colors=[]
                for i in range(editor.ColorCount):
                    color=editor.GetColor(i)
                    if int(color.ColorMode.value__)==1:color=color.ToRgb()
                    colors.append([float(color.Red),float(color.Green),float(color.Blue),float(color.Alpha)])
                functions[name]=dict(data_base64=base64.b64encode(bytes(e.SelectField('Struct:Mapping/Data:data').GetData())).decode('ascii'),
                    input=str(e.SelectField('Input Variable').GetStringData()),range=str(e.SelectField('Range Variable').GetStringData()),
                    output_modifier=int(e.SelectField('Output Modifier').Value),output_input=str(e.SelectField('Output Modifier Input').GetStringData()),
                    master_type=int(editor.MasterType.value__),color_graph_type=int(editor.ColorGraphType.value__),
                    is_ranged=bool(editor.IsRanged),clamp_min=float(editor.ClampRangeMin),clamp_max=float(editor.ClampRangeMax),colors=colors)
            result.append(dict(source=path,sha256=before,functions=functions))
        finally:t.Dispose()
        assert sha(KIT/'tags'/path)==before
    before=sha(KIT/'tags'/gel);t=Bungie.Tags.TagFile();t.Load(Bungie.Tags.TagPath.FromPathAndExtension(*gel.rsplit('.',1)))
    try:
        metadata=[{str(f.DisplayName):str(f.Value) if hasattr(f,'Value') else str(f.GetStringData()) for f in e.Fields if str(f.DisplayName) in ('width','height','format','curve','mipmap count')} for e in t.SelectField('bitmaps').Elements]
    finally:t.Dispose()
    assert sha(KIT/'tags'/gel)==before
finally:Bungie.ManagedBlamSystem.Stop()
report=dict(lights=result,gel=dict(source=gel,sha256=before,bitmaps=metadata))
(OUT/'original-placed-light-inputs.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('SOURCE_LIGHT_INPUTS',json.dumps(report),flush=True)
