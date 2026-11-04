"""Inspect official Tool's saved tags and exported pixels; no asset edits."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
sys.path.insert(0, str(OUT / 'python-packages'))
from PIL import Image, ImageChops, ImageStat

def xml(path):
    # Tool's own output contains this unescaped resource placeholder.
    return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>', '&lt;unavailable&gt;'))

stock = xml(OUT / 'h3-shader-xml/bunkerworld_treebranch.shader_foliage.xml')
trial = xml(OUT / 'foliage-trial.shader_foliage.xml')
reference = r'levels\custom\battle_canyon_fresh\bitmaps\tree_boreal_leaves_diffuse,bitm'
stock_parameters = stock.find("block[@name='parameters']")
trial_parameters = trial.find("block[@name='parameters']")
for index in (0, 2):
    field = trial_parameters[index].find("field[@name='bitmap']")
    assert field.get('value') == reference, (index, field.attrib)
    field.set('value', stock_parameters[index].find("field[@name='bitmap']").get('value'))
trial.set('id', stock.get('id'))
assert ET.tostring(trial) == ET.tostring(stock), 'Unexpected changes beyond the two approved texture references'

source_hashes = json.loads((OUT / 'foliage-trial-source-hashes.json').read_text(encoding='utf-8-sig'))
for path, expected in source_hashes.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest().upper() == expected

source_path = ROOT / 'work/editing-kits/hrek/data/levels/shared/bitmaps/nature/tree/tree_boreal_leaves_diffuse.tiff'
export_path = OUT / 'foliage-trial-exporttree_boreal_leaves_diffuse_00_00.tga'
with Image.open(source_path) as original, Image.open(export_path) as exported:
    assert original.size == exported.size == (512, 512)
    assert original.mode == exported.mode == 'RGBA'
    delta = ImageChops.difference(original, exported)
    report = dict(shader_changes='Only base_map and alpha_test_map references; all other exported stock fields unchanged',
                  source_hashes_unchanged=True, size=list(exported.size), mode=exported.mode,
                  source_alpha_range=original.getchannel('A').getextrema(),
                  h3_alpha_range=exported.getchannel('A').getextrema(),
                  mean_absolute_channel_difference=ImageStat.Stat(delta).mean,
                  channel_difference_extrema=delta.getextrema(),
                  limitation='Pixel/tag checks only; no shader rendering, alpha cutoff, foliage motion, MCC or 360 acceptance.')
    assert report['h3_alpha_range'] == (0, 255), 'Leaf transparency was lost'
(OUT / 'foliage-trial-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
