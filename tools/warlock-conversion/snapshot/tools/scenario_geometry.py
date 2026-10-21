"""Stage source-built BSP and lighting, then bind them to the retail scenario."""
import struct
import xml.etree.ElementTree as ET
from bsp_importer import import_bsp
from lightmap_importer import import_lightmap
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def stage_geometry(importer, terrain, water):
    try:
        return _stage(importer, terrain, water)
    except Exception:
        importer.failed = True
        raise


def _stage(i, terrain, water):
    s, c, b = i.source, i.registry.cache, i.builder
    ss = ET.parse(i.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(i.reference / 'plugins/scnr.xml').getroot()
    source_root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    target_root = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    sf, df = field(ss, 'Structure BSPs'), field(ds, 'Structure BSPs')
    rows = s.block(source_root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
    target_rows = c.block(target_root + int(df.get('offset'), 0), int(df.get('elementSize'), 0))
    if not rows or len(rows) > 32 or not target_rows:
        raise ValueError('Invalid source or target BSP bindings')
    bsps, reports, geometry_resources, bsp_addresses = [], [], [], []
    for index in range(len(rows)):
        bsp, bsp_address, report = import_bsp(i, terrain, water, index)
        bsp_addresses.append(bsp_address)
        geometry = next(r for r in report['resources'] if r['field'] == '[zone] Asset Datum 2')
        bsps.append(bsp[1])
        reports.append(report)
        geometry_resources.append(int(geometry['datum'], 16))
    lightmap, lightmap_address, lighting_report = import_lightmap(i, geometry_resources)
    lighting_count, lighting_pointer = struct.unpack_from('>II', b.meta, lightmap_address - b.base + 4)
    if lighting_count != len(bsp_addresses):
        raise ValueError('Visibility binding BSP count mismatch')
    for index, bsp_address in enumerate(bsp_addresses):
        target = bsp_address - b.base
        lighting = lighting_pointer - b.base + index * 436
        mesh_count = struct.unpack_from('>I', b.meta, target + 0x2e4)[0]
        lighting_meshes = struct.unpack_from('>I', b.meta, lighting + 0x134)[0]
        tree_count = struct.unpack_from('>I', b.meta, lighting + 0x170)[0]
        if mesh_count != lighting_meshes or tree_count != mesh_count:
            raise ValueError('BSP visibility trees do not match rebuilt geometry')
        if not struct.unpack_from('>I', b.meta, target + 0x320)[0]:
            # MCC omits this BSP copy. Original Sandbox, Last Resort, Valhalla,
            # Avalanche and Guardian serialize identical trees in both places.
            # Share the converted lighting allocation instead of duplicating it.
            b.meta[target + 0x320:target + 0x32c] = b.meta[lighting + 0x170:lighting + 0x17c]
            reports[index]['shared_visibility_tree_count'] = tree_count
    converter = MetadataConverter(s, b, i.source_strings, i.target_strings, i.import_tag)
    payload = b''.join(converter.convert(row, sf, df, f'scnr:/Structure BSPs[{index}]')
                       for index, row in enumerate(rows))
    # Publish scenario references only after both dependency graphs succeed.
    stage(b, {'arrays': {'Structure BSPs': (len(rows), payload)}, 'unresolved': []}, ds)
    at = target_root - c.start + c.base + int(field(ds, 'Lightmaps').get('offset'), 0)
    b.meta[at - b.base:at - b.base + 16] = lightmap[0].encode('ascii') + bytes(8) + struct.pack('>I', lightmap[1])
    i.converted_bsps = bsps
    return {'bsp': reports[0], 'bsps': reports, 'lightmap': lighting_report}
