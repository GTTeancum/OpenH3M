"""Find Halo 3 textures that are the same picture as Tombstone's Halo 2 textures.
Pulls each listed Halo 3 tag's top-level pixels with MaterialSwap export-pixels-list (one ManagedBlam process),
keeps only a 32x32 greyscale thumbnail, deletes the raw pixels, and scores every Tombstone texture against every
thumbnail by normalised correlation (1.0 = identical picture; brightness/contrast differences ignored).
Usage: texture_match.py <list of H3 tag paths> <out.json>"""
import json, io, struct, shutil, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent)); import kit_run
H2 = ROOT / '.local/h3ek-source/data/levels/test/tombstone/bitmaps'
RAW = ROOT / '.local/tombstone/h3px'; THUMBS = ROOT / '.local/tombstone/h3-thumbs.npz'
BS = chr(92)


def decode(bin_path):
    meta = json.loads(Path(str(bin_path) + '.json').read_text()); img = meta['images'][0]; data = bin_path.read_bytes()
    w, h, fmt = img['width'], img['height'], int(img['format'].split(':')[0])
    def dds(fourcc, size):
        hdr = struct.pack('<4sIIIIIII44sII4sIIIIIIIIII', b'DDS ', 124, 0x1007 | 0x80000, h, w, size, 0, 1, bytes(44), 32, 4, fourcc, 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0)
        return Image.open(io.BytesIO(hdr + data[:size]))
    bl = max(1, w // 4) * max(1, h // 4)
    if fmt in (10, 11): return Image.fromarray(np.frombuffer(data, np.uint8, w * h * 4).reshape(h, w, 4)[:, :, [2, 1, 0]].copy())
    if fmt == 14: return dds(b'DXT1', bl * 8)
    if fmt == 15: return dds(b'DXT3', bl * 16)
    if fmt == 16: return dds(b'DXT5', bl * 16)
    if fmt in (0, 2, 3): return Image.frombytes('L', (w, h), data[:w * h])   # 8-bit monochrome-ish
    raise ValueError(f'format {fmt}')


def thumb(im):
    a = np.asarray(im.convert('L').resize((32, 32), Image.Resampling.BOX), np.float32).ravel()
    a -= a.mean(); n = np.linalg.norm(a)
    return a / n if n > 1e-3 else None


tags = [t.strip() for t in Path(sys.argv[1]).read_text().split('\n') if t.strip()]
names, vecs = [], []
if THUMBS.exists():
    z = np.load(THUMBS, allow_pickle=True); names, vecs = list(z['names']), list(z['vecs'])
todo = [t for t in tags if t not in set(names)]
for i in range(0, len(todo), 100):
    chunk = todo[i:i + 100]
    shutil.rmtree(RAW, ignore_errors=True); RAW.mkdir(parents=True)
    lst = RAW / 'list.txt'; lst.write_text('\n'.join(t + '.bitmap' for t in chunk))
    kit_run.run('swap', ['export-pixels-list', str(lst), str(RAW)], timeout=1800, log_name='pixels.log')
    for t in chunk:
        b = RAW / ((t + '.bitmap').replace(BS, '~') + '.bin')
        try:
            v = thumb(decode(b)) if b.exists() else None
        except Exception: v = None
        if v is not None: names.append(t); vecs.append(v)
    np.savez(THUMBS, names=np.array(names, dtype=object), vecs=np.array(vecs))
    print('thumbnails', len(names), flush=True)
shutil.rmtree(RAW, ignore_errors=True)
M = np.array(vecs); out = {}
for f in sorted(H2.glob('*.tif')):
    v = thumb(Image.open(f))
    if v is None: continue
    best = []
    for k in range(4):   # also try 90-degree rotations
        vv = thumb(Image.open(f).rotate(90 * k, expand=True))
        s = M @ vv; best += [(float(s[j]), names[j], 90 * k) for j in np.argsort(-s)[:3]]
    best.sort(reverse=True)
    out[f.stem] = best[:3]
json.dump(out, open(sys.argv[2], 'w'), indent=1)
for k, v in sorted(out.items(), key=lambda kv: -kv[1][0][0]):
    print(f'{v[0][0]:.3f}  {k:40s} {v[0][1]}')
