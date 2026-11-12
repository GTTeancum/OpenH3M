"""Resolve MCC BSP geometry through scenario lightmap bindings, not tag IDs."""
from source_schema import load_schema
from resource_reader import Resource
from render_resource import convert_render_resource
from water_buffers import rebuild_water_buffers
from string_ids import StringTable


def convert_bsp_geometry(cache, bsp_index=0):
    """Return converted geometry and provenance; does not write or register it."""
    if not cache.mcc:
        raise ValueError('BSP geometry source must be MCC')
    def field(group, name):
        matches = [f for f in load_schema(cache, group)
                   if f.get('name') == name]
        if len(matches) != 1:
            raise ValueError(f'Ambiguous schema field {group}/{name}')
        return int(matches[0].get('offset'), 0)

    def tag(datum, group):
        entry = cache.tags.get(datum & 65535)
        if entry is None or entry['salt'] != datum >> 16 or entry['group'] != group:
            raise ValueError(f'Invalid {group} binding: {datum:#x}')
        return entry['offset']

    scenarios = [t['offset'] for t in cache.tags.values() if t['group'] == 'scnr']
    if len(scenarios) != 1:
        raise ValueError('Expected one scenario')
    scenario = scenarios[0]
    bindings = cache.block(scenario + field('scnr', 'Structure BSPs'), 0x6c)
    if not 0 <= bsp_index < len(bindings):
        raise ValueError('BSP index outside scenario bindings')
    bsp_datum = cache.u(bindings[bsp_index] + 12)
    bsp = tag(bsp_datum, 'sbsp')
    lightmap = tag(cache.u(scenario + field('scnr', 'Lightmaps') + 12), 'sLdT')
    candidates = {}
    for name in ('Per-Pixel Lightmap BSPs', 'Per-Vertex Lightmap BSPs'):
        for row in cache.block(lightmap + field('sLdT', name), 16):
            datum = cache.u(row + 12)
            offset = tag(datum, 'Lbsp')
            if cache.unpack('h', offset + field('Lbsp', 'BSP Reference Index'))[0] == bsp_index:
                candidates[datum] = offset
    if len(candidates) != 1:
        raise ValueError('Expected one lightmap geometry binding for BSP')
    owner, offset = next(iter(candidates.items()))
    resource_datum = cache.u(offset + field('Lbsp', '[zone] Asset Datum'))
    zones = [t['offset'] for t in cache.tags.values() if t['group'] == 'zone']
    if len(zones) != 1:
        raise ValueError('Expected one resource zone')
    rows = cache.block(zones[0] + 100, 64)
    index = resource_datum & 65535
    if index >= len(rows):
        raise ValueError('BSP geometry resource outside zone')
    row = rows[index]
    types = cache.block(zones[0] + 4, 28)
    type_index = cache.data[row + 18]
    type_name = (StringTable(cache).text(cache.u(types[type_index] + 24))
                 if type_index < len(types) else None)
    if (cache.unpack('H', row + 16)[0] != resource_datum >> 16
            or cache.u(row + 12) != owner
            or type_name != 'render_geometry_api_resource_definition'):
        raise ValueError('BSP geometry resource salt, owner or type mismatch')
    source = Resource(cache, resource_datum)
    water = rebuild_water_buffers(cache, bsp, source)
    quarter_stops = getattr(cache, 'powerhouse_ambient_quarter_stops', 0)
    vertex_converter = None
    if quarter_stops:
        from render_buffers import convert_vertices
        from powerhouse_lighting import boost_vertices

        def vertex_converter(payload, count, fmt, stride):
            data, target_stride = convert_vertices(payload, count, fmt, stride)
            if fmt == 6:
                if target_stride != 20:
                    raise ValueError('Unexpected static lighting stride')
                data = boost_vertices(data, quarter_stops)
            return data, target_stride

    converted = convert_render_resource(source, water_buffers=water, vertex_converter=vertex_converter)
    from powerhouse_room_lighting import apply as apply_room_fill
    room_fill = apply_room_fill(cache, bsp, offset, source, converted,
                               getattr(cache, 'powerhouse_room_fill', 0.))
    return converted, {'bsp_index': bsp_index, 'bsp_datum': hex(bsp_datum),
                       'lightmap_datum': hex(owner), 'resource_datum': hex(resource_datum),
                       'reconstructed_water_buffers': len(water),
                       'ambient_quarter_stops': quarter_stops,
                       'powerhouse_room_fill': room_fill}
