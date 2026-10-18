"""Stage authored sky, atmosphere, acoustics and per-cluster environment data."""
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def stage_environment(importer):
    s, c, b = importer.source, importer.registry.cache, importer.builder
    ss = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
    source_root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    target_root = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    converter = MetadataConverter(s, b, importer.source_strings, importer.target_strings,
                                  importer.import_tag)
    bsp_field = field(ds, 'Structure BSPs')
    bsps = c.block(target_root + int(bsp_field.get('offset'), 0), int(bsp_field.get('elementSize'), 0))
    arrays = {}
    for name in ('Skies', 'Atmosphere', 'Acoustics Palette', 'Scenario Cluster Data',
                 'Camera FX Palette', 'Cubemaps', 'Airprobes'):
        sf, df = field(ss, name), field(ds, name)
        rows = s.block(source_root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        if name == 'Scenario Cluster Data' and len(rows) != len(bsps):
            raise ValueError('Environment BSP count differs from converted geometry')
        payload = bytearray()
        for index, row in enumerate(rows):
            data = bytearray(converter.convert(row, sf, df, f'scnr:/{name}[{index}]'))
            if name == 'Scenario Cluster Data':
                # MCC leaves this reference null. Retail points to the BSP whose
                # geometry was replaced, preserving the corresponding BSP index.
                datum = c.u(bsps[index] + 12)
                if datum == 0xffffffff or c.tags[datum & 65535]['group'] != 'sbsp':
                    raise ValueError('Missing converted retail BSP binding')
                data[:16] = b'sbsp' + bytes(8) + struct.pack('>I', datum)
            payload.extend(data)
        arrays[name] = len(rows), bytes(payload)
    references = []
    for name in ('Sky Parameters', 'Camera Effects', 'Global Screen Effect',
                 'Global Lighting', 'Performance Throttles'):
        sf, df = field(ss, name), field(ds, name)
        datum = s.u(source_root + int(sf.get('offset'), 0) + 12)
        if datum == 0xffffffff:
            reference = b'\xff' * 4 + bytes(8) + b'\xff' * 4
        else:
            group, target = importer.import_tag(datum)
            reference = group.encode('ascii') + bytes(8) + struct.pack('>I', target)
        at = target_root - c.start + c.base + int(df.get('offset'), 0)
        references.append((at, reference))
    stage(b, {'arrays': arrays, 'unresolved': []}, ds)
    for at, reference in references:
        b.meta[at - b.base:at - b.base + 16] = reference
    return {name: count for name, (count, _) in arrays.items()}
