"""Side-by-side sheet: each Halo 2 Tombstone texture (from the Halo 3 kit data folder) next to Halo 3 candidate
textures exported with the Halo 3 kit's own tool (export-bitmap-tga, hidden desktop).
Usage: texture_compare_sheet.py <pairs.json {h2 name: [h3 tag paths without extension]}> <out.png>"""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
import kit_run
BS = chr(92)
H2 = ROOT / '.local/h3ek-source/data/levels/test/tombstone/bitmaps'
WORK = ROOT / '.local/tombstone/h3-candidates'; WORK.mkdir(parents=True, exist_ok=True)
pairs = json.load(open(sys.argv[1]))
CELL = 160


def h3_image(tag):
    stem = tag.split(BS)[-1]
    found = sorted(WORK.glob(stem + '__*.tga'))
    if not found:
        kit_run.run('tool', ['export-bitmap-tga', tag, str(WORK) + BS + stem + '__'], timeout=120, log_name='export.log')
        found = sorted(WORK.glob(stem + '__*.tga'))
    return Image.open(found[0]) if found else None


rows = []
for h2, cands in pairs.items():
    cells = [(h2 + ' (Tombstone)', Image.open(H2 / (h2 + '.tif')))]
    for c in cands:
        c = c.replace("/", BS); cells.append((c.split(BS)[-1], h3_image(c)))
    rows.append(cells)
w = CELL * max(len(r) for r in rows); h = (CELL + 14) * len(rows)
sheet = Image.new('RGB', (w, h), (30, 30, 30)); dr = ImageDraw.Draw(sheet)
for y, r in enumerate(rows):
    for x, (label, im) in enumerate(r):
        if im is not None:
            sheet.paste(im.convert('RGB').resize((CELL - 4, CELL - 4)), (x * CELL + 2, y * (CELL + 14) + 14))
        dr.text((x * CELL + 2, y * (CELL + 14)), label[:26], fill=(255, 255, 255) if x else (255, 200, 80))
sheet.save(sys.argv[2]); print('sheet', sys.argv[2], len(rows), 'rows')
