"""Human-authorized Reach Forerunner architecture exception for Forge Gulch."""
import copy
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def reach_architecture(name):
    if not name.startswith('objects\\levels\\forge\\ff_'):
        return False
    leaf = name.rsplit('\\', 1)[-1]
    return not leaf.startswith(('ff_rock_', 'ff_tree_', 'ff_terrain_'))


def sandbox_architecture(name):
    return name.startswith('objects\\levels\\dlc\\sandbox\\') and name.rsplit('\\', 1)[-1].startswith(('sand_', 'stone_'))


def scenery_array(i):
    s, c, b = i.source, i.registry.cache, i.builder
    ss = ET.parse(i.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(i.reference / 'plugins/scnr.xml').getroot()
    name = 'Map Variant Scenery Palette'
    sf, df = field(ss, name), field(ds, name)
    source_root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    target_root = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    source_rows = s.block(source_root + int(sf.get('offset'), 0), 28)
    target_rows = c.block(target_root + int(df.get('offset'), 0), 48)
    selected = [r for r in source_rows if s.u(r+12) != 0xffffffff and reach_architecture(s.name(s.u(r+12)&65535))]
    if len(selected) != 40:
        raise ValueError(f'Review changed Reach architecture inventory: {len(selected)}')
    prefix = copy.deepcopy(df)
    prefix.set('elementSize', '0x1c')
    for node in list(prefix):
        if int(node.get('offset', '0'), 0) >= 28:
            prefix.remove(node)
    converter = MetadataConverter(s, b, i.source_strings, i.target_strings, i.import_tag)
    payload = bytearray()
    imported, retained, removed, labels = [], [], [], {}
    for r in selected:
        tagname = s.name(s.u(r+12)&65535)
        print('Reach scenery: ' + tagname, flush=True)
        payload.extend(converter.convert(r, sf, prefix, 'scnr:/'+name)+bytes(20))
        labels[s.u(r+16)] = struct.unpack_from('>I',payload,len(payload)-48+16)[0]
        imported.append(tagname)
    for r in target_rows:
        datum = c.u(r+12)
        tagname = c.name(datum&65535) if datum != 0xffffffff else ''
        if sandbox_architecture(tagname):
            removed.append(tagname)
        elif not reach_architecture(tagname):
            payload.extend(c.data[r:r+48])
            retained.append(tagname)
    from forge_scenery_labels import stage_labels
    stage_labels(s,i.registry,labels)
    i.reach_scenery_report = dict(imported=imported, retained_stock_utilities=retained,
                                  removed_sandbox_architecture=removed,
                                  prices_limits='Authored Reach entries; existing native total Forge budget unchanged')
    return len(payload)//48, bytes(payload)


def stage_scenery(i):
    ds = ET.parse(i.reference / 'plugins/scnr.xml').getroot()
    array = scenery_array(i)
    stage(i.builder, {'arrays': {'Map Variant Scenery Palette': array}, 'unresolved': []}, ds)
    return i.reach_scenery_report
