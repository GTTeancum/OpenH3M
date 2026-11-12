"""Suppress donor-only cloud diffuse lighting, preserving authored BC3 alpha.

HaloShaderGenerator 5af3671: material_model_none.fx zeros diffuse;
two_detail_overlay multiplies RGB by overlay RGB and alpha by overlay alpha.
Self-illumination detail samples independent textures.
"""
from encode_bitmap import encode_bitmap_base, mip_size


def bake(materials, datum):
    source = materials.bitmaps
    tag = datum & 65535
    infos = source.info(tag)
    if len(infos) != 1:
        raise ValueError('Cloud mask requires one image')
    info = infos[0]
    row = source.c.block(source.c.tags[tag]['offset'] + 96, 56)[0]
    if info['format'] != 16 or source.c.unpack('H', row + 10)[0] != 0:
        raise ValueError('Cloud mask requires a 2D BC3 image')
    original = source.pixels(tag)
    data = bytearray(original)
    width, height = info['width'], info['height']
    size = 0
    for _ in range(info['mips']):
        size += mip_size(width, height, 16)
        width, height = max(1, width // 2), max(1, height // 2)
    if len(data) != size:
        raise ValueError('Cloud mask mip payload length differs')
    for offset in range(0, size, 16):
        # Independent BC3 RGB endpoints/selectors; alpha bytes stay untouched.
        data[offset + 8:offset + 16] = bytes(8)
    assert all(data[o:o+8] == original[o:o+8] for o in range(0, size, 16))

    class Baked:
        c = source.c
        def info(self, tag): return infos
        def pixels(self, tag, index=0): return bytes(data)

    return materials.bitmap_resource(*encode_bitmap_base(Baked(), tag, preserve_bc_mips=True))
