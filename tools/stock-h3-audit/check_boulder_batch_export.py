"""Run existing saved/ASS fidelity checks around the unchanged full exporter."""
from pathlib import Path
import runpy
import sys

HERE=Path(__file__).resolve().parent
for helper in ('verify_boulder_collision_batch.py','verify_h3_lighting_metadata.py',
               'verify_world_collision_authoring.py','verify_water_bindings.py','export_h3_inspection.py'):
    runpy.run_path(str(HERE/helper),run_name='__main__')
sys.argv.append('--ass')
for helper in ('verify_h3_lighting_metadata.py','verify_water_ass.py','verify_world_collision_ass.py','verify_boulder_batch_ass.py'):
    runpy.run_path(str(HERE/helper),run_name='__main__')
