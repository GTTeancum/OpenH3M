"""Use stock player animation graphs with the additional vehicle seat modes."""
import struct
import xml.etree.ElementTree as ET
from cache_reader import Cache


def add_shade_mode(i, name, address, schema):
    """Use retail graph inheritance for Guardian's stock Shade seat mode."""
    b = i.builder
    key = ('jmad', name)
    path, index = next((p, n) for p, n in i.native_assets.candidates[key] if p.stem == 'guardian')
    saved = i.resolved[key]
    donor = Cache(path)
    try:
        _, handle = i.native_assets.import_from(donor, donor.tags[index]['salt'] << 16 | index, force=True)
    finally:
        donor.close()
        i.resolved[key] = saved
    graph = struct.unpack_from('>I', i.registry.tags, (handle & 65535) * 8 + 4)[0]
    def block(at, stride):
        count, ptr = struct.unpack('>II', b.read(at, 8))
        return [ptr + n * stride for n in range(count)]
    local_nodes = [struct.unpack('>I', b.read(r, 4))[0] for r in block(address + 0x14, 32)]
    donor_nodes = [struct.unpack('>I', b.read(r, 4))[0] for r in block(graph + 0x14, 32)]
    if set(donor_nodes) != set(local_nodes):
        raise ValueError('Shade donor skeleton differs from the native player')
    inherited = block(address + 0x80, 48)
    entry = bytearray(48)
    struct.pack_into('>4sIII', entry, 0, b'jmad', 0, 0, handle)
    mapping = b''.join(struct.pack('>h', local_nodes.index(n)) for n in donor_nodes)
    flags = b''.join(struct.pack('>I', (1 << min(32, len(donor_nodes)-n))-1) for n in range(0,len(donor_nodes),32))
    struct.pack_into('>III', entry, 16, len(donor_nodes), b.alloc(mapping), 0)
    struct.pack_into('>III', entry, 28, len(flags)//4, b.alloc(flags), 0)
    struct.pack_into('>I', entry, 44, 2)  # Inherit for use on player.
    entries = b''.join(b.read(r,48) for r in inherited) + entry
    struct.pack_into('>III', b.meta, address-b.base+0x80, len(inherited)+1, b.alloc(entries), 0)
    mode_schema = next(f for f in schema if f.get('name') == 'Modes')
    def copy_mode(at, node, size):
        data = bytearray(b.read(at,size))
        for f in node:
            if 'offset' not in f.attrib: continue
            offset = int(f.get('offset'),0)
            if f.tag.lower() == 'tagblock':
                stride = int(f.get('elementSize'),0)
                rows = block(at+offset,stride)
                payload = b''.join(copy_mode(r,f,stride) for r in rows)
                struct.pack_into('>III',data,offset,len(rows),b.alloc(payload) if payload else 0,0)
            elif f.get('name') == 'Graph Index':
                if struct.unpack_from('>h',data,offset)[0] != -1:
                    raise ValueError('Shade mode unexpectedly references another graph')
                struct.pack_into('>h',data,offset,len(inherited))
        return bytes(data)
    shade = next(r for r in block(graph+0x5c,40)
                 if i.target_strings.text(struct.unpack('>I',b.read(r,4))[0]) == 'shade_d')
    modes = [b.read(r,40) for r in block(address+0x5c,40)] + [copy_mode(shade,mode_schema,40)]
    modes.sort(key=lambda r: struct.unpack_from('>I',r)[0])
    struct.pack_into('>III',b.meta,address-b.base+0x5c,len(modes),b.alloc(b''.join(modes)),0)
    return handle


def stage_player_animations(i):
    c, s, b = i.registry.cache, i.source, i.builder
    schema = ET.parse(i.reference / 'plugins/jmad.xml').getroot()
    size = int(schema.get('baseSize'), 0)
    result = []
    for name in (r'objects\characters\masterchief\masterchief', r'objects\characters\elite\elite'):
        old = next(((index, tag) for index, tag in c.tags.items()
                    if tag['group'] == 'jmad' and c.name(index) == name), None)
        source = next(((index, tag) for index, tag in s.tags.items()
                       if tag['group'] == 'jmad' and s.name(index) == name), None)
        if old is None:
            raise ValueError('Missing player animation graph: ' + name)
        def modes(cache, tag, strings):
            return {strings.text(cache.u(row)) for row in cache.block(tag['offset'] + 0x5c, 40)}
        required = (modes(s, source[1], i.source_strings) if source is not None else
                    {'banshee_d', 'ghost_d', 'warthog_d', 'scorpion_d', 'wraith_d',
                     'hornet_d', 'mongoose_d', 'shade_d'})
        missing = sorted(required - modes(c, old[1], i.target_strings))
        if not missing:
            continue
        _, datum = i.native_assets.import_named(('jmad', name), force=True)
        address = struct.unpack_from('>I', i.registry.tags, (datum & 65535) * 8 + 4)[0]
        count, pointer = struct.unpack('>II', b.read(address + 0x5c, 8))
        imported_modes = {i.target_strings.text(struct.unpack('>I', b.read(pointer + n * 40, 4))[0]) for n in range(count)}
        if 'shade_d' in required - imported_modes:
            add_shade_mode(i, name, address, schema)
        old_address = old[1]['offset'] - c.start + c.base
        # Keep all original player model references valid. The imported graph
        # remains registered as the owner of its relocated native resources.
        b.meta[old_address - b.base:old_address - b.base + size] = b.read(address, size)
        i.registry.superseded_resource_owners = getattr(i.registry, 'superseded_resource_owners', set()) | {old[0]}
        count, pointer = struct.unpack('>II', b.read(address + 0x5c, 8))
        actual = {i.target_strings.text(struct.unpack('>I', b.read(pointer + n * 40, 4))[0]) for n in range(count)}
        result.append({'player': name, 'added_modes': sorted(actual - modes(c, old[1], i.target_strings)),
                       'source_modes_not_in_donor': sorted(required - actual),
                       'graph': hex(datum)})
    return result
