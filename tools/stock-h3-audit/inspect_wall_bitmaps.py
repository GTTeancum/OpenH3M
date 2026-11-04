"""Read original Reach bitmap settings through official ManagedBlam; never save."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    os.environ[key]=str(OUT/relative)
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie

paths={
    'base_map':r'levels\dlc\cex_beaver_creek\bitmaps\ca_bcreek_bb_wall_diff.bitmap',
    'detail_map':r'levels\dlc\cex_ff_halo\bitmaps\ca_halo_for_metal_scratch_detail.bitmap',
    'bump_map':r'levels\dlc\cex_beaver_creek\bitmaps\ca_bcreek_bb_wall_bump.bitmap',
    'environment_map':r'levels\dlc\cex_beaver_creek\bitmaps\ca_bcreek_fore_cubemap.bitmap',
}
parser=argparse.ArgumentParser()
parser.add_argument('--family',action='store_true')
args=parser.parse_args()
if args.family:
    paths={p:p for p in json.loads((OUT/'wall-family-candidates.json').read_text())['images']}
def value(field):
    return str(field.Value) if hasattr(field,'Value') else str(field.GetStringData())
callback=Bungie.ManagedBlamCrashCallback(lambda info:None)
parameters=Bungie.ManagedBlamStartupParameters()
parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
report=[]
try:
    for name,path in paths.items():
        before=hashlib.sha256((KIT/'tags'/path).read_bytes()).hexdigest()
        tag=Bungie.Tags.TagFile()
        try:
            tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(*path.rsplit('.',1)))
            settings={str(f.DisplayName):value(f) for f in tag.Fields if str(f.DisplayName) in ['Usage','curve mode','force bitmap format']}
            bitmaps=[{str(f.DisplayName):value(f) for f in e.Fields if str(f.DisplayName) in ['width','height','type','format','curve']}
                     for e in tag.SelectField('Block:bitmaps').Elements]
            overrides=[{str(f.DisplayName):value(f) for f in e.Fields if hasattr(f,'Value') or hasattr(f,'GetStringData')}
                       for e in tag.SelectField('Block:usage override').Elements]
            report.append(dict(input=name,tag=path,fields=settings,bitmaps=bitmaps,overrides=overrides,sha256=before))
        finally:tag.Dispose()
        assert hashlib.sha256((KIT/'tags'/path).read_bytes()).hexdigest()==before
finally:Bungie.ManagedBlamSystem.Stop()
destination=OUT/'wall-family-bitmap-settings.json' if args.family else OUT/'wall-detail-trial/source-bitmap-settings.json'
destination.write_text(json.dumps(report,indent=2)+'\n')
if args.family:
    from collections import Counter
    print('SOURCE_BITMAPS',len(report),'CURVES',dict(Counter(r['bitmaps'][0]['curve'] for r in report)))
else:
    for r in report:print(r['input'],r['bitmaps'],r['overrides'])
