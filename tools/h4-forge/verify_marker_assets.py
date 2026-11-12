"""Verify private extracted marker assets; this is not live visual acceptance."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[2]
research = root / 'work/h4-forge-research'
isolated = research / 'isolated'
cache = (research / 'disc2-assets/ca_forge_ravine.map').read_bytes()
shaders = json.loads((isolated / 'marker-shaders/extracted.json').read_text())
for shader in shaders:
    code = (isolated / 'marker-shaders' / shader['file']).read_bytes()
    start, size = shader['source_file_offset'], shader['code_size']
    assert code == cache[start:start + size]
    assert hashlib.sha256(code).hexdigest() == shader['code_sha256']
    disasm = (isolated / 'marker-shaders' / (shader['file'] + '.txt')).read_text()
    assert 'exece' in disasm and 'tfetch' in disasm
    assert 'unknown' not in disasm.lower()

decoded = json.loads((isolated / 'marker-bitmaps/decoded.json').read_text())
for bitmap in decoded:
    pixels = (isolated / 'marker-bitmaps' / f"{bitmap['index']}.rgba").read_bytes()
    assert len(pixels) == bitmap['width'] * bitmap['height'] * 4
    assert hashlib.sha256(pixels).hexdigest() == bitmap['rgba_sha256']

# An independent BC1 implementation checks endpoint expansion, byte swapping,
# color interpolation and selector order for the complete original gradient.
gradient = next(b for b in decoded if b['index'] == 16659)
page = (isolated / 'marker-pages' / f"{gradient['source_page']}.bin").read_bytes()
start = gradient['source_offset']
linear = np.frombuffer(page[start:start + 512], dtype=np.uint8).reshape(-1, 2)[:, ::-1].tobytes()
expected = np.asarray(Image.frombytes('RGBA', (256, 4), linear, 'bcn', (1, 'BC1')))[0]
actual = np.frombuffer((isolated / 'marker-bitmaps/16659.rgba').read_bytes(), dtype=np.uint8).reshape(256, 4)
assert np.array_equal(expected, actual)
print(f'PASS: {len(shaders)} original shaders match the retail cache and disassemble; '
      f'{len(decoded)} texture payloads verified; gradient matches independent BC1 decoder.')
