"""Correlate recorded Blender wiring with unmodified official shader source."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT/'work/halo4-to-h3/haven'
DATA = ROOT/'work/editing-kits/h4ek/data/shaders/material_shaders'

def read(name):
    return json.loads((OUT/name).read_text())

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

audit = read('haven-sky-color-audit.json')
inputs = read('haven-material-input-audit.json')['materials']
functions = read('haven-material-function-audit.json')['materials']
assert audit['source_blend_unchanged']
tree = audit['node_trees']['group:srf_constant_vertalpha']
nodes = {n['name']:n for n in tree['nodes']}
assert nodes['Mix']['settings']['data_type'] == 'FLOAT'
assert nodes['Mix']['settings']['blend_type'] == 'MIX'
assert nodes['Mix.014']['settings']['blend_type'] == 'ADD'
alpha_links = [link for link in tree['links'] if link['target_node'] == 'Group'
               and link['target_socket'] == 'alpha']
assert len(alpha_links) == 1 and alpha_links[0]['source_node'] == 'Mix.014'
assert not any(link['source_node'] == 'Mix' for link in tree['links'])
alpha_reader = audit['node_trees']['group:vertex alpha output']
assert alpha_reader['links'][0]['source_socket'] == 'Alpha'

source_evidence = []
for relative, needles in {
    'materials/srf_constant_vertalpha.fx':['#define VERTEX_ALPHA'],
    'materials/special/srf_constant_core.fxh':[
        'out_color.a = lerp(shader_data.common.vertexColor.a,',
        'shader_data.common.vertexColor.a * out_color.a,',
        'vertex_alpha_multiplicative);'],
    'include/deform.fxh':[
        'float4(vertex.vertexColor.r, vertex.vertexColor.g, vertex.vertexColor.b, vertex.vertexColor.r)',
        'float4 vertexColor = float4(1,1,1,vertex.position.w);'],
}.items():
    path = DATA/relative
    lines = path.read_text().splitlines()
    evidence = []
    for needle in needles:
        matches = [i+1 for i, line in enumerate(lines) if needle in line]
        assert len(matches) == 1, (relative, needle, matches)
        evidence.append(dict(line=matches[0], code=lines[matches[0]-1].strip()))
    source_evidence.append(dict(path=str(path.relative_to(ROOT)),
        sha256=sha(path), statements=evidence))

materials = []
for name in ('wa_bigclouds_bottom', 'wa_topclouds_fade'):
    row = next(r for r in audit['materials'] if r['material'] == name)
    source = row['source']
    static = inputs[source]['parameters']['vertex_alpha_multiplicative']['effective_static']
    records = functions[source].get('vertex_alpha_multiplicative', [])
    assert static == 0
    for record in records:
        assert record['master_type'] == 'Basic' and not record['is_ranged']
        assert record['clamp_min'] == 0
    assert row['color']['channels'][0]['min'] == 0
    assert row['color']['channels'][0]['max'] == 1
    assert row['color']['nonidentity_alpha'] == 0
    materials.append(dict(source=source, polygons=row['polygons'], color=row['color'],
        effective_vertex_alpha_multiplicative=0))

report = dict(status='preview_opacity_mismatch_confirmed', materials=materials,
    source_evidence=source_evidence, observed_alpha_connection=alpha_links[0],
    vertex_fade_result_disconnected=True, imported_color_alpha_is_one=True,
    imported_color_red_contains_fade=True,
    official_formula='lerp(vertex_alpha, vertex_alpha * texture_alpha, multiplicative); zero selects vertex_alpha',
    conclusions=[
        'The unmodified imported node graph does not apply the official vertex-alpha formula to opacity.',
        'The existing vertex alpha output group reads padded Blender alpha, not the varying source red channel used by the official authoring-preview shader.',
        'The source preview cannot establish correct cloud fading; material authoring must preserve this semantic explicitly.',
    ], limitations=[
        'No corrected render or native H3 sky shader has been evaluated.',
        'The visible seam is not proven to have only this cause.',
        'The native H4 packed position.w value has not yet been compared to the authored red field.',
        'ASS/JMS RGB serialization does not itself establish H3 shader consumption of this fade.',
    ])
(OUT/'haven-sky-opacity-evidence.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status=report['status'], affected_materials=len(materials),
    affected_polygons=sum(r['polygons'] for r in materials),
    source_blend_unchanged=True, h3_shader_mapping_verified=False)))
