"""Export Halo 2 bitmap tags with the Halo 2 kit's own tool (export-bitmap-tga) and write them as TIFF source
files into a Halo 3 kit data folder, ready for the Halo 3 tool's `bitmaps` import.
Usage: h2_bitmaps_to_h3.py <list of H2 bitmap tag paths, no extension> <H3 data folder> [--skip <path>...]
Only the first frame/face of each bitmap is kept (cube maps should be skipped and replaced with stock H3 ones)."""
import os, sys, shutil
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/asset-library'))
import hidden_run
K = ROOT / '.local/h2ek-source'
BS = chr(92)
args = sys.argv[1:]
skip = set(args[args.index('--skip') + 1:]) if '--skip' in args else set()
tags = [t.strip() for t in Path(args[0]).read_text().split('\n') if t.strip() and t.strip() not in skip]
out = Path(args[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
work = (ROOT / '.local/tombstone/h2-bitmaps').resolve(); shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
e = os.environ.copy(); e['TEMP'] = e['TMP'] = str(K / 'temp')
names = [t.split(BS)[-1] for t in tags]
assert len(set(names)) == len(names), 'duplicate texture names'
failed = []
for t, name in zip(tags, names):
    rc, log = hidden_run.run([str(K / 'tool.exe'), 'export-bitmap-tga', t, str(work) + BS + name + '__'], str(K), str(K / 'temp/bitmap.log'), timeout=120, env=e)
    frames = sorted(work.glob(name + '__*.tga'))
    if not frames: failed.append(t); print('FAILED', t, log[-200:]); continue
    im = Image.open(frames[0])
    im = im if im.mode in ('RGB', 'RGBA', 'L') else im.convert('RGBA')
    if im.mode == 'RGBA' and im.getextrema()[3] == (255, 255): im = im.convert('RGB')
    im.save(out / (name + '.tif'), compression='tiff_lzw')
    print(name, im.size, im.mode, 'frames', len(frames))
shutil.rmtree(work, ignore_errors=True)
print('written', len(tags) - len(failed), 'failed', len(failed))
