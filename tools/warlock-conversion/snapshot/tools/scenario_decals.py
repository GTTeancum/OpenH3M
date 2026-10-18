"""Import every placed decal and stage a compact, fully resolved palette."""
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def stage_decals(importer):
    s = importer.source
    ss = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
    root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    sf, df = field(ss, 'Decals'), field(ds, 'Decals')
    pf, pd = field(ss, 'Decal Palette'), field(ds, 'Decal Palette')
    rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
    palette = s.block(root + int(pf.get('offset'), 0), int(pf.get('elementSize'), 0))
    used = sorted({s.unpack('h', row)[0] for row in rows})
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
    return {'placements': len(rows), 'palette': len(used)}
