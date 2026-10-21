"""Replace map-specific visibility, audio and inactive stock script state."""
import copy
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter, SCALARS
from scenario_placements import fields, translate_enum, translate_flags


EMPTY_BLOCKS = ('Scripts', 'Globals', 'Script References', 'Machines', 'Machine Palette',
                'Scenario Kill Triggers',
                'Scenario Safe Zone Triggers')


def stage_runtime(importer):
    try:
        return _stage(importer)
    except Exception:
        importer.failed = True
        raise


def _stage(i):
    s, c, b = i.source, i.registry.cache, i.builder
    ss = ET.parse(i.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(i.reference / 'plugins/scnr.xml').getroot()
    root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    target = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    converter = MetadataConverter(s, b, i.source_strings, i.target_strings, i.import_tag)
    arrays = {}
    for name in EMPTY_BLOCKS:
        sf = field(ss, name)
        if s.u(root + int(sf.get('offset'), 0)):
            raise ValueError(f'Active source {name} requires a dedicated conversion')
        arrays[name] = (0, b'')
    expressions = field(ss, 'Script Expressions')
    stride = int(expressions.get('elementSize'), 0)
    rows = s.block(root + int(expressions.get('offset'), 0), stride)
    # Unallocated expression slots have a zero salt followed by MCC heap fill.
    # They are capacity, not executable script nodes; no live roots exist above.
    if any(bytes(s.data[r:r + stride]) != bytes(2) + b'\xba' * (stride - 2) for r in rows):
        raise ValueError('Source contains populated script expression slots')
    arrays['Script Expressions'] = (0, b'')
    for name in ('Trigger Volumes', 'Soft Ceilings', 'Zone Set Potentially Visible Sets', 'Zone Set Audibility', 'Zone Sets', 'Scripting Data', 'AI User Hint Data', 'Zone Debugger', 'Soft Surfaces', 'Editor Folders'):
        sf, df = copy.deepcopy(field(ss, name)), field(ds, name)
        rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        if name == 'Zone Sets':
            if any(s.unpack('HH', r + 36) != (65535, 0) for r in rows):
                raise ValueError('Active MCC zone lighting override requires conversion')
            for node in list(sf):
                if node.get('offset') and int(node.get('offset'), 0) >= 36:
                    sf.remove(node)
        payload = b''.join(converter.convert(r, sf, df, 'scnr:/' + name) for r in rows)
        arrays[name] = len(rows), payload
    # Unused editor palettes have no runtime consumers in this multiplayer map.
    for palette, consumers in (('Biped Palette', ('Bipeds',)), ('Character Palette', ('Squads',)),
                               ('Flock Palette', ('Flocks',)), ('Creatures Palette', ('Flocks',))):
        if all(not s.u(root + int(field(ss, name).get('offset'), 0)) for name in consumers):
            if palette == 'Creatures Palette' and s.u(root + int(field(ss, 'Creatures Block').get('offset'), 0)):
                raise ValueError('Active creature placements require conversion')
            arrays[palette] = (0, b'')
    # Empty source arrays must not inherit unrelated Lockout editor/runtime data.
    source_fields, target_fields = fields(ss), fields(ds)
    for key, sf in source_fields.items():
        if sf.tag == 'tagblock' and key in target_fields and not s.u(root + int(sf.get('offset'), 0)):
            arrays[sf.get('name')] = (0, b'')
    stage(b, {'arrays': arrays, 'unresolved': []}, ds)
    address = target - c.start + c.base
    # Keep Blackout's menu/network slot identity; copy authored budget, north,
    # flags and object salts instead of inheriting the stock map's values.
    for key, df in target_fields.items():
        name = key[0]
        if key not in source_fields or df.tag not in SCALARS or name in ('Unknown', 'Map ID', 'Campaign ID'):
            continue
        sf = source_fields[key]
        values = s.unpack(SCALARS[sf.tag], root + int(sf.get('offset'), 0))
        if (getattr(i, 'stock_forge_palette', False) and name == 'Flags'
                and sf.tag.startswith('flags')):
            # MCC's Eldorado object-light sampling has no retail flag.
            # Use native H3 probe sampling; geometry/light probes remain intact.
            values = (values[0] & ~(1 << 7),)
        if df.tag.startswith('flags'):
            values = (translate_flags(values[0], sf, df),)
        elif df.tag.startswith('enum'):
            values = (translate_enum(values[0], sf, df),)
        payload = struct.pack('>' + SCALARS[df.tag], *values)
        at = address - b.base + int(df.get('offset'), 0)
        b.meta[at:at + len(payload)] = payload
    # With no scripts/globals/live expressions, the source string allocation is
    # unused. Remove stock strings and editor data without copying heap slack.
    for name in ('Script Strings', 'Editor Scenario Data'):
        if name == 'Editor Scenario Data' and s.u(root + int(field(ss, name).get('offset'), 0)):
            raise ValueError('Nonempty scenario editor data is unsupported')
        address = target - c.start + c.base + int(field(ds, name).get('offset'), 0)
        b.meta[address - b.base:address - b.base + 20] = bytes(20)
    return {name: count for name, (count, _) in arrays.items()}
