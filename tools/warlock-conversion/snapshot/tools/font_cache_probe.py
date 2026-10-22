"""Read-only snapshot of the retail font cache, mapped from original XEX code.

82201C50 inserts a character at TLS+F4, using heap+70/table+44 nodes,
node+8 shifted by heap+3C into the cache's pixel arena. 822C2058 walks
the same 24-byte LRU nodes through +0C; no Halo Online offsets are assumed.
"""
import hashlib
import struct


def snapshot(read, memory, r13, cache_address=None):
    def data(address, size):
        # TLS and cache allocations may be in the guest user-virtual heap,
        # below the XEX/physical ranges. Null/low addresses remain rejected.
        if not 0x10000 <= address < 0xe0000000 or size < 0 or size > 65536 or address+size > 0xe0000000:
            raise ValueError(f'Font probe read outside bounded guest range: {address:#x}+{size:#x}')
        return read(memory + address, size)

    def word(address):
        return struct.unpack('>I', data(address, 4))[0]

    cache = cache_address if cache_address is not None else word(word(r13) + 0xf4)
    header = data(cache, 20)
    frame, _, hash_table, heap, pixels = struct.unpack('>5I', header)
    heap_header = data(heap, 0x74)
    shift = word(heap + 0x3c)
    if shift > 16:
        raise ValueError('Unexpected font heap allocation unit')
    table = word(heap + 0x70)
    nodes = word(table + 0x44)
    handle = word(heap + 0x48)
    visited, characters = set(), []
    while handle != 0xffffffff:
        if handle in visited or len(visited) >= 1600:
            raise ValueError('Cyclic or unexpectedly large font cache')
        visited.add(handle)
        node = data(nodes + (handle & 65535) * 24, 24)
        salt, units, offset, following, previous, owner = struct.unpack('>6I', node)
        address = pixels + (offset << shift)
        record = data(address, 24)
        key, touched, hardware = struct.unpack_from('>3I', record)
        metrics = struct.unpack_from('>6H', record, 12)
        packed_size = metrics[1]
        if (units << shift) < 24 + packed_size:
            raise ValueError('Character pixels exceed allocation')
        payload = data(address + 24, packed_size)
        hardware_record = None
        if hardware != 0xffffffff:
            if hardware >= 1024:
                raise ValueError('Unexpected font hardware block index')
            # 82201DF0..82201E08 indexes 20-byte records at this address.
            hardware_record = data(0x827dc960 + hardware * 20, 20).hex()
        characters.append({'key': hex(key), 'codepoint': key & 65535,
                           'font': key >> 16, 'handle': hex(handle), 'hardware': hex(hardware),
                           'last_touched': touched, 'metrics': metrics,
                           'hardware_record': hardware_record,
                           'packed_sha256': hashlib.sha256(payload).hexdigest(),
                           'pixel_nonzero_bytes': sum(v != 0 for v in payload)})
        handle = following
    return {'frame': frame, 'cache': hex(cache), 'heap': hex(heap),
            'heap_header': heap_header.hex(), 'hash_table': hex(hash_table),
            'characters': characters,
            'scope': 'Live read may race updates; compare repeated samples before treating mismatches as corruption'}
