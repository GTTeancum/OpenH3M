"""Import source Forge object palettes with authored names, limits and prices."""
from source_schema import load_schema
import xml.etree.ElementTree as ET
import copy
import struct
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter


def without_redundant_dmr(cache, rows, object_offset):
    """The DMR alias must not add a second BR entry with an unsupported label."""
    dmr = ('weap', r'priception\objects\weapons\rifle\dmr\dmr')
    br = ('weap', r'objects\weapons\rifle\battle_rifle\battle_rifle')
    def identity(row):
        datum = cache.u(row + object_offset)
        if datum == 0xffffffff:
            return None
        return cache.tags[datum & 65535]['group'], cache.name(datum & 65535)
    if not any(identity(row) == br for row in rows):
        return rows
    return [row for row in rows if identity(row) != dmr]


def without_empty_entries(cache, rows, object_offset):
    """A null source placeholder is not a Forge object or usable native quota."""
    return [row for row in rows if cache.u(row + object_offset) != 0xffffffff]


def stage_forge(importer):
    try:
        if getattr(importer, 'stock_forge_palette', False):
            from forge_world import stage_stock_palette
            return stage_stock_palette(importer)
        s, b = importer.source, importer.builder
        ss = load_schema(importer.source, 'scnr', importer.reference)
        ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
        root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
        scenario_name = next(s.name(k) for k, t in s.tags.items() if t['group'] == 'scnr')
        if scenario_name == r'levels\multi\s3d_powerhouse\s3d_powerhouse':
            categories = ('Vehicle', 'Weapon', 'Equipment', 'Scenery', 'Teleporter', 'Goal', 'Spawner')
            counts = [s.u(root + int(field(ss, 'Map Variant ' + cat + ' Palette').get('offset'), 0))
                      for cat in categories]
            if not any(counts):
                # This source has no scenario Forge palette. Preserve the stock
                # assembly basis's native objects, prices, limits and budget.
                # Never replace a future authored, populated source palette.
                from forge_world import stage_stock_palette
                print('forge: empty Powerhouse source uses stock assembly palette', flush=True)
                return stage_stock_palette(importer)
        converter = MetadataConverter(s, b, importer.source_strings,
                                      importer.target_strings, importer.import_tag)
        arrays = {}
        custom_labels = {}
        native_labels=None
        if (getattr(importer,'battle_canyon_rebuilt',False) or
                scenario_name == r'levels\multi\resuscitation\resuscitation'):
            from forge_scenery_labels import native_label_ids
            native_labels=native_label_ids(importer.registry.cache)
        for category in ('Vehicle', 'Weapon', 'Equipment', 'Scenery', 'Teleporter', 'Goal', 'Spawner'):
            name = 'Map Variant ' + category + ' Palette'
            sf, df = field(ss, name), field(ds, name)
            source_stride = int(sf.get('elementSize'), 0)
            if source_stride not in (28, 48) or int(df.get('elementSize'), 0) != 48:
                raise ValueError('Unsupported Forge palette layout')
            prefix = copy.deepcopy(df)
            prefix.set('elementSize', '0x1c')
            for node in list(prefix):
                if int(node.get('offset', '0'), 0) >= 28:
                    prefix.remove(node)
            rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
            object_offset = next(int(n.get('offset'), 0) + 12 for n in sf if n.tag.lower() == 'tagref')
            for index, row in enumerate(rows):
                if s.u(row + object_offset) == 0xffffffff:
                    # A placeholder may be skipped only after the legacy
                    # runtime/editor words pass their normal validation. Do
                    # not let a null tag hide an unsupported record layout.
                    if source_stride == 48:
                        converter.convert(row, sf, df, f'scnr:/{name}[{index}]')
                    if not hasattr(importer, 'empty_forge_placeholders'):
                        importer.empty_forge_placeholders = []
                    importer.empty_forge_placeholders.append(dict(category=category, index=index,
                        label=importer.source_strings.text(s.u(row + 16)),
                        reason='Source entry has no object datum; not a playable object'))
            rows = without_empty_entries(s, rows, object_offset)
            rows = [row for row in rows
                    if (s.tags[s.u(row + object_offset) & 65535]['group'],
                        s.name(s.u(row + object_offset) & 65535))
                    not in getattr(importer, 'omitted_assets', ())]
            if category == 'Weapon':
                rows = without_redundant_dmr(s, rows, object_offset)
            print(f'forge {category}: {len(rows)} entries', flush=True)
            # Newer MCC omits five runtime/editor words. Older MCC retains
            # them; normal metadata conversion verifies their values.
            converted=[]
            for index,row in enumerate(rows):
                if source_stride == 48:
                    item=converter.convert(row,sf,df,f'scnr:/{name}[{index}]')
                else:
                    item=converter.convert(row,sf,prefix,f'scnr:/{name}[{index}]')+bytes(20)
                source_label=s.u(row+16)
                target_label=struct.unpack_from('>I',item,16)[0]
                if native_labels is not None and target_label not in native_labels:
                    custom_labels[source_label]=target_label
                converted.append(item)
            payload=b''.join(converted)
            arrays[name] = len(rows), payload
        stage(b, {'arrays': arrays, 'unresolved': []}, ds)
        if custom_labels:
            from forge_scenery_labels import stage_labels
            count=stage_labels(s,importer.registry,custom_labels)
            importer.added.append(dict(group='unic',source='Authored English Forge display labels',
                labels_added=count,source_string_ids=sorted(custom_labels),
                policy='Existing native sandbox UI labels retained; missing labels copied from source English or explicitly reported owner-approved derived names',
                label_publication=importer.registry.forge_label_publication))
        return {name: count for name, (count, _) in arrays.items()}
    except Exception:
        importer.failed = True
        raise
