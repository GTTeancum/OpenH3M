"""Read native Reach option defaults without saving tags or decoding binaries."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:os.environ[key]=str(OUT/relative)
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie

paths=sorted({c['tag'] for s in json.loads((OUT/'reach-effective-shader-options.json').read_text()).values()
              for c in s.get('categories',[]) if c['tag']})
callback=Bungie.ManagedBlamCrashCallback(lambda _:None)
parameters=Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
result=[]
try:
    for path in paths:
        original=KIT/'tags'/path
        before=hashlib.sha256(original.read_bytes()).hexdigest()
        tag=Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*path.rsplit('.',1)))
            rows=[]
            for element in tag.SelectField('Block:parameters').Elements:
                row={}
                for field in element.Fields:
                    name=str(field.DisplayName)
                    if not (name.startswith('default ') or name in ['parameter name','parameter type','source extern']):continue
                    if isinstance(field,Bungie.Tags.TagFieldReference):
                        row[name]=str(field.Path.RelativePathWithExtension) if field.Path else None
                    elif isinstance(field,Bungie.Tags.TagFieldEnum):
                        row[name]=str(field.Items[int(field.Value)].EnumName)
                    elif isinstance(field,Bungie.Tags.TagFieldElementStringID):
                        row[name]=str(field.GetStringData())
                    elif hasattr(field,'Data'):
                        data=field.Data
                        row[name]=list(data) if hasattr(data,'__iter__') else data
                    elif hasattr(field,'GetStringData'):
                        row[name]=str(field.GetStringData())
                rows.append(row)
            result.append(dict(path=path,sha256=before,parameters=rows))
        finally:tag.Dispose()
        assert hashlib.sha256(original.read_bytes()).hexdigest()==before,path
finally:Bungie.ManagedBlamSystem.Stop()
(OUT/'reach-option-defaults.json').write_text(json.dumps(result,indent=2)+'\n')
print('REACH_OPTION_DEFAULTS_READ',len(result),flush=True)
