"""Read MCC Reach DualVMF lightmap blocks without extracting resource pages.

ReachLightmapConverter.cs (TagTool ce2dc6ac) consumes one direction texture
and three intensity layers. MCC stores linear BC blocks rather than Xenos
tiles. This reader deliberately does not relabel them as H3 SH textures.
"""
from reach_resource import ReachResource


def read_lightmap_pair(cache, lighting_offset, shared_paths):
    result = {}
    for label, offset, expected in (
            ('direction', 0x1c, (44, 83, 0, 1)),
            ('intensity', 0x2c, (16, 77, 3, 3))):
        datum = cache.u(lighting_offset + offset + 12)
        tag = cache.tags.get(datum & 65535)
        if not tag or tag['group'] != 'bitm' or tag['salt'] != datum >> 16:
            raise ValueError('Invalid Reach lightmap bitmap reference')
        images = cache.block(tag['offset'] + 0x7c, 56)
        hardware = cache.block(tag['offset'] + 0xa8, 8)
        if len(images) != 1 or len(hardware) != 1:
            raise ValueError('Expected one non-interleaved Reach lightmap image')
        image = images[0]
        width, height, depth = cache.unpack('HHH', image)
        kind = cache.data[image + 6]
        fmt = cache.unpack('H', image + 8)[0]
        resource = ReachResource(cache, cache.u(hardware[0]), shared_paths, {})
        if resource.root != 60 or resource.ptr(60) != 0:
            raise ValueError('Unexpected Reach lightmap control layout')
        rw, rh, rd, mips, rk = resource.unpack('HHBBB', 40)
        dxgi = resource.unpack('I', 52)[0]
        if (fmt, dxgi, kind, depth) != expected:
            raise ValueError('Unsupported Reach DualVMF texture format/layers')
        if (rw, rh, rd, rk) != (width, height, depth, kind):
            raise ValueError('Reach lightmap dimensions disagree with resource')
        if not width or not height or mips != 1 or cache.data[image + 16] != 0:
            raise ValueError('Expected nonempty single-mip Reach lightmap')
        size, high = resource.unpack('I', 0)[0], resource.unpack('I', 20)[0]
        slice_size = ((width + 3)//4) * ((height + 3)//4) * 16
        if high or size != slice_size * depth:
            raise ValueError('Unsupported Reach lightmap segment layout')
        if resource.fix.get(12) != 0x40000000 or size > len(resource.raw[0]):
            raise ValueError('Reach lightmap pixel range outside resource')
        result[label] = dict(width=width, height=height, depth=depth,
                             format=fmt, dxgi=dxgi, slice_bytes=slice_size,
                             pixels=bytes(resource.raw[0][:size]))
    if (result['direction']['width'], result['direction']['height']) != (
            result['intensity']['width'], result['intensity']['height']):
        raise ValueError('Reach DualVMF lightmap pair dimensions differ')
    result['brightness'] = cache.unpack('f', lighting_offset + 0x18)[0]
    return result
