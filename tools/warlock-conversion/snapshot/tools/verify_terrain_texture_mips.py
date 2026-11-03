"""Compare every retained native terrain texture mip with its MCC source blocks.

This verifies generated resources, including required signed-DXN conversion.
It does not assert that the runtime binds or fetches those resources correctly.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from cache_reader import Cache
from resource_reader import Resource
from mcc_bitmap_source import BitmapSource
from material_importer import MaterialImporter
from string_ids import StringTable
from encode_bitmap import mip_size, mcc_dxn_to_retail
from xbox_bitmap import untile_base
from xbox_mip_chain import layout


def verify(source, candidate, source_material, target_material, shared=None):
    s, t = Cache(source, True), Cache(candidate)
    try:
        if shared:
            s.shared_paths = {r'maps\shared.map': shared}
        bitmaps = BitmapSource(s)
        def textures(c, index):
            post = c.block(c.tags[index]['offset'] + 40, 140 if c.mcc else 132)[0]
            names = MaterialImporter.parameters(None, c, StringTable(c), post)[0]
            rows = c.block(post + 16, 28 if c.mcc else 24)
            if len(names) != len(rows):
                raise ValueError('Texture names and sampler count differ')
            return dict(zip(names, (c.u(row + 12) & 65535 for row in rows)))
        original, converted = textures(s, source_material), textures(t, target_material)
        if original.keys() != converted.keys():
            raise ValueError('Source and target texture names differ')
        checks = []
        for name, si in original.items():
            info = bitmaps.info(si)[0]
            root = t.tags[converted[name]]['offset']
            row = t.block(root + 96, 48)[0]
            w, h = t.unpack('HH', row + 4)
            fmt = t.unpack('H', row + 12)[0]
            count = t.data[row + 20] + 1
            if fmt not in (14, 15, 16, 33) or info['format'] != fmt:
                raise ValueError('This audit requires unchanged BC formats')
            resource = Resource(t, t.u(t.block(root + 140, 8)[0]))
            if resource.unpack('HHBB', 40) != (w, h, 1, count):
                raise ValueError('Bitmap metadata and resource dimensions/mips differ')
            expected = bitmaps.pixels(si)
            sw, sh, selected = info['width'], info['height'], 0
            while (sw, sh) != (w, h):
                if selected + 1 >= info['mips']:
                    raise ValueError('Target size does not match an authored source mip')
                expected = expected[mip_size(sw, sh, fmt):]
                sw, sh, selected = max(1, sw // 2), max(1, sh // 2), selected + 1
            if count > info['mips'] - selected:
                raise ValueError('Native chain exceeds authored mip count')
            if fmt == 33:
                expected = mcc_dxn_to_retail(expected)
            actual = resource.raw[0]
            if count == 1:
                mips = [untile_base(actual, w, h, fmt)]
            else:
                bpb = 8 if fmt == 14 else 16
                rows, size = layout(w, h, count, bpb)
                if len(actual) < size:
                    raise ValueError('Native mip payload truncated')
                raw = np.frombuffer(actual, dtype=np.uint8)
                mips = [raw[pos.reshape(-1, 1) + np.arange(bpb)]
                        .reshape(-1, bpb // 2, 2)[:, :, ::-1].tobytes()
                        for pos, _ in rows]
            offset = 0
            equal = []
            for level, data in enumerate(mips):
                size = mip_size(max(1, w >> level), max(1, h >> level), fmt)
                if len(data) != size:
                    raise ValueError('Decoded mip has unexpected size')
                equal.append(data == expected[offset:offset + size])
                offset += size
            checks.append({'texture': name, 'width': w, 'height': h,
                           'format': fmt, 'source_base_mip': selected,
                           'native_mips': count, 'exact_mips': equal})
        return {'candidate': str(candidate), 'source': str(source),
                'passed': all(all(row['exact_mips']) for row in checks),
                'checks': checks,
                'scope': 'All retained BC blocks after required DXN conversion; not a live GPU fetch check.'}
    finally:
        s.close()
        t.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'candidate', 'report'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--source-shared', type=Path)
    p.add_argument('--source-material-index', type=int, required=True)
    p.add_argument('--target-material-index', type=int, required=True)
    a = p.parse_args()
    result = verify(a.source, a.candidate, a.source_material_index,
                    a.target_material_index, a.source_shared)
    a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'textures': len(result['checks']),
                      'mips': sum(row['native_mips'] for row in result['checks'])}))
    raise SystemExit(0 if result['passed'] else 1)
