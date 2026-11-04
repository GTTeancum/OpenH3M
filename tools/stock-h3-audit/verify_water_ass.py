"""Read the full native ASS export and verify each river triangle's four UVs."""
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.file_ass.process_file import process_file

def read(name):
    return json.loads((OUT / name).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

export = read('h3-bound-ass-inspection-report.json')
bindings = read('h3-material-bindings.json')
saved = read('water-material-binding-verification.json')
channels = read('water-channel-authoring.json')
assert export['source_sha256'] == saved['scene_sha256'] == bindings['scene_sha256'] == sha(bindings['scene'])
assert bindings['source_sha256'] == channels['scene_sha256'] == sha(channels['scene'])
assert sha(export['ass']) == export['ass_sha256']
asset = process_file(export['ass'])
rows = []
for surface in saved['surfaces']:
    matches = [i for i in asset.instances if i.name == surface['object']]
    assert len(matches) == 1, surface
    obj = asset.objects[matches[0].object_index]
    original = next(m for m in channels['meshes'] if m['mesh'] == surface['mesh'])
    expected = [tuple(main + water) for main, water in zip(original['original_main_uv'], original['original_water_uv'])]
    assert len(obj.triangles) == surface['faces']
    checked = []
    for triangle in obj.triangles:
        assert asset.materials[triangle.material_index].name == surface['export_name']
        for index in (triangle.v0, triangle.v1, triangle.v2):
            uv = obj.vertices[index].uv_set
            assert len(uv) == 4 and all(len(v) == 3 and v[2] == 0 for v in uv), uv
            assert uv[1] == [1000, 0, 0] and uv[2] == [0, 0, 0], uv
            pair = tuple(uv[0][:2] + uv[3][:2])
            assert any(max(abs(a-b) for a,b in zip(pair, target)) < 1e-7 for target in expected), pair
            checked.append(pair)
    assert len(checked) == len(expected)
    # Preserve per-corner multiplicity as well as pair membership.
    remaining = checked.copy()
    for target in expected:
        match = next((i for i, pair in enumerate(remaining) if max(abs(a-b) for a,b in zip(pair, target)) < 1e-7), None)
        assert match is not None, target
        remaining.pop(match)
    assert not remaining
    rows.append(dict(object=surface['object'], faces=len(obj.triangles), corners=len(checked), original_uv_pairs_preserved=True))
assert len(rows) == 3 and sum(r['faces'] for r in rows) == 42
assert sha(export['ass']) == export['ass_sha256']
(OUT / 'water-ass-verification.json').write_text(json.dumps(dict(
    scene_sha256=bindings['scene_sha256'], ass_sha256=export['ass_sha256'], surfaces=rows,
    limitation='Actual full-map ASS coordinates verified through the unmodified reader. Full-map Tool import and MCC rendering remain unverified.'), indent=2) + '\n')
print('WATER_ASS_VERIFIED: 3 surfaces, 42 triangles, 126 corners; four UV channels and original UV pairs preserved.', flush=True)
