"""Export a diagnostic from the author's example without modifying its file."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
source=OUT/'upstream/c20-water-example/water-visual.blend'
assert Path(bpy.data.filepath)==source
before=hashlib.sha256(source.read_bytes()).hexdigest()
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
from io_scene_halo.file_ass.process_file import process_file
four='--four-channels' in sys.argv
if four:
    mesh=bpy.data.objects['water_plane'].data
    assert len(mesh.uv_layers)==1
    original=[tuple(v.uv) for v in mesh.uv_layers[0].data]
    local=mesh.uv_layers.new(name='UVMap1',do_init=False)
    velocity=mesh.uv_layers.new(name='UVMap2',do_init=False)
    shape=mesh.uv_layers.new(name='UVMap3',do_init=False)
    for i,uv in enumerate(original):
        local.data[i].uv=(1000,0)  # Tool scales this distance by .01: stock Longshore native X=10.
        velocity.data[i].uv=(0,0)  # Native Tool default established by one-channel import.
        shape.data[i].uv=uv
name='water_four_channels' if four else 'water_workflow'
dest=ROOT/'work/editing-kits/h3ek/data/levels/custom/bc_water_workflow_probe/structure'/(name+'.ass')
dest.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(dest),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),False,1.0,
    lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
asset=process_file(str(dest))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report=dict(source=str(source),sha256=before,ass=str(dest),
    ass_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),materials=[m.name for m in asset.materials],
    instances=[i.name for i in asset.instances],
    authored_water_uvs=[[list(v.uv) for v in layer.data] for layer in bpy.data.objects['water_plane'].data.uv_layers],
    four_channel_probe=four,
    limitation='Diagnostic using the author-provided example; no saved example changes, Battle Canyon replacement geometry or game acceptance.')
(OUT/('water-four-channel-example-export.json' if four else 'water-example-export.json')).write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE_WATER_EXAMPLE_EXPORT',report,flush=True)
