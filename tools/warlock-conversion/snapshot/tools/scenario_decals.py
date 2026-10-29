"""Import every placed decal and stage a compact, fully resolved palette."""
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def verify_runtime_decals(cache, reference):
    """Check the BSP consumer, not only the editor scenario placements."""
    schema = ET.parse(reference / 'plugins/scnr.xml').getroot()
    bsp_schema = ET.parse(reference / 'plugins/sbsp.xml').getroot()
    root = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
    palette_count = cache.u(root + int(field(schema, 'Decal Palette').get('offset'), 0))
    bsp_field = field(schema, 'Structure BSPs')
    verified = 0
    for row in cache.block(root + int(bsp_field.get('offset'), 0), int(bsp_field.get('elementSize'), 0)):
        datum = cache.u(row + 12)
        tag = cache.tags[datum & 65535]
        if tag['group'] != 'sbsp' or tag['salt'] != datum >> 16:
            raise ValueError('Invalid scenario BSP reference')
        runtime_field = field(bsp_schema, 'Runtime Decals')
        for decal in cache.block(tag['offset'] + int(runtime_field.get('offset'), 0), 36):
            index = cache.unpack('h', decal)[0]
            if not 0 <= index < palette_count:
                raise ValueError(f'BSP runtime decal palette index {index} exceeds palette size {palette_count}')
            verified += 1
    return verified


def stage_decals(importer):
    s = importer.source
    ss = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
    root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    sf, df = field(ss, 'Decals'), field(ds, 'Decals')
    pf, pd = field(ss, 'Decal Palette'), field(ds, 'Decal Palette')
    rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
    palette = s.block(root + int(pf.get('offset'), 0), int(pf.get('elementSize'), 0))
    # BSP runtime decals use the same scenario palette. They survive scenario
    # placement conversion and must participate in both dependency collection
    # and index remapping when the palette is compacted.
    b = importer.builder
    bsp_schema = ET.parse(importer.reference / 'plugins/sbsp.xml').getroot()
    runtime_field = int(field(bsp_schema, 'Runtime Decals').get('offset'), 0)
    runtime_rows = []
    for datum in importer.converted_bsps:
        root_address = struct.unpack_from('>I', importer.registry.tags, (datum & 65535) * 8 + 4)[0]
        count, pointer = struct.unpack('>II', b.read(root_address + runtime_field, 8))
        runtime_rows.extend(pointer + index * 36 for index in range(count))
    runtime_indices = [struct.unpack('>h', b.read(row, 2))[0] for row in runtime_rows]
    used = sorted({s.unpack('h', row)[0] for row in rows} | set(runtime_indices))
    if any(index < 0 or index >= len(palette) for index in used):
        raise ValueError('Decal placement references an invalid palette index')
    converter = MetadataConverter(s, importer.builder, importer.source_strings,
                                  importer.target_strings, importer.import_tag)
    # Resolve the whole dependency graph before replacing scenario arrays.
    palette_data = b''.join(converter.convert(palette[index], pf, pd,
                            f'scnr:/Decal Palette[{index}]') for index in used)
    remap = {index: compact for compact, index in enumerate(used)}
    data = bytearray()
    for index, row in enumerate(rows):
        record = bytearray(converter.convert(row, sf, df, f'scnr:/Decals[{index}]'))
        struct.pack_into('>h', record, 0, remap[s.unpack('h', row)[0]])
        data.extend(record)
    stage(importer.builder, {'arrays': {'Decal Palette': (len(used), palette_data),
                                       'Decals': (len(rows), bytes(data))},
                             'unresolved': []}, ds)
    for row, index in zip(runtime_rows, runtime_indices):
        b.put(row, 'h', remap[index])
    return {'placements': len(rows), 'runtime_decals_remapped': len(runtime_rows), 'palette': len(used)}
