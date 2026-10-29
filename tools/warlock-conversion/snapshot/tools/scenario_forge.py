"""Import source Forge object palettes with authored names, limits and prices."""
import xml.etree.ElementTree as ET
import copy
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def stage_forge(importer):
    try:
        if getattr(importer, 'stock_forge_palette', False):
            from forge_world import stage_stock_palette
            return stage_stock_palette(importer)
        s, b = importer.source, importer.builder
        ss = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
        ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
        root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
        converter = MetadataConverter(s, b, importer.source_strings,
                                      importer.target_strings, importer.import_tag)
        arrays = {}
        for category in ('Vehicle', 'Weapon', 'Equipment', 'Scenery', 'Teleporter', 'Goal', 'Spawner'):
            name = 'Map Variant ' + category + ' Palette'
            sf, df = field(ss, name), field(ds, name)
            if int(sf.get('elementSize'), 0) != 28 or int(df.get('elementSize'), 0) != 48:
                raise ValueError('Unsupported Forge palette layout')
            prefix = copy.deepcopy(df)
            prefix.set('elementSize', '0x1c')
            for node in list(prefix):
                if int(node.get('offset', '0'), 0) >= 28:
                    prefix.remove(node)
            rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
            object_offset = next(int(n.get('offset'), 0) + 12 for n in sf if n.tag.lower() == 'tagref')
            rows = [row for row in rows
                    if s.u(row + object_offset) == 0xffffffff or (s.tags[s.u(row + object_offset) & 65535]['group'],
                        s.name(s.u(row + object_offset) & 65535))
                    not in getattr(importer, 'omitted_assets', ())]
            print(f'forge {category}: {len(rows)} entries', flush=True)
            # Retail's five trailing runtime/editor words are zero in all
            # original Lockout palettes; MCC does not serialize these words.
            payload = b''.join(converter.convert(row, sf, prefix, f'scnr:/{name}[{index}]') + bytes(20)
                               for index, row in enumerate(rows))
            arrays[name] = len(rows), payload
        stage(b, {'arrays': arrays, 'unresolved': []}, ds)
        return {name: count for name, (count, _) in arrays.items()}
    except Exception:
        importer.failed = True
        raise
