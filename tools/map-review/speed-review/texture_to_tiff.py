"""Turn a texture's exported base level (from MaterialSwap export-pixels) into a TIFF the kit's importer can read,
shrunk so its longest side is at most --max (aspect kept, power-of-two sides). Normal maps are renormalised."""
import argparse, json, struct, io
from pathlib import Path
import numpy as np
from PIL import Image
p = argparse.ArgumentParser(); p.add_argument('bin', type=Path); p.add_argument('tiff', type=Path); p.add_argument('--max', type=int, default=512)
a = p.parse_args()
meta = json.loads(Path(str(a.bin) + '.json').read_text()); img = meta['images'][0]; data = a.bin.read_bytes()
w, h, fmt = img['width'], img['height'], int(img['format'].split(':')[0])
assert img['type'].startswith('0:') and img['depth'] == 1 and len(meta['images']) == 1, 'only single 2D textures'
def dds(fourcc, size):
    hdr = struct.pack('<4sIIIIIII44sII4sIIIIIIIIII', b'DDS ', 124, 0x1007 | 0x80000, h, w, size, 0, 1, bytes(44), 32, 4, fourcc, 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + data[:size]))
normal = meta['Usage'].split(':')[0] in ('2', '3', '17', '18') or 'Bump' in meta['Usage'] or 'Normal' in meta['Usage']
if fmt in (10, 11):      # x8r8g8b8 / a8r8g8b8, stored B,G,R,A
    px = np.frombuffer(data, np.uint8, w * h * 4).reshape(h, w, 4)[:, :, [2, 1, 0, 3]].copy()
    if fmt == 10: px[:, :, 3] = 255
    im = Image.fromarray(px, 'RGBA')
elif fmt == 14: im = dds(b'DXT1', max(1, w // 4) * max(1, h // 4) * 8).convert('RGBA')
elif fmt == 15: im = dds(b'DXT3', max(1, w // 4) * max(1, h // 4) * 16).convert('RGBA')
elif fmt == 16: im = dds(b'DXT5', max(1, w // 4) * max(1, h // 4) * 16).convert('RGBA')
elif fmt == 33:          # dxn: MCC stores signed BC5; bias endpoints to unsigned (as the repo converter does) and swap
    n = max(1, w // 4) * max(1, h // 4) * 16   # the two channel blocks for the PC ATI2 layout, then rebuild z
    blocks = np.frombuffer(data, np.uint8, n).reshape(-1, 16).copy(); blocks[:, (0, 1, 8, 9)] ^= np.uint8(128)
    data = blocks[:, list(range(8, 16)) + list(range(8))].tobytes()
    im = dds(b'ATI2', n).convert('RGB')
else: raise SystemExit(f'unsupported format {fmt}')
scale = max(w, h) / a.max
nw, nh = (max(1, w // int(round(scale))), max(1, h // int(round(scale)))) if scale > 1 else (w, h)
out = im.resize((nw, nh), Image.LANCZOS) if (nw, nh) != (w, h) else im
if normal or fmt == 33:
    v = np.asarray(out.convert('RGB')).astype(np.float64) / 127.5 - 1.0
    if fmt == 33: v[:, :, 2] = np.sqrt(np.clip(1 - v[:, :, 0] ** 2 - v[:, :, 1] ** 2, 0, 1))
    v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-6)
    out = Image.fromarray(np.clip((v + 1) * 127.5 + 0.5, 0, 255).astype(np.uint8), 'RGB')
a.tiff.parent.mkdir(parents=True, exist_ok=True); out.save(a.tiff, compression=None)
print(f'{w}x{h} fmt {fmt} -> {out.size[0]}x{out.size[1]} {out.mode} {"normal" if normal or fmt == 33 else ""}')
