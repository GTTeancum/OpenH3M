"""Read-only snapshot of the retail font cache, mapped from original XEX code.

82201C50 inserts a character at TLS+F4, using heap+70/table+44 nodes,
node+8 shifted by heap+3C into the cache's pixel arena. 822C2058 walks
the same 24-byte LRU nodes through +0C; no Halo Online offsets are assumed.
"""
import hashlib
import struct


def snapshot(read, memory, r13, cache_address=None, include_atlas=False):
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
    atlas = None
    if include_atlas:
        # Original 8246C1E4/8246C234 uses +1C for the D3D texture and +18
        # for bitmap dimensions. 825BA490 reads texture fetch word 1 at +20.
        try:
            bitmap = word(0x827dc538 + 0x18)
            texture = word(0x827dc538 + 0x1c)
            fetch = struct.unpack('>6I', data(texture + 0x1c, 24))
            width, height = struct.unpack('>HH', data(bitmap + 4, 4))
            pitch = ((fetch[0] >> 22) & 511) * 32
            fmt, tiled = fetch[1] & 63, fetch[0] >> 31
            base = 0xa0000000 | (fetch[1] & 0x1ffff000)
            atlas = {'texture': hex(texture), 'fetch': [hex(v) for v in fetch],
                     'width': width, 'height': height, 'pitch_pixels': pitch,
                     'format': fmt, 'tiled': tiled, 'cpu_address': hex(base)}
            if fmt != 15 or tiled or not 0 < width <= pitch <= 4096 or not 0 < height <= 4096:
                raise ValueError('Atlas is not the expected bounded linear 16-bit texture')
            if (width, height) != ((fetch[2] & 8191)+1, ((fetch[2] >> 13) & 8191)+1):
                raise ValueError('Atlas bitmap/fetch dimensions differ')
            for character in characters:
                if character['font'] != 1 or not character['hardware_record']:
                    continue
                raw = bytes.fromhex(character['hardware_record'])
                character['hardware_key_matches'] = struct.unpack_from('>I', raw)[0] == int(character['key'], 16)
                if not character['hardware_key_matches']:
                    continue
                x, y = struct.unpack_from('>HH', raw, 16)
                glyph_width, glyph_height = character['metrics'][2:4]
                if x+glyph_width > width or y+glyph_height > height:
                    raise ValueError('Glyph rectangle outside font atlas')
                raw_pixels = b''.join(data(base+((y+row)*pitch+x)*2, glyph_width*2)
                                      for row in range(glyph_height))
                character['atlas_cpu_sha256'] = hashlib.sha256(raw_pixels).hexdigest()
                character['atlas_cpu_nonzero_bytes'] = sum(v != 0 for v in raw_pixels)
        except (OSError, ValueError) as error:
            atlas = dict(atlas or {}, error=str(error))
    return {'frame': frame, 'cache': hex(cache), 'heap': hex(heap), 'atlas': atlas,
            'heap_header': heap_header.hex(), 'hash_table': hex(hash_table),
            'characters': characters,
            'scope': 'Live read may race updates; compare repeated samples before treating mismatches as corruption'}
