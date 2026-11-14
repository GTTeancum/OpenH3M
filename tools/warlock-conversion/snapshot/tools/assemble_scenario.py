"""Prepare retail scenario arrays and stage them only when dependencies resolve.

Unresolved records remain visible in the report. Preparation never writes a map;
stage() refuses partial output so an incomplete scenario cannot be deployed by
mistake. Imported object tags can be supplied by the dependency importer.
"""
from source_schema import load_schema
import struct
from scenario_placements import plan_placements


PLACEMENTS = {'Scenery': ('Scenery Palette', 6), 'Weapons': ('Weapon Palette', 2),
              'Equipment': ('Equipment Palette', 3), 'Crates': ('Crates Palette', 10),
              'Machines': ('Machine Palette', 7), 'Controls': ('Control Palette', 8)}


def field(schema, name):
    return next(x for x in schema if x.get('name') == name)


def prepare(source, target, source_schema, target_schema, imported=None, placements=None, omitted=(), omit_null_effects=False, omit_null_palettes=False, translate_string=None, preserved_null_placements=(), placement_corrections=None):
    placements = placements or PLACEMENTS
    plan = plan_placements(source, target, source_schema, target_schema, imported,
                           [(name, palette) for name, (palette, _) in placements.items()], omitted, omit_null_effects, omit_null_palettes, translate_string, preserved_null_placements, placement_corrections)
    scenario = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    arrays, unresolved, maps = {}, [], {}
    for name, (_, object_type) in placements.items():
        maps[object_type] = {row['source_index']: i for i, row in enumerate(plan[name]['converted'])}
        unresolved.extend(dict(block=name, **item) for item in plan[name]['unresolved'])

    # Keep the name-table indices stable, remapping its placement indices instead.
    names_field = field(source_schema, 'Object Names')
    names_rows = source.block(scenario + int(names_field.get('offset'), 0), 36)
    names = bytearray()
    valid_names = set()
    for index, row in enumerate(names_rows):
        object_type, placement = source.unpack('hh', row + 32)
        mapped = maps.get(object_type, {}).get(placement)
        names.extend(source.data[row:row + 32])
        names.extend(struct.pack('>hh', object_type if mapped is not None else -1,
                                 mapped if mapped is not None else -1))
        if mapped is not None:
            valid_names.add(index)
        elif object_type != -1:
            unresolved.append({'block': 'Object Names', 'index': index,
                               'reason': f'Placement {object_type}:{placement} is not assembled'})
    arrays['Object Names'] = (len(names_rows), bytes(names))

    for name, (palette_name, _) in placements.items():
        rows = plan[name]['converted']
        target_field = field(target_schema, name)
        target_fields = [x for x in target_field if x.get('offset') is not None]
        palette = bytearray()
        palette_indices = {}
        records = bytearray()
        for row in rows:
            datum = row['retail_datum']
            if datum is None:
                # Explicit audited null placement: retain record/index, no tag.
                records.extend(row['record'])
                continue
            if datum not in palette_indices:
                palette_indices[datum] = len(palette) // 48
                tag_group = row['retail_group']
                # Retail palettes have 32 zero padding bytes after the tagref.
                palette.extend(tag_group.encode('ascii') + bytes(8) + struct.pack('>I', datum) + bytes(32))
            record = bytearray(row['record'])
            struct.pack_into('>h', record, 0, palette_indices[datum])
            for f in target_fields:
                offset, fname = int(f.get('offset'), 0), f.get('name')
                if fname in ('Name Index', 'Parent Object Name Index'):
                    index = struct.unpack_from('>h', record, offset)[0]
                    if index != -1 and index not in valid_names:
                        unresolved.append({'block': name, 'index': row['source_index'],
                                           'reason': f'{fname} {index} has no assembled object'})
                elif fname == 'Parent Object Index':
                    index = struct.unpack_from('>h', record, offset)[0]
                    if index != -1:
                        unresolved.append({'block': name, 'index': row['source_index'],
                                           'reason': 'Non-null multiplayer parent needs global object-index mapping'})
            records.extend(record)
        arrays[name] = (len(rows), bytes(records))
        arrays[palette_name] = (len(palette) // 48, bytes(palette))
    return {'arrays': arrays, 'unresolved': unresolved,
            'source_counts': {k: v['source_count'] for k, v in plan.items()}}


def audited_dune_null_placements(source, schema):
    """Retain six native-valid indexless crate records, never omit placements."""
    import hashlib
    scenarios = [(source.name(k), t['offset']) for k, t in source.tags.items() if t['group'] == 'scnr']
    if len(scenarios) != 1 or scenarios[0][0] != r'levels\multi\dune\dune':
        return set()
    f = field(schema, 'Crates')
    if int(f.get('elementSize'), 0) != 176:
        raise ValueError('Dune crate placeholder layout changed')
    rows = source.block(scenarios[0][1] + int(f.get('offset'), 0), 176)
    expected = {37: '33d57c9d680114449d95f8a1b7b24e54fb9d715ba82b4f1fdacba4c3807978ca', 38: 'a11dfa50723b8fe3e8418ff1c92140326246e10c5c17ad5827c2cbe48c870160', 39: '0ff7fca9b0d476759e9ad4dc09c0ae40357edbfc0b3bed89bbdabfb33ea890ad', 40: '369188d437506e5adc2580d67d90aded4f761dfb30a69684a7e988646b30fbaa', 41: 'a7f539a21d6a1da42f82edab8160861852eb4bcaf29ca82dd093e54b2115a395', 42: 'e83902a225f24a1df26f9b8b8728cf3cc3ed5643f1e815f44d8eb9e3cf0b8f79'}
    actual = {n for n, row in enumerate(rows) if source.unpack('h', row)[0] == -1}
    if actual != set(expected):
        raise ValueError('Dune null crate placement set changed')
    for index, digest in expected.items():
        row = rows[index]
        if hashlib.sha256(source.data[row:row + 176]).hexdigest() != digest:
            raise ValueError('Dune null crate placement changed; re-audit required')
    return {('Crates', index) for index in expected}


def stage(builder, prepared, target_schema):
    if prepared['unresolved']:
        raise ValueError(f"Scenario has {len(prepared['unresolved'])} unresolved dependencies/references: "
                         f"{prepared['unresolved'][:3]}")
    cache = builder.cache
    scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
    scenario_address = scenario - cache.start + cache.base
    # Validate every array and reserve capacity before changing the builder.
    required = 0
    for name, (count, payload) in prepared['arrays'].items():
        stride = int(field(target_schema, name).get('elementSize'), 0)
        if len(payload) != count * stride:
            raise ValueError(f'{name}: wrong payload size')
        required += len(payload) + 15
    if builder.used + required > builder.reserve:
        raise ValueError('Insufficient metadata reserve for scenario arrays')
    for name, (count, payload) in prepared['arrays'].items():
        pointer = builder.alloc(payload) if payload else 0
        offset = int(field(target_schema, name).get('offset'), 0)
        builder.put(scenario_address + offset, 'III', count, pointer, 0)


def stage_primary_objects(importer, include_sound_scenery=False, include_effect_scenery=False):
    """Import every used primary palette entry and stage all four object arrays.

    Caller owns the scratch builder and finalization. This does not replace the
    remaining scenario/environment conversion or publish a partial map.
    """
    import xml.etree.ElementTree as ET
    from object_variants import resolve_variants
    source, target = importer.source, importer.registry.cache
    placements = dict(PLACEMENTS)
    if getattr(importer, 'chiron', False) or getattr(importer,'desolation',False):
        placements['Bipeds'] = ('Biped Palette', 0)
    if getattr(importer, 'slot', 'lockout') in ('zanzibar', 'chillout', 'sandbox'):
        placements['Vehicles'] = ('Vehicle Palette', 1)
    if include_sound_scenery:
        placements['Sound Scenery'] = ('Sound Scenery Palette', 9)
    if include_effect_scenery:
        placements['Effect Scenery'] = ('Effect Scenery Palette', 13)
    ss = load_schema(importer.source, 'scnr', importer.reference)
    ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
    variants, variant_report = resolve_variants(source, target, importer.registry.newtag)
    importer.resolved.update({key: (key[0], datum) for key, datum in variants.items()})
    scenario = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    # Some MCC multiplayer caches retain anonymous editor biped placements
    # whose entire used palette consists of null references. Route only that
    # proven inert case through the existing null-palette omission logic.
    if 'Bipeds' not in placements:
        bf,pf=field(ss,'Bipeds'),field(ss,'Biped Palette')
        bipeds=source.block(scenario+int(bf.get('offset'),0),int(bf.get('elementSize'),0))
        palette=source.block(scenario+int(pf.get('offset'),0),int(pf.get('elementSize'),0))
        if bipeds and all(source.unpack('h',row+2)[0]==-1
                and 0<=source.unpack('h',row)[0]<len(palette)
                and source.u(palette[source.unpack('h',row)[0]]+12)==0xffffffff for row in bipeds):
            placements['Bipeds']=('Biped Palette',0)
    preserved_null_placements = audited_dune_null_placements(source, ss)
    from dune_placements import corrections as dune_corrections
    placement_corrections, placement_correction_report = dune_corrections(importer, ss)
    for name, (palette_name, _) in placements.items():
        sf, pf = field(ss, name), field(ss, palette_name)
        rows = source.block(scenario + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        palette = source.block(scenario + int(pf.get('offset'), 0), int(pf.get('elementSize'), 0))
        for source_index, row in enumerate(rows):
            if (name, source_index) in preserved_null_placements:
                continue
            index = source.unpack('h', row)[0]
            if getattr(importer, 'gulch_partition', None) and name == 'Effect Scenery' and index == -1:
                if source.unpack('h', row + 2)[0] != -1:
                    raise ValueError('Named null effect placement requires review')
                continue
            if not 0 <= index < len(palette):
                raise ValueError(f'{name}: invalid palette index {index}')
            datum = source.u(palette[index] + 12)
            if datum == 0xffffffff:
                if source.unpack('h', row + 2)[0] != -1:
                    raise ValueError('Named null palette placement requires review')
                continue
            key = source.tags[datum & 65535]['group'], source.name(datum & 65535)
            if key not in getattr(importer, 'omitted_assets', ()):
                importer.import_tag(datum)
    prepared = prepare(source, target, ss, ds, {key: value[1] for key, value in importer.resolved.items()}, placements,
                       getattr(importer, 'omitted_assets', ()), bool(getattr(importer, 'gulch_partition', None)),
                       True,
                       lambda value: importer.source_strings.translate(value, importer.target_strings),
                       preserved_null_placements, placement_corrections)
    importer.preserved_null_placements = sorted(preserved_null_placements)
    powerup_adjustments = []
    if getattr(importer, 'slot', None) == 'chillout':
        # CE powerups were authored with their origins on the floor. Native H3
        # pickups need clearance and the retail resting/acceleration settings.
        # Change placements only; leave native equipment and physics untouched.
        count, payload = prepared['arrays']['Equipment']
        payload = bytearray(payload)
        equipment = field(ds, 'Equipment')
        stride = int(equipment.get('elementSize'), 0)
        palette = prepared['arrays']['Equipment Palette'][1]
        native_names = {(t['salt'] << 16) | i: target.name(i) for i, t in target.tags.items()}
        for i in range(count):
            at = i * stride
            pi = struct.unpack_from('>h', payload, at)[0]
            datum = struct.unpack_from('>I', palette, pi * 48 + 12)[0]
            name = native_names.get(datum, '')
            if name not in (r'objects\multi\powerups\powerup_blue\powerup_blue',
                            r'objects\multi\powerups\powerup_red\powerup_red'):
                continue
            pos = at + int(field(equipment, 'Position').get('offset'), 0)
            xyz = struct.unpack_from('>3f', payload, pos)
            struct.pack_into('>f', payload, pos + 8, xyz[2] + 0.35)
            for label, fmt, value in [('Placement Flags', 'I', 0x100),
                                      ('Equipment Flags', 'I', 4), ('Team', 'h', 8)]:
                offset = at + int(field(equipment, label).get('offset'), 0)
                old = struct.unpack_from('>' + fmt, payload, offset)[0]
                struct.pack_into('>' + fmt, payload, offset, value if label == 'Team' else old | value)
            powerup_adjustments.append({'index': i, 'tag': name, 'original_position': xyz,
                                        'height_clearance': 0.35, 'settings': 'Retail resting, acceleration, neutral team'})
        if not getattr(importer, 'chiron', False) and len(powerup_adjustments) != 2:
            raise ValueError('Prisoner must have exactly two native powerup placements')
        prepared['arrays']['Equipment'] = count, bytes(payload)
    teleporter_adjustments = []
    if getattr(importer, 'chiron', False) or getattr(importer.materials, 'boarding_action', False):
        tele_name = r'custom\objects\scen\mp_obj\hce_tele_flat_wide\hce_tele_2_way_flat_wide'
        tele_tag = next(t for n, t in source.tags.items() if source.name(n) == tele_name)
        object_schema = load_schema(importer.source, 'scen', importer.reference)
        multiplayer = field(object_schema, 'Multiplayer Object')
        defaults = source.block(tele_tag['offset'] + int(multiplayer.get('offset'), 0),
                                int(multiplayer.get('elementSize'), 0))
        if len(defaults) != 1 or source.data[defaults[0] + 6] != 2:
            raise ValueError('CE wall teleporter requires its authored cylinder defaults')
        dimensions = source.unpack('4f', defaults[0] + 12)
        if dimensions[0] <= 0 or dimensions[2] + dimensions[3] <= 0:
            raise ValueError('Invalid authored teleporter dimensions')
        datum = importer.resolved[('scen', tele_name)][1]
        # The source's narrow cylinder does not span its wide portal wall.
        # Use H3's oriented box: full X width and full Y length, as in
        # ManagedDonkey multiplayer_object_render_debug_boundary. Derive Y
        # coverage from the authored render-model bounds rather than guessing.
        model_name = r'custom\objects\scen\mp_obj\hce_tele_flat_wide\hce_tele_flat_wide'
        model = next(t for n, t in source.tags.items()
                     if t['group'] == 'mode' and source.name(n) == model_name)
        model_schema = load_schema(importer.source, 'mode', importer.reference)
        compression = field(model_schema, 'Compression Info')
        bounds = source.block(model['offset'] + int(compression.get('offset'), 0),
                              int(compression.get('elementSize'), 0))
        if len(bounds) != 1:
            raise ValueError('CE wall portal must have one authored compression bound')
        x0, x1, y0, y1, z0, z1 = source.unpack('6f', bounds[0] + 4)
        if not (x0 < x1 and y0 < y1 and z0 < z1):
            raise ValueError('Invalid CE wall portal model bounds')
        dimensions = (max(dimensions[0] * 2, 2 * max(abs(x0), abs(x1))),
                      2 * max(abs(y0), abs(y1)) + 0.04, dimensions[2], dimensions[3])
        # Also update the private custom tag so newly forged instances agree.
        tag_address = struct.unpack_from('>I', importer.registry.tags, (datum & 65535) * 8 + 4)[0]
        target_object_schema = ET.parse(importer.reference / 'plugins/scen.xml').getroot()
        target_mp = field(target_object_schema, 'Multiplayer Object')
        mp_count, mp_pointer = struct.unpack('>II', importer.builder.read(
            tag_address + int(target_mp.get('offset'), 0), 8))
        if mp_count != 1:
            raise ValueError('Converted portal multiplayer defaults missing')
        importer.builder.put(mp_pointer + 6, 'B', 3)
        importer.builder.put(mp_pointer + 12, '4f', *dimensions)
        count, data = prepared['arrays']['Scenery']
        _, palette = prepared['arrays']['Scenery Palette']
        payload = bytearray(data)
        scenery = field(ds, 'Scenery')
        stride = int(scenery.get('elementSize'), 0)
        labels = ('Boundary Shape Width/Radius', 'Boundary Shape Box Length',
                  'Boundary Shape +Height', 'Boundary Shape -Height')
        for index in range(count):
            at = index * stride
            pi = struct.unpack_from('>h', payload, at)[0]
            if struct.unpack_from('>I', palette, pi * 48 + 12)[0] != datum:
                continue
            shape = at + int(field(scenery, 'Boundary Shape').get('offset'), 0)
            offsets = [at + int(field(scenery, label).get('offset'), 0) for label in labels]
            old = [struct.unpack_from('>f', payload, pos)[0] for pos in offsets]
            if payload[shape] in (0, 1) and not any(old):
                old_shape = payload[shape]
                payload[shape] = 3
                for pos, value in zip(offsets, dimensions):
                    struct.pack_into('>f', payload, pos, value)
                teleporter_adjustments.append({'index': index, 'old_shape': old_shape,
                                               'wall_box_dimensions': dimensions,
                                               'model_bounds': [x0, x1, y0, y1, z0, z1]})
        prepared['arrays']['Scenery'] = count, bytes(payload)
    island_start = []
    if getattr(importer, 'forge_partition_side', None) == 'island':
        from forge_island_spawn import relocate_marker
        island_start = relocate_marker(importer, prepared, ds)
    from dune_inactive_ai import (remap_palettes as remap_dune_ai_palettes,
                                 sanitize_navigation as sanitize_dune_ai_navigation)
    ai_palette_relocations = remap_dune_ai_palettes(importer, ss, ds, prepared)
    ai_navigation_corrections = sanitize_dune_ai_navigation(importer, ss, ds)
    stage(importer.builder, prepared, ds)
    return {'counts': {name: count for name, (count, _) in prepared['arrays'].items()},
            'variants': variant_report, 'unresolved': prepared['unresolved'],
            'preserved_null_placements': sorted(preserved_null_placements),
            'placement_corrections': placement_correction_report,
            'inactive_ai_palette_relocations': ai_palette_relocations,
            'inactive_ai_navigation_corrections': ai_navigation_corrections,
            'powerup_adjustments': powerup_adjustments, 'island_start': island_start,
            'teleporter_adjustments': teleporter_adjustments}


def stage_spawn_settings(importer):
    """Transfer starting loadout, fallback starts and authored spawn influences."""
    import xml.etree.ElementTree as ET
    from tag_metadata import MetadataConverter
    source = importer.source
    ss = load_schema(importer.source, 'scnr', importer.reference)
    ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
    root = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    converter = MetadataConverter(source, importer.builder, importer.source_strings,
                                  importer.target_strings, importer.import_tag)
    arrays = {}
    names = ('Player Starting Profile', 'Player Starting Locations', 'Enemy Forbid Influence',
             'Enemy Bias Influence', 'Ally Bias Influence', 'Selected Ally Bias Influence',
             'Dead Teammate Influence', 'Spawn Data')
    for name in names:
        sf, df = field(ss, name), field(ds, name)
        stride = int(sf.get('elementSize'), 0)
        rows = source.block(root + int(sf.get('offset'), 0), stride)
        payload = bytearray()
        for index, row in enumerate(rows):
            if name == 'Spawn Data':
                if stride == 108 and int(df.get('elementSize'), 0) == 108:
                    # Pre-December 2022 MCC retains the original reserved area.
                    payload.extend(converter.convert(row, sf, df, f'scnr:/{name}[{index}]'))
                    continue
                # MCC removes 60 reserved bytes before the three nested blocks.
                # Preserve authored heights, influences and zones at retail offsets.
                if stride != 48 or int(df.get('elementSize'), 0) != 108:
                    raise ValueError('Unexpected spawn-data layout')
                record = bytearray(108)
                struct.pack_into('>3f', record, 0, *source.unpack('3f', row))
                for block_name in ('Dynamic Spawn Overloads', 'Static Respawn Zones',
                                   'Static Initial Spawn Zones'):
                    sb, db = field(sf, block_name), field(df, block_name)
                    children = source.block(row + int(sb.get('offset'), 0),
                                            int(sb.get('elementSize'), 0))
                    data = b''.join(converter.convert(child, sb, db,
                        f'scnr:/Spawn Data[{index}]/{block_name}[{n}]')
                        for n, child in enumerate(children))
                    struct.pack_into('>III', record, int(db.get('offset'), 0), len(children),
                                     importer.builder.alloc(data) if data else 0, 0)
                payload.extend(record)
            else:
                payload.extend(converter.convert(row, sf, df, f'scnr:/{name}[{index}]'))
        if name == 'Player Starting Locations' and getattr(importer, 'forge_partition_side', None) == 'island':
            from forge_island_spawn import FACING
            if len(rows) != 1:
                raise ValueError('Expected one Forge fallback start')
            struct.pack_into('>3f', payload, int(field(df, 'Position').get('offset'), 0), *importer.forge_island_start)
            struct.pack_into('>2f', payload, int(field(df, 'Facing').get('offset'), 0), FACING, 0.)
        arrays[name] = len(rows), bytes(payload)
    stage(importer.builder, {'arrays': arrays, 'unresolved': []}, ds)
    return {name: count for name, (count, _) in arrays.items()}
