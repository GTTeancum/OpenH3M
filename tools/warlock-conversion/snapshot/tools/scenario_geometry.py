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
    if len(rows) != 1 or len(target_rows) != 1:
        raise ValueError('Geometry assembly currently requires one source and target BSP')
    bsp, _, bsp_report = import_bsp(i, terrain, water)
    geometry = next(r for r in bsp_report['resources'] if r['field'] == '[zone] Asset Datum 2')
    lightmap, _, lighting_report = import_lightmap(i, int(geometry['datum'], 16))
    converter = MetadataConverter(s, b, i.source_strings, i.target_strings, i.import_tag)
    payload = converter.convert(rows[0], sf, df, 'scnr:/Structure BSPs[0]')
    # Publish scenario references only after both dependency graphs succeed.
    stage(b, {'arrays': {'Structure BSPs': (1, payload)}, 'unresolved': []}, ds)
    at = target_root - c.start + c.base + int(field(ds, 'Lightmaps').get('offset'), 0)
    b.meta[at - b.base:at - b.base + 16] = lightmap[0].encode('ascii') + bytes(8) + struct.pack('>I', lightmap[1])
    i.converted_bsps = [bsp[1]]
    return {'bsp': bsp_report, 'lightmap': lighting_report}
