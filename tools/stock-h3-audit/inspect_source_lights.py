"""Read the three placed Reach light fixtures with the official source tools."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/hrek'
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:os.environ[key]=str(OUT/path)
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie
callback=Bungie.ManagedBlamCrashCallback(lambda info:None);parameters=Bungie.ManagedBlamStartupParameters();parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
palette=json.loads((OUT/'original-gameplay-palettes.json').read_text())['palettes']['scenery palette']
paths=[p for p in palette if Path(p).stem in ('ca_bcreek_omni_1','ca_bcreek_spot_5','ca_bcreek_spot_7')];assert len(paths)==3
def refs(fields):
    result=[]
    for field in fields:
        if isinstance(field,Bungie.Tags.TagFieldReference) and field.Path:result.append(dict(field=str(field.FieldPath),tag=str(field.Path.RelativePathWithExtension)))
        elif isinstance(field,(Bungie.Tags.TagFieldStruct,Bungie.Tags.TagFieldBlock)):
            for e in field.Elements:result.extend(refs(e.Fields))
    return result
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
report={}
try:
    for path in paths:
        tag=Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*path.rsplit('.',1)))
            references=refs(tag.Fields)
            report[path]=dict(references=references,sha256=hashlib.sha256((KIT/'tags'/path).read_bytes()).hexdigest())
            paths.extend(r['tag'] for r in references if r['tag'].endswith('.light') and r['tag'] not in paths)
        finally:tag.Dispose()
finally:Bungie.ManagedBlamSystem.Stop()
for path,row in report.items():
    source=KIT/'tags'/path;xml=OUT/('original-placed-'+Path(path).name+'.xml')
    with (OUT/('original-placed-'+Path(path).name+'-export.log')).open('wb') as log:
        run=subprocess.run([str(KIT/'tool_fast.exe'),'export-tag-to-xml',str(source),str(xml)],cwd=KIT,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    assert run.returncode==0 and xml.stat().st_size>1000
    assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256'];row['xml']=str(xml)
(OUT/'original-placed-lights.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_PLACED_LIGHTS',len(report),'source tags read, unchanged',flush=True)
