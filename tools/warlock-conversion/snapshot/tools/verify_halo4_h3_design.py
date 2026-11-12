"""Compile through official H3 Tool and verify its XML soft-ceiling output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h3ek'
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

authored = json.loads((OUT / 'haven-h3-design-authoring.json').read_text())
source = json.loads((OUT / 'haven-source-design.json').read_text())
source_file = ROOT / 'work/editing-kits/h4ek/tags' / source['source']
assert sha(source_file) == source['source_sha256'] == authored['source_design_sha256']
assert sha(authored['scene']) == authored['scene_sha256']
assert sha(authored['ass']) == authored['ass_sha256']
tool_hash = sha(KIT / 'tool.exe')
assert tool_hash == sha(Path('D:/SteamLibrary/steamapps/common/H3EK/tool.exe'))
env = os.environ.copy()
for key, suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    directory = OUT / 'h3-authoring' / suffix
    directory.mkdir(parents=True, exist_ok=True)
    env[key] = str(directory)

def tool(arguments, name):
    log = OUT / 'h3-authoring' / name
    with log.open('wb') as stream:
        run = subprocess.run([str(KIT / 'tool.exe'), *arguments], cwd=KIT, env=env,
            stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    text = log.read_text(errors='replace')
    assert run.returncode == 0 and '-ERROR-' not in text and 'FATAL' not in text, text
    return text

log = tool(['structure-design', str(Path(authored['ass']).relative_to(KIT / 'data'))], 'design-import.log')
assert '=== finished import' in log, log
tag = KIT / 'tags/levels/custom/haven_h4/haven.structure_design'
tag_hash = sha(tag)
xml = OUT / 'h3-authoring/haven-design-native.xml'
tool(['export-tag-to-xml', str(tag), str(xml)], 'design-native-xml.log')
assert sha(tag) == tag_hash
root = ET.parse(xml).getroot()
assert root.attrib['group'] == 'structure_design'
def block(element, name):
    return element.find('./block[@name="' + name + '"]')
def field(element, name):
    return element.find('./field[@name="' + name + '"]').attrib['value']
def vector(element, name):
    return tuple(float(v) for v in field(element, name).split(','))
def error(a,b):
    return max(abs(x-y) for x,y in zip(a,b))
ceilings = block(root, 'soft ceilings block')
assert len(ceilings) == 1
ceiling = ceilings[0]
assert field(ceiling, 'name') == 'ceiling1' and field(ceiling, 'type') == 'acceleration'
remaining = source['blocks']['soft ceilings block'][0]['soft ceiling triangles'].copy()
triangles = block(ceiling, 'soft ceiling triangles')
assert len(triangles) == len(remaining) == 60
maximum_vertex_error = maximum_plane_error = 0.0
tolerance = 0.00006  # Tool XML's six-significant-digit presentation, not bit equality.
for triangle in triangles:
    points = [vector(triangle, key) for key in ('vertex0','vertex1','vertex2')]
    def triangle_error(candidate):
        return max(error(point,candidate[key]) for point,key in zip(points,('vertex0','vertex1','vertex2')))
    match = min(remaining, key=triangle_error)
    vertex_error = triangle_error(match)
    plane_error = error(vector(triangle,'plane'), match['plane'])
    assert vertex_error < tolerance and plane_error < tolerance, (vertex_error,plane_error)
    maximum_vertex_error = max(maximum_vertex_error, vertex_error)
    maximum_plane_error = max(maximum_plane_error, plane_error)
    remaining.remove(match)
assert not remaining
mopps = block(root, 'soft ceiling mopp code block')
mopp_bytes = sum(len(block(e,'mopp data block ')) for e in mopps)
assert len(mopps) and mopp_bytes
assert not list(block(root,'water instances block'))
assert sha(source_file) == source['source_sha256']
report = dict(status='verified', source_design_sha256=source['source_sha256'],
    ass_sha256=authored['ass_sha256'], tool_sha256=tool_hash,
    native_tag=str(tag), native_tag_sha256=tag_hash, xml_sha256=sha(xml),
    soft_ceiling_name='ceiling1', type='acceleration', triangles=60,
    all_oriented_triangles_match=True, collision_mopp_bytes=mopp_bytes,
    maximum_vertex_error_world_units=maximum_vertex_error,
    maximum_plane_error=maximum_plane_error, xml_tolerance=tolerance,
    source_tag_unchanged=True,
    limitation='Design geometry and generated collision data only. Full BSP, scenario linkage, appearance and game behavior remain unverified.')
(OUT / 'haven-h3-design-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('H3_DESIGN_VERIFIED', json.dumps(report), flush=True)
