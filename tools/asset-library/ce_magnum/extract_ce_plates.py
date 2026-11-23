"""Write the authored color plates stored inside CE bitmap tags as TIFF source images.

Input: JSON produced by read_ce_tags.py (General-101 reader). CE stores the
authored source as a big-endian uint32 decompressed size followed by a zlib
stream of 32-bit BGRA pixels ("compressed color plate data").
Output: H3EK data folder images for tool.exe bitmap import.
"""
import base64, json, struct, sys, zlib
from pathlib import Path
from PIL import Image

def plate(json_path):
    d = json.loads(Path(json_path).read_text())['Data']
    w, h = d['color plate width'], d['color plate height']
    raw = base64.b64decode(d['compressed color plate data']['encoded'])
    size = struct.unpack('>I', raw[:4])[0]
    px = zlib.decompress(raw[4:])
    assert len(px) == size == w * h * 4, (json_path, len(px), size, w, h)
    return Image.frombuffer('RGBA', (w, h), px, 'raw', 'BGRA', 0, 1)

if __name__ == '__main__':
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    img = plate(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, compression='tiff_lzw')
    a = img.getchannel('A').getextrema()
    print('PLATE', src.name, img.size, 'alpha range', a, '->', dst)
