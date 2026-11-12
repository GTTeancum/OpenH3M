"""Render exported ImGui draw data without a window, GPU, or desktop capture."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(sys.argv[1]).resolve()
data = json.loads((root / 'panel.json').read_text())
w, h = data['width'], data['height']
aw, ah = data['atlas']
atlas = np.fromfile(root / 'font.rgba', dtype=np.uint8).reshape(ah, aw, 4) / 255.
canvas = np.full((h, w, 3), (.025, .035, .05), dtype=float)
for draw in data['lists']:
    vertices = np.array(draw['vertices'])
    colors = vertices[:, 4].astype(np.uint32)
    rgba = np.stack([(colors >> shift) & 255 for shift in (0, 8, 16, 24)], axis=1) / 255.
    indices = np.array(draw['indices'])
    for start, count, offset, cx0, cy0, cx1, cy1 in draw['commands']:
        for tri in indices[int(start):int(start + count)].reshape(-1, 3):
            ids = tri + int(offset)
            v = vertices[ids, :4]
            x0 = max(0, int(cx0), int(np.floor(v[:, 0].min())))
            y0 = max(0, int(cy0), int(np.floor(v[:, 1].min())))
            x1 = min(w, int(cx1), int(np.ceil(v[:, 0].max())))
            y1 = min(h, int(cy1), int(np.ceil(v[:, 1].max())))
            if x0 >= x1 or y0 >= y1:
                continue
            x, y = np.meshgrid(np.arange(x0, x1) + .5, np.arange(y0, y1) + .5)
            ax, ay, bx, by, dx, dy = *v[0, :2], *v[1, :2], *v[2, :2]
            denominator = (by - dy) * (ax - dx) + (dx - bx) * (ay - dy)
            if abs(denominator) < 1e-8:
                continue
            a = ((by - dy) * (x - dx) + (dx - bx) * (y - dy)) / denominator
            b = ((dy - ay) * (x - dx) + (ax - dx) * (y - dy)) / denominator
            c = 1 - a - b
            mask = (a >= 0) & (b >= 0) & (c >= 0)
            weights = np.stack((a, b, c), axis=-1)
            uv = weights @ v[:, 2:4]
            tx = np.clip((uv[..., 0] * aw).astype(int), 0, aw - 1)
            ty = np.clip((uv[..., 1] * ah).astype(int), 0, ah - 1)
            color = (weights @ rgba[ids]) * atlas[ty, tx]
            alpha = (color[..., 3] * mask)[..., None]
            region = canvas[y0:y1, x0:x1]
            region[:] = color[..., :3] * alpha + region * (1 - alpha)
Image.fromarray(np.uint8(np.clip(canvas * 255, 0, 255))).save(root / 'panel.png')
print(root / 'panel.png')
