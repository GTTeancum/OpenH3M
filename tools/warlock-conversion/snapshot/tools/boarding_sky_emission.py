"""Preserve Boarding Action's cutout sky using native simple emission.

The source from-albedo operation clears diffuse RGB after computing emission.
The native simple operation leaves diffuse intact, so explicitly zero its RGB
and sample the same base texture for emission. Fold only a verified constant
detail sample, decoded to linear color, into emission color; leave alpha testing
unchanged.
"""
def validate(cache, bitmaps, post, texture_names, textures, constant_names, constants):
    if not cache.name(cache.u(post + 12) & 65535).endswith('_0_0_1_0_0_0_4_0_0_0_0_0_0'):
        raise ValueError('Boarding sky shader options changed')
    if cache.u(post + 92):
        raise ValueError('Boarding sky emission adaptation requires static inputs')
    detail = cache.u(textures[texture_names.index('detail_map')] + 12) & 65535
    infos = bitmaps.info(detail)
    row = cache.block(cache.tags[detail]['offset'] + 96, 56)[0]
    curve = cache.data[row + 21]
    if len(infos) != 1 or (infos[0]['width'], infos[0]['height'], infos[0]['format']) != (1, 1, 11) or curve not in (1, 3, 5):
        raise ValueError('Boarding sky detail must be a constant ARGB texture with supported color curve')
    pixel = bitmaps.pixels(detail)
    if len(pixel) != 4 or pixel[3] != 255:
        raise ValueError('Boarding sky detail alpha must be opaque')
    albedo = cache.unpack('4f', constants[constant_names.index('albedo_color')])
    # Pinned HaloShaderGenerator albedo.fx: DETAIL_MULTIPLIER = 4.59479.
    samples = [pixel[2-j] / 255. for j in range(3)]
    if curve in (1, 5):
        samples = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in samples]
    return [samples[j] * 4.59479 * albedo[j] for j in range(3)]
