"""Read original prop dependencies with the official Reach tag API/Tool."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/hrek'
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
callback=Bungie.ManagedBlamCrashCallback(lambda info:None)
parameters=Bungie.ManagedBlamStartupParameters();parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
report={}
try:
    for name in ('frunner_wheel','cex_health_cabinet','ff_redbase_rocks02','health_station'):
        original=json.loads((OUT/f'original-prop-{name}.json').read_text())
        source=Path(original['source']);relative=str(source.relative_to(KIT/'tags'))
        tag=Bungie.Tags.TagFile();tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(relative.rsplit('.',1)[0],source.suffix[1:]))
        try:
            object_struct=tag.Fields[0]
            if object_struct.DisplayName!='object':object_struct=object_struct.Elements[0].Fields[0]
            model=tag.SelectField(str(object_struct.FieldPath)+'/Reference:model').Path.RelativePathWithExtension
        finally:tag.Dispose()
        tag=Bungie.Tags.TagFile();tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(model.rsplit('.',1)[0],'model'))
        try:
            references={}
            for field in ('render model','collision model','animation','physics_model'):
                ref=tag.SelectField(field).Path
                references[field]=None if ref is None else ref.RelativePathWithExtension
        finally:tag.Dispose()
        report[name]=dict(object=relative,model=model,references=references,exports={})
        for label,path in [('object',relative),('model',model),('physics',references['physics_model'])]:
            if path is None:continue
            file=KIT/'tags'/path;before=hashlib.sha256(file.read_bytes()).hexdigest()
            xml=OUT/f'original-prop-{name}-{label}.xml'
            with (OUT/f'original-prop-{name}-{label}-read.log').open('wb') as stream:
                result=subprocess.run([str(KIT/'tool_fast.exe'),'export-tag-to-xml',str(file),str(xml)],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=60)
            assert result.returncode==0 and xml.stat().st_size>100
            assert hashlib.sha256(file.read_bytes()).hexdigest()==before
            report[name]['exports'][label]=dict(path=str(xml),source_sha256=before)
        print('SOURCE_PROP_DEPENDENCIES',name,references,flush=True)
finally:Bungie.ManagedBlamSystem.Stop()
(OUT/'original-prop-native-dependencies.json').write_text(json.dumps(report,indent=2)+'\n')
