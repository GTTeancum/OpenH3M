"""Export Reach bitmap tags to TGA with the official HREK tool (export-bitmap-tga).

Usage: python reach_export_bitmaps.py <out_dir> <tag path without extension, '/' or '\\'> ...
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for t in sys.argv[2:]:
    rel = t.replace('/', '\\')
    name = rel.split('\\')[-1]
    rc, text = kit.rtool('export-bitmap-tga', rel, str(out / name), log=kit.WORK / 'logs' / ('rtga-' + name + '.log'))
    made = sorted(p.name for p in out.glob(name + '*'))
    print(name, 'rc', rc, made, '' if made else text.strip()[-300:])
