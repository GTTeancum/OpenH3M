"""Reduce the constant gravlift emission sampler without dropping moving alpha."""
from encode_bitmap import expand_argb, mip_size


def uniform_emission_scale(source, tag):
    info = source.info(tag)
    if len(info) != 1 or any(info[0][k] != v for k,v in
                            dict(width=1,height=1,format=11,mips=1).items()):
        raise ValueError('Gravlift emission factor must be a single constant ARGB pixel')
    row = source.c.block(source.c.tags[tag]['offset']+96,56)[0]
    if source.c.data[row+21] != 3 or source.c.unpack('H',row+10)[0] != 0:
        raise ValueError('Gravlift emission factor must use linear 2D sampling')
    raw = source.pixels(tag)
    if raw != b'\x40\x40\x40\xff':
        raise ValueError('Audited gravlift constant texture changed')
    # self_illumination_detail_ps: uniform * detail * DETAIL_MULTIPLIER.
    return (64. / 255.) * 4.59479


def black_rgb_mask(source, tag):
    info = source.info(tag)[0]
    if info['format'] != 3:
        raise ValueError('Gravlift base mask must be A8Y8')
    raw = source.pixels(tag)
    result = bytearray(); offset = 0
    for level in range(info['mips']):
        w,h = max(1,info['width']>>level),max(1,info['height']>>level)
        size = mip_size(w,h,3)
        pixels = bytearray(expand_argb(raw[offset:offset+size],w,h,3))
        for channel in range(3): pixels[channel::4] = bytes(w*h)
        result.extend(pixels); offset += size
    if offset != len(raw): raise ValueError('Unexpected gravlift mask mip payload')
    class Baked:
        c = source.c
        def info(self, unused):
            return [dict(width=info['width'],height=info['height'],format=11,
                         mips=info['mips'],kind=0,curve=3)]
        def pixels(self, unused, index=0): return bytes(result)
    return Baked()
