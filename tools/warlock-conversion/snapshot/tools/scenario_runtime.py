"""Replace map-specific visibility, audio and inactive stock script state."""
from source_schema import load_schema
import copy
import struct
import xml.etree.ElementTree as ET
from assemble_scenario import field, stage
from tag_metadata import MetadataConverter, SCALARS
from scenario_placements import fields, translate_enum, translate_flags


EMPTY_BLOCKS = ('Scripts', 'Globals', 'Script References')


def stage_runtime(importer):
    try:
        return _stage(importer)
    except Exception:
        importer.failed = True
        raise


def _stage(i):
    s, c, b = i.source, i.registry.cache, i.builder
    ss = load_schema(i.source, 'scnr', i.reference)
    ds = ET.parse(i.reference / 'plugins/scnr.xml').getroot()
    root = next(t['offset'] for t in s.tags.values() if t['group'] == 'scnr')
    target = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    converter = MetadataConverter(s, b, i.source_strings, i.target_strings, i.import_tag)
    arrays, script_strings = {}, b''
    has_scripts = any(s.u(root + int(field(ss, name).get('offset'), 0)) for name in EMPTY_BLOCKS)
    if has_scripts:
        from scenario_scripts import prepare_scripts
        arrays, script_strings = prepare_scripts(i, ss, ds, converter, root)
    else:
        arrays.update({name: (0, b'') for name in EMPTY_BLOCKS})
    expressions = field(ss, 'Script Expressions')
    stride = int(expressions.get('elementSize'), 0)
    rows = s.block(root + int(expressions.get('offset'), 0), stride)
    # Workshop tools use zero salt followed by MCC heap fill; official H3EK
    # also emits wholly zero-filled capacity (512 slots in the fresh build).
    # They are capacity, not executable script nodes; no live roots exist above.
    empty_slots = {bytes(stride), bytes(2) + b'\xba' * (stride - 2)}
    if not has_scripts and any(bytes(s.data[r:r + stride]) not in empty_slots for r in rows):
        raise ValueError('Source contains populated script expression slots')
    if not has_scripts:
        arrays['Script Expressions'] = (0, b'')
    trigger_count = s.u(root + int(field(ss, 'Trigger Volumes').get('offset'), 0))
    for name in ('Scenario Resources', 'Trigger Volumes', 'Scenario Kill Triggers', 'Scenario Safe Zone Triggers', 'Soft Ceilings', 'Zone Set Potentially Visible Sets', 'Zone Set Audibility', 'Zone Sets', 'Scripting Data', 'AI User Hint Data', 'Zone Debugger', 'Soft Surfaces', 'Editor Folders', 'Device Groups', 'Cutscene Flags', 'Cutscene Camera Points'):
        sf, df = copy.deepcopy(field(ss, name)), field(ds, name)
        rows = s.block(root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        if name in ('Scenario Kill Triggers', 'Scenario Safe Zone Triggers'):
            # Both formats store signed indices into the unchanged trigger array.
            # Preserve authored out-of-bounds behavior, never silently drop it.
            if any(not 0 <= s.unpack('h', row)[0] < trigger_count for row in rows):
                raise ValueError(f'{name} references a missing trigger volume')
        if name == 'Scenario Resources':
            field(sf, 'Split Resources').set('name', 'Resources')
        if name == 'Zone Sets':
            stride = int(sf.get('elementSize'), 0)
            if stride not in (36, 40):
                raise ValueError('Unsupported MCC zone-set layout')
            if stride == 40 and any(s.unpack('HH', r + 36) != (65535, 0) for r in rows):
                raise ValueError('Active MCC zone lighting override requires conversion')
            for node in list(sf):
                if node.get('offset') and int(node.get('offset'), 0) >= 36:
                    sf.remove(node)
        payload = b''.join(converter.convert(r, sf, df, 'scnr:/' + name) for r in rows)
        if name == 'Soft Ceilings' and getattr(i, 'gulch_partition', None):
            if len(rows) != 1 or len(payload) != 12:
                raise ValueError('Gulch expects one scenario soft ceiling')
            # Zero ignore masks: apply to bipeds, vehicles and camera. Runtime
            # flags are recomputed by the original engine on map load.
            payload = bytes(4) + payload[4:]
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
        if name == 'Flags' and sf.tag.startswith('flags'):
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
    # Replace stock script strings with the validated source allocation when
    # scripts exist; otherwise clear it. Editor data remains unsupported.
    for name in ('Script Strings', 'Editor Scenario Data'):
        if name == 'Editor Scenario Data' and s.u(root + int(field(ss, name).get('offset'), 0)):
            raise ValueError('Nonempty scenario editor data is unsupported')
        address = target - c.start + c.base + int(field(ds, name).get('offset'), 0)
        b.meta[address - b.base:address - b.base + 20] = bytes(20)
        if name == 'Script Strings' and script_strings:
            pointer = b.alloc(script_strings)
            b.put(address, 'I', len(script_strings))
            b.put(address + 12, 'I', pointer)
    return {name: count for name, (count, _) in arrays.items()}
