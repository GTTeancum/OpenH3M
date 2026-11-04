"""Import the approved Blender-packed glass image with official H3 tools."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/h3ek'
DEST = OUT / 'glass-channel-preparation'
env = os.environ.copy()
for key, rel in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'), ('TEMP', 'temp'), ('TMP', 'temp')]:
    env[key] = str(OUT / rel)
sys.path.insert(0, str(OUT / 'python-packages'))
from PIL import Image, ImageChops
parser = argparse.ArgumentParser()
parser.add_argument('--verify-only', action='store_true', help='Inspect an already imported native bitmap without rewriting it')
args = parser.parse_args()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(label, command):
    result = subprocess.run(command, cwd=KIT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    (DEST / (label + '.log')).write_bytes(result.stdout)
    assert result.returncode == 0, (label, result.stdout.decode(errors='replace'))
    checked = result.stdout.lower()
    if label == 'native-pixels' and b'attempting to save directly' in checked:
        # Tool's uncompressed a8y8 direct-save path is valid only if the actual
        # exported file passes the complete pixel comparison below.
        checked = checked.replace(b'failed to decompress', b'direct-save fallback')
    assert not any(s in checked for s in [b'failed to', b"can't resolve", b'fatal error']), label

prepared = json.loads((DEST / 'report.json').read_text())
source = Path(prepared['output'])
assert sha(source) == prepared['output_sha256']
assert prepared['max_alpha_error'] == 0 and max(prepared['max_rgb_errors']) <= 1
for path, expected in prepared['source_hashes'].items():
    assert sha(path) == expected, path
donor = r'levels\dlc\warehouse\shaders\ware_glass_overhead_a.shader'
configuration = next(r for r in json.loads((OUT / 'stock-shader-configurations.json').read_text()) if r['path'] == donor)
assert sha(KIT / 'tags' / donor) == configuration['sha256']
template_name = next(p['bitmap'] for p in configuration['parameters'] if p['name'] == 'base_map')
assert template_name and template_name.endswith('.bitmap')
template = KIT / 'tags' / template_name
template_sha = sha(template)
relative = Path(r'levels\custom\battle_canyon_fresh\bitmaps\bc_glass_color_opacity.bitmap')
target = KIT / 'tags' / relative
data = (KIT / 'data' / relative).with_suffix('.tif')
assert target.resolve().is_relative_to((KIT / 'tags/levels/custom/battle_canyon_fresh').resolve())
if data.exists():
    assert sha(data) == sha(source), 'Existing working image changed; review before replacing'
else:
    assert not args.verify_only
    shutil.copyfile(source, data)
if not target.exists():
    assert not args.verify_only
    shutil.copyfile(template, target)
elif not args.verify_only:
    previous = json.loads((DEST / 'native-import-report.json').read_text())
    assert sha(target) == previous['target_sha256'], 'Existing native glass image changed'
plan = DEST / 'native-import-plan.json'
plan.write_text(json.dumps(dict(Kit=str(KIT), Bitmaps=[dict(Path=str(relative), Usage='Diffuse Map',
    Format='8-bit Monochrome + 8-bit Alpha', LinearSource=True, MaxMipmapLevel=10)]), indent=2) + '\n')
if not args.verify_only:
    run('native-settings', [str(OUT / 'h3-api-probe/ApplyH3BitmapPlan.exe'), str(plan)])
    run('native-import', [str(KIT / 'tool.exe'), 'bitmap_single', str(relative.with_suffix('.tif'))])
native_xml = DEST / 'native-bitmap.xml'
run('native-xml', [str(KIT / 'tool.exe'), 'export-tag-to-xml', str(target), str(native_xml)])
tree = ET.fromstring(native_xml.read_text(errors='replace').replace('<unavailable>', '&lt;unavailable&gt;'))
fields = {f.get('name'): f.get('value') for f in tree.find("block[@name='bitmaps']/element").findall('field')}
assert (fields['width'], fields['height'], fields['format'], fields['curve'], fields['mipmap count']) == ('512', '512', 'a8y8', 'linear', '9'), fields
pixels = DEST / 'native-pixels'
pixels.mkdir(exist_ok=True)
run('native-pixels', [str(KIT / 'tool.exe'), 'export-bitmap-tga', str(relative.with_suffix('')), str(pixels) + os.sep])
files = list(pixels.glob('bc_glass_color_opacity_00_*.tga'))
assert len(files) == 1 and files[0].stat().st_mtime_ns >= target.stat().st_mtime_ns
with Image.open(source) as image:
    original = image.convert('RGBA')
with Image.open(files[0]) as image:
    imported = image.convert('RGBA')
assert original.size == imported.size
difference = ImageChops.difference(original, imported)
errors = difference.getextrema()
assert errors == ((0, 0), (0, 0), (0, 0), (0, 0)), errors
assert sha(template) == template_sha and sha(KIT / 'tags' / donor) == configuration['sha256']
for path, expected in prepared['source_hashes'].items():
    assert sha(path) == expected, path
(DEST / 'native-import-report.json').write_text(json.dumps(dict(target=str(relative), target_sha256=sha(target),
    source=str(source), source_sha256=sha(source), native_fields=fields, max_rgba_errors=[v[1] for v in errors],
    template=template_name, template_sha256=template_sha, donor=donor, donor_sha256=configuration['sha256'],
    native_direct_save_fallback=b'attempting to save directly' in (DEST / 'native-pixels.log').read_bytes(),
    limitation='Native bitmap input verified; the three glass shaders and UV controls are not yet assigned.'), indent=2) + '\n')
print('GLASS_NATIVE_BITMAP_VERIFIED', relative, 'RGBA_ERRORS', errors, flush=True)
