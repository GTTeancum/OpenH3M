"""Update accepted BSP material slots without changing geometry or physics data."""
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field


def stage_bsp_materials(importer, terrain=None):
    s, c, b = importer.source, importer.registry.cache, importer.builder
    def active_bsps(cache, folder):
        schema = ET.parse(importer.reference / folder / 'scnr.xml').getroot()
        block = field(schema, 'Structure BSPs')
        root = next(tag['offset'] for tag in cache.tags.values() if tag['group'] == 'scnr')
        result = []
        for row in cache.block(root + int(block.get('offset'), 0), int(block.get('elementSize'), 0)):
            datum = cache.u(row + 12)
            tag = cache.tags.get(datum & 65535)
            if tag is None or tag['salt'] != datum >> 16 or tag['group'] != 'sbsp':
                raise ValueError('Invalid scenario BSP binding')
            result.append(tag)
        return result
    source_bsps = active_bsps(s, 'mcc')
    target_bsps = active_bsps(c, 'plugins')
    if len(source_bsps) != 1 or len(target_bsps) != 1:
        raise ValueError('BSP material checkpoint requires exactly one source and target BSP')
    ss = ET.parse(importer.reference / 'mcc/sbsp.xml').getroot()
    ds = ET.parse(importer.reference / 'plugins/sbsp.xml').getroot()
    sf, df = field(ss, 'Materials'), field(ds, 'Materials')
    source_rows = s.block(source_bsps[0]['offset'] + int(sf.get('offset'), 0),
                          int(sf.get('elementSize'), 0))
    target_rows = c.block(target_bsps[0]['offset'] + int(df.get('offset'), 0),
                          int(df.get('elementSize'), 0))
    if len(source_rows) != len(target_rows):
        raise ValueError('BSP material slots differ from accepted geometry')
    updates, report = [], {'converted': [], 'retained_checkpoint': []}
    for slot, (source_row, target_row) in enumerate(zip(source_rows, target_rows)):
        datum = s.u(source_row + 12)
        tag = s.tags.get(datum & 65535)
        if tag is None or tag['salt'] != datum >> 16:
            raise ValueError(f'Invalid source material reference at slot {slot}')
        entry = {'slot': slot, 'source': s.name(datum & 65535), 'group': tag['group']}
        if tag['group'] not in ('rmsh', 'rmfl') and not (tag['group'] in ('rmtr', 'rmhg') and terrain is not None):
            # Explicitly retain accepted approximations until specialized
            # terrain, hologram and water importers are integrated.
            existing = c.u(target_row + 12)
            old = c.tags.get(existing & 65535)
            if old is None or old['salt'] != existing >> 16:
                raise ValueError(f'Invalid retained material reference at slot {slot}')
            entry.update(reason='Specialized material converter pending',
                         retained_group=old['group'], retained_datum=hex(existing))
            report['retained_checkpoint'].append(entry)
            continue
        group, target = terrain.shader(datum) if tag['group'] in ('rmtr', 'rmhg') else importer.materials.shader(datum)
        updates.append((target_row - c.start + c.base,
                        group.encode('ascii') + bytes(8) + struct.pack('>I', target)))
        entry['target_datum'] = hex(target)
        report['converted'].append(entry)
    # Preserve each material's remaining 20 bytes (physics/properties/breakable
    # indices); the accepted geometry continues to reference the same slot IDs.
    for address, payload in updates:
        b.meta[address - b.base:address - b.base + 16] = payload
    return report
