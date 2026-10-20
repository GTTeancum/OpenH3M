"""Use stock player animation graphs with the additional vehicle seat modes."""
import struct
import xml.etree.ElementTree as ET


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
