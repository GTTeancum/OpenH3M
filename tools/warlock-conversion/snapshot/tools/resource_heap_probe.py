"""Bounded read-only retail resource LRU occupancy, not total console RAM.

Original XEX 822C2058: page table +C -> heap; heap +70 -> datum table,
table +44 -> 24-byte nodes, +48 -> first handle. Node +4 is units, +8
offset, +C next. 8229819C shifts bytes by heap +3C; 822981D8 bounds
allocation against heap +38. No PC-build capacity constants are used.
"""
import struct


def snapshot(read, memory, wrapper):
    def data(address, size):
        if not 0x10000 <= address < 0xe0000000 or not 0 <= size <= 65536 or address + size > 0xe0000000:
            raise ValueError('Resource probe read outside bounded guest range')
        return read(memory + address, size)

    def word(address):
        return struct.unpack('>I', data(address, 4))[0]

    heap = word(wrapper + 12)
    header = data(heap, 0x78)
    capacity, shift = struct.unpack_from('>II', header, 0x38)
    if shift > 20 or capacity << shift > 512 * 1024 * 1024:
        raise ValueError('Unexpected resource heap capacity/unit')
    table = word(heap + 0x70)
    limit, stride = struct.unpack('>II', data(table + 0x20, 8))
    if not 0 < limit <= 65535 or stride != 24:
        raise ValueError('Unexpected resource node table layout')
    nodes = word(table + 0x44)
    first = word(heap + 0x48)
    handle, previous, end, used, largest = first, 0xffffffff, 0, 0, 0
    seen = set()
    while handle != 0xffffffff:
        index = handle & 65535
        if index >= limit:
            raise ValueError('Resource handle exceeds node table')
        if index in seen or len(seen) >= limit:
            raise ValueError('Cyclic resource allocation list')
        seen.add(index)
        salt, units, offset, following, back, _ = struct.unpack('>6I', data(nodes + index * 24, 24))
        if salt >> 16 != handle >> 16 or back != previous or units == 0 or offset < end or offset + units > capacity:
            raise ValueError('Inconsistent resource allocation extents/links')
        largest = max(largest, offset - end)
        used += units
        end = offset + units
        previous, handle = handle, following
    largest = max(largest, capacity - end)
    if data(heap, 0x78) != header:
        raise ValueError('Resource heap changed during snapshot')
    return {'wrapper': hex(wrapper), 'heap': hex(heap),
            'name': header[:32].split(b'\0')[0].decode('ascii', errors='replace'),
            'allocation_count': len(seen), 'unit_bytes': 1 << shift,
            'capacity_bytes': capacity << shift, 'occupied_bytes': used << shift,
            'free_bytes': (capacity - used) << shift,
            'largest_free_extent_bytes': largest << shift,
            'retail_console_budget_verified': False}
