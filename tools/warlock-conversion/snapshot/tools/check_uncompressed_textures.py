"""Check real source texture bytes against the new retail encoding, without a run."""
import argparse
import json
import struct
from pathlib import Path
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from encode_bitmap import encode_bitmap_base, mip_size, expand_argb
from xbox_bitmap import addresses, untile_base


def check_addresses():
    # Independent XGAddress2DTiledOffset algebra for four-byte texels.
    for pitch, height in [(1, 1), (33, 65), (257, 129)]:
        actual = addresses(pitch, height, 4)
        for y in range(height):
            for x in range(pitch):
                macro = ((x >> 5) + (y >> 5) * (((pitch + 31) & ~31) >> 5)) << 9
                micro = ((x & 7) + ((y & 6) << 2)) << 2
                off = macro + ((micro & ~15) << 1) + (micro & 15) + ((y & 8) << 5) + ((y & 1) << 4)
                expected = ((off & ~511) << 3) + ((off & 448) << 2) + (off & 63) + ((y & 16) << 7) + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6)
                assert actual[y, x] == expected, (x, y, pitch)
    assert expand_argb(bytes([0, 128]), 2, 1, 0) == bytes([255, 255, 255, 0, 255, 255, 255, 128])
    assert expand_argb(bytes([0, 128]), 2, 1, 1) == bytes([0, 0, 0, 255, 128, 128, 128, 255])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--material-inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    check_addresses()
    cache = Cache(args.source, True)
    try:
        source = BitmapSource(cache)
        inventory = json.loads(args.material_inventory.read_text())
        materials = next(x['materials'] for x in inventory['9178:sbsp']['blocks'] if x['name'] == 'Materials')
        report = []
        for slot, material in enumerate(materials):
            if material['group'] not in ('rmsh', 'rmfl', 'rmtr') or not material['textures']:
                continue
            texture = material['textures'][1 if material['group'] == 'rmtr' else 0]
            if not texture['name']:
                continue
            tid = int(texture['datum'], 16) & 65535
            info = source.info(tid)[0]
            fmt = info['format']
            if fmt not in (0, 1, 10, 11):
                continue
            w, h = info['width'], info['height']
            pixels = source.pixels(tid)
            while max(w, h) > 512:
                pixels = pixels[mip_size(w, h, fmt):]
                w, h = max(1, w // 2), max(1, h // 2)
            record, control, raw = encode_bitmap_base(source, tid)
            assert struct.unpack_from('>HH', record, 4) == (w, h)
            assert struct.unpack_from('>I', control, 48)[0] == 0x18280186
            assert untile_base(raw, w, h, 11) == expand_argb(pixels, w, h, fmt)
            report.append({'slot': slot, 'source_format': fmt, 'width': w, 'height': h,
                           'lossless_selected_mip': True})
        assert report, 'No matching source textures checked'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f'{len(report)} material slots: selected mip bytes preserved; address and channel checks passed.')
    finally:
        cache.close()


if __name__ == '__main__':
    main()
