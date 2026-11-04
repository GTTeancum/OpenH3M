"""Compare official H3/Reach water arrays using native Tool exports only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
DEST = OUT / 'water-bitmap-pixels'
sys.path.insert(0, str(OUT / 'python-packages'))
from PIL import Image, ImageChops, ImageStat

env = os.environ.copy()
for key, relative in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'),
                      ('TEMP', 'temp'), ('TMP', 'temp')]:
    env[key] = str(OUT / relative)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

rows = []
for name in ['wave_new_displ_water', 'wave_new_slope_water']:
    tag = 'rasterizer\\water\\wave_new\\' + name + '.bitmap'
    exports = {}
    for game, kit_name, exe in [('h3', 'h3ek', 'tool.exe'), ('reach', 'hrek', 'tool_fast.exe')]:
        kit = ROOT / 'work/editing-kits' / kit_name
        source = kit / 'tags' / tag
        before = sha(source)
        folder = DEST / game
        folder.mkdir(parents=True, exist_ok=True)
        xml_path = folder / (name + '.xml')
        commands = [
            ['export-tag-to-xml', str(source), str(xml_path)],
            ['export-bitmap-tga', tag[:-7], str(folder) + os.sep],
        ]
        for command in commands:
            run = subprocess.run([str(kit / exe), *command], cwd=kit, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
            (folder / (name + '-' + command[0] + '.log')).write_bytes(run.stdout)
            assert run.returncode == 0, (game, command)
        parsed = ET.fromstring(xml_path.read_text(errors='replace').replace('<unavailable>', '&lt;unavailable&gt;'))
        blocks = parsed.findall("block[@name='bitmaps']/element")
        if not blocks and game == 'reach':
            # Reach Tool's older XML places block elements beside the count field.
            children = list(parsed)
            header = next(i for i, e in enumerate(children)
                          if e.tag == 'field' and e.get('name') == 'bitmaps')
            count = int(children[header].get('value'))
            blocks = children[header + 1:header + 1 + count]
            assert all(e.tag == 'element' for e in blocks)
        assert blocks, (game, xml_path)
        metadata = [{f.get('name'): f.get('value') for f in b.findall('field')} for b in blocks]
        slices = sorted(folder.glob(name + '_00_*.tga'))
        assert len(slices) == 16, (game, name, len(slices))
        assert all(p.stat().st_mtime_ns >= source.stat().st_mtime_ns for p in slices)
        assert sha(source) == before, source
        exports[game] = dict(source=str(source), sha256=before, metadata=metadata,
                             slices=[dict(path=str(p), sha256=sha(p)) for p in slices])
    matching_metadata = {}
    for key in ['width', 'height', 'depth', 'type', 'format', 'mipmap count', 'curve']:
        h3_values = [m[key] for m in exports['h3']['metadata']]
        reach_values = [m[key] for m in exports['reach']['metadata']]
        assert h3_values == reach_values, (name, key, h3_values, reach_values)
        matching_metadata[key] = h3_values
    comparisons = []
    for h3, reach in zip(exports['h3']['slices'], exports['reach']['slices']):
        a = Image.open(h3['path']).convert('RGBA')
        b = Image.open(reach['path']).convert('RGBA')
        assert a.size == b.size == (128, 128)
        difference = ImageChops.difference(a, b)
        errors = ImageStat.Stat(difference).mean
        assert difference.getextrema() == ((0, 0),) * 4, (name, h3['path'], errors)
        comparisons.append(dict(slice=Path(h3['path']).name, size=list(a.size),
                                mean_RGBA_error=errors, exact_decoded_match=True))
    rows.append(dict(tag=tag, exports=exports, matching_metadata=matching_metadata,
                     comparisons=comparisons))

report = dict(arrays=rows, limitation='Exact native top-mip slices only. Metadata retained for review; '
              'mip contents, shader response and original Xbox 360 availability are not established by pixel equality.')
(OUT / 'water-wave-asset-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('WATER_WAVE_ASSETS: 2 arrays, 32 exact native RGBA slice matches; original tags unchanged.')
