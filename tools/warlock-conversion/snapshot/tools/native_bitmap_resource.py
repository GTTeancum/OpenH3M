"""Copy a native single-bitmap resource, retaining arrays/cubes and every mip."""
from resource_reader import Resource


def copy_bitmap_resource(cache, datum, shared_paths=None):
    if cache.mcc:
        raise ValueError('Native bitmap resource copy requires a retail donor')
    zone = next(tag['offset'] for tag in cache.tags.values() if tag['group'] == 'zone')
    row = cache.block(zone + 88, 64)[datum & 65535]
    if cache.unpack('H', row + 16)[0] != datum >> 16:
        raise ValueError('Native bitmap resource salt mismatch')
    resource = Resource(cache, datum, shared_paths)
    interops = [cache.unpack('II', at) for at in cache.block(row + 52, 8)]
    if len(resource.data) != 64 or resource.root != 52 or interops != [(0x20000034, 2)]:
        raise ValueError('Unsupported native bitmap control layout')
    sizes = [resource.unpack('I', offset)[0] for offset in (0, 20)]
    payload = bytearray()
    locations = {}
    for segment, size in enumerate(sizes):
        if not size:
            continue
        if segment >= len(resource.raw) or size > len(resource.raw[segment]):
            raise ValueError('Truncated native bitmap mip segment')
        payload.extend(bytes((-len(payload)) % 4096))
        locations[segment] = len(payload)
        # Resource.raw extends to the page end; copy only this bitmap's bytes.
        payload.extend(resource.raw[segment][:size])
    fixups = []
    for offset, address in resource.fix.items():
        if offset == 52 and address == 0x20000000:
            fixups.append((offset, address))
        elif offset in (12, 32):
            segment = 0 if offset == 12 else 1
            expected = (0x40000000, 0x60000000)[segment]
            if address != expected or segment not in locations:
                raise ValueError('Unsupported native bitmap segment fixup')
            fixups.append((offset, 0x40000000 | locations[segment]))
        else:
            raise ValueError('Unexpected native bitmap resource fixup')
    required = {52} | {12 + index * 20 for index, size in enumerate(sizes) if size}
    if set(resource.fix) != required:
        raise ValueError('Native bitmap fixups do not cover its mip segments')
    return {'control': resource.data, 'raw': bytes(payload), 'root': 52,
            'fixups': fixups, 'interops': interops}
