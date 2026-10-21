"""Read Forge World's authored large collision mesh without modifying its cache."""
import struct
import numpy as np
from resource_reader import Resource


def read_mesh(cache):
    tag = next(t for n, t in cache.tags.items() if t['group'] == 'sbsp'
               and cache.name(n) == r'levels\multi\forge_halo\forge_halo')
    resource = Resource(cache, cache.u(tag['offset'] + 0x38c))
    if resource.unpack('I', resource.root + 12)[0] != 1:
        raise ValueError('Expected one authored large collision BSP')
    header = resource.fix[resource.root + 16]
    if header >> 29 != 1:
        raise ValueError('Expected resident collision header')
    header &= 0x1fffffff
    formats = ('3i', '4f', 'BBHI', '2i', '3fii', 'iihhhBb', '6i', '3fii')
    arrays = []
    for index, fmt in enumerate(formats):
        at = header + index * 12
        count = resource.unpack('I', at)[0]
        if not count:
            arrays.append([])
            continue
        pointer = resource.fix[at + 4]
        segment, offset = pointer >> 29, pointer & 0x1fffffff
        if segment == 1:
            data = resource.data
        elif segment in (2, 3) and segment - 2 < len(resource.raw):
            data = resource.raw[segment - 2]
        else:
            raise ValueError('Invalid collision segment')
        size = count * struct.calcsize('<' + fmt)
        if offset + size > len(data):
            raise ValueError('Collision array exceeds resource')
        arrays.append(list(struct.iter_unpack('<' + fmt, data[offset:offset + size])))
    return tag, arrays


def surface_loops(arrays):
    """Return oriented vertex loops; reject corrupt ownership and open cycles."""
    edges, vertices = arrays[6:8]
    loops = []
    for index, surface in enumerate(arrays[5]):
        first = edge = surface[1]
        seen, loop = set(), []
        while edge not in seen:
            if not 0 <= edge < len(edges):
                raise ValueError('Surface edge outside table')
            seen.add(edge)
            start, end, forward, reverse, left, right = edges[edge]
            if left == index:
                loop.append(start)
                edge = forward
            elif right == index:
                loop.append(end)
                edge = reverse
            else:
                raise ValueError('Surface edge ownership mismatch')
        if edge != first or len(loop) < 3 or any(not 0 <= v < len(vertices) for v in loop):
            raise ValueError('Invalid surface loop')
        loops.append(loop)
    return loops


def positions(arrays):
    return np.asarray([row[:3] for row in arrays[7]])
