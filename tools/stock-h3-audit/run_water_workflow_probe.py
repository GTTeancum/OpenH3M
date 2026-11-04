"""Compile the exported c20 water example with official Tool; read native fields."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
export=json.loads((OUT/'water-four-channel-example-export.json').read_text())
ass=Path(export['ass'])
assert ass.is_relative_to(KIT/'data/levels/custom/bc_water_workflow_probe/structure')
assert hashlib.sha256(ass.read_bytes()).hexdigest()==export['ass_sha256']
log=OUT/'water-four-channel-structure.log'
with log.open('wb') as stream:
    result=subprocess.run([str(KIT/'tool.exe'),'structure',str(ass.relative_to(KIT/'data'))],
        cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
output=log.read_text(errors='replace')
assert result.returncode==0 and '-ERROR-' not in output and '=== imported structure' in output,output
report=OUT/'water-four-channel-native-geometry.json'
result=subprocess.run([str(OUT/'h3-api-probe/InspectH3WaterGeometry.exe'),str(KIT),str(report),
    r'levels\custom\bc_water_workflow_probe\water_four_channels'],cwd=KIT,env=env,
    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
(OUT/'water-four-channel-native-read.log').write_bytes(result.stdout)
assert result.returncode==0,result.stdout
native=json.loads(report.read_text())
vertices=[v for m in native['meshes'] for v in m['water']['raw water vertices']]
assert len(vertices)==4
stock=json.loads((OUT/'h3-docks-water-geometry.json').read_text())
assert hashlib.sha256(Path(stock['source']).read_bytes()).hexdigest()==stock['sha256']
stock_info={tuple(v['local info']) for m in stock['meshes'] for v in m['water']['raw water vertices']}
assert stock_info=={(10,0,0)}
assert all(max(abs(a-b) for a,b in zip(v['local info'],(10,0,0)))<1e-6 for v in vertices)
assert all(v['water velocity']==[0,0,0] and v['base texcoord'][2]==0 for v in vertices)
assert {tuple(v['base texcoord'][:2]) for v in vertices}=={(0,0),(0,1),(1,0),(1,1)}
assert export['authored_water_uvs'][1]==[[1000,0]]*4
assert export['authored_water_uvs'][2]==[[0,0]]*4
assert hashlib.sha256(ass.read_bytes()).hexdigest()==export['ass_sha256']
(OUT/'water-channel-workflow-verification.json').write_text(json.dumps(dict(
    ass_sha256=export['ass_sha256'],bsp_sha256=native['sha256'],stock_sha256=stock['sha256'],
    authoring_local_info=[1000,0],native_local_info=[10,0,0],native_velocity=[0,0,0],
    shape_channel=3,native_w=0,vertices=len(vertices),
    limitation='Native coordinate mapping verified on the author-provided diagnostic. Battle Canyon geometry and rendered behavior still need validation.'),indent=2)+'\n')
print('NATIVE_WATER_CHANNEL_MAPPING_VERIFIED: four vertices, stock local info, neutral velocity, shape UVs.')
