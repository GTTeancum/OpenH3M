"""Expand equivalent single-BSP resource zone sets without importing MCC IDs."""
import struct
import xml.etree.ElementTree as ET
from tag_metadata import MetadataConverter


def stage_residency(importer):
    s, c, b = importer.source, importer.registry.cache, importer.builder
    schemas = [ET.parse(importer.reference / kind / 'zone.xml').getroot()
               for kind in ('mcc', 'plugins')]
    roots = [next(t['offset'] for t in cache.tags.values() if t['group'] == 'zone')
             for cache in (s, c)]
    usage_name, manifest_name = 'Zone Set Zone Usage', 'Zone Only Zone Set Manifests'
    fields = [{n.get('name'): n for n in schema if n.tag == 'tagblock'} for schema in schemas]

    def rows(cache, root, field):
        return cache.block(root + int(field.get('offset'), 0), int(field.get('elementSize'), 0))

    converted = getattr(importer, 'converted_bsps', None)
    if converted:
        field = fields[1]['BSP References']
        if len(rows(c, roots[1], field)) != len(converted):
            raise ValueError('Resource BSP reference count differs from converted geometry')
        payload = b''.join(struct.pack('>4s8xI', b'sbsp', datum) for datum in converted)
        b.put(importer.registry.address(roots[1] + int(field.get('offset'), 0)),
              'III', len(converted), b.alloc(payload), 0)
    source_usage = rows(s, roots[0], fields[0][usage_name])
    native_usage = rows(c, roots[1], fields[1][usage_name])
    if len(source_usage) == len(native_usage):
        return {'zone_sets': len(source_usage), 'expanded': False, 'bsp_references_remapped': bool(converted)}
    if len(native_usage) != 1 or not source_usage:
        raise ValueError('Resource zone expansion requires a single native zone set')
    # This path is valid only when each source zone uses exactly the same
    # BSP/designer/cinematic masks as the native seed. Names may differ.
    expected = c.unpack('8I', native_usage[0] + 4)
    if any(s.unpack('8I', row + 4) != expected for row in source_usage):
        raise ValueError('Source resource zones have different residency masks')
    sf, df = fields[0][manifest_name], fields[1][manifest_name]
    source_manifests = rows(s, roots[0], sf)
    native_manifests = rows(c, roots[1], df)
    if len(source_manifests) != len(source_usage) or len(native_manifests) != 1:
        raise ValueError('Resource zone manifest count differs from zone usage')
    # Compare source manifests with pointers normalized to their actual data.
    def contents(row):
        record = bytearray(s.data[row:row + int(sf.get('elementSize'), 0)])
        blocks = []
        for field in sf:
            if field.tag != 'tagblock':
                continue
            offset, stride = int(field.get('offset'), 0), int(field.get('elementSize'), 0)
            blocks.append(b''.join(s.data[p:p + stride] for p in s.block(row + offset, stride)))
            record[offset + 4:offset + 12] = bytes(8)
        return bytes(record), blocks
    first = contents(source_manifests[0])
    if any(contents(row) != first for row in source_manifests[1:]):
        raise ValueError('Source zone manifests differ; independent remapping required')
    converter = MetadataConverter(s, b, importer.source_strings, importer.target_strings, importer.import_tag)
    usage = b''.join(converter.convert(row, fields[0][usage_name], fields[1][usage_name],
                                      'zone:/Zone Set Zone Usage') for row in source_usage)
    native = b.read(importer.registry.address(native_manifests[0]), int(df.get('elementSize'), 0))
    for name, payload in ((usage_name, usage), (manifest_name, native * len(source_usage))):
        address = importer.registry.address(roots[1] + int(fields[1][name].get('offset'), 0))
        b.put(address, 'III', len(source_usage), b.alloc(payload), 0)
    return {'zone_sets': len(source_usage), 'expanded': True, 'equivalent_source_manifests': True,
            'bsp_references_remapped': bool(converted)}
