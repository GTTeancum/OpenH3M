"""Prepare retail scenario arrays and stage them only when dependencies resolve.

Unresolved records remain visible in the report. Preparation never writes a map;
stage() refuses partial output so an incomplete scenario cannot be deployed by
mistake. Imported object tags can be supplied by the dependency importer.
"""
import struct
from scenario_placements import plan_placements


PLACEMENTS = {'Scenery': ('Scenery Palette', 6), 'Weapons': ('Weapon Palette', 2),
              'Equipment': ('Equipment Palette', 3), 'Crates': ('Crates Palette', 10)}


def field(schema, name):
    return next(x for x in schema if x.get('name') == name)


def prepare(source, target, source_schema, target_schema, imported=None, placements=None, omitted=(), omit_null_effects=False):
    placements = placements or PLACEMENTS
    plan = plan_placements(source, target, source_schema, target_schema, imported,
                           [(name, palette) for name, (palette, _) in placements.items()], omitted, omit_null_effects)
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
    if getattr(importer, 'slot', 'lockout') in ('zanzibar', 'chillout', 'sandbox'):
        placements['Vehicles'] = ('Vehicle Palette', 1)
    if include_sound_scenery:
        placements['Sound Scenery'] = ('Sound Scenery Palette', 9)
    if include_effect_scenery:
        placements['Effect Scenery'] = ('Effect Scenery Palette', 13)
    ss = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
    ds = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
    variants, variant_report = resolve_variants(source, target, importer.registry.newtag)
    importer.resolved.update({key: (key[0], datum) for key, datum in variants.items()})
    scenario = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    for name, (palette_name, _) in placements.items():
        sf, pf = field(ss, name), field(ss, palette_name)
        rows = source.block(scenario + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        palette = source.block(scenario + int(pf.get('offset'), 0), int(pf.get('elementSize'), 0))
        for row in rows:
            index = source.unpack('h', row)[0]
            if getattr(importer, 'gulch_partition', None) and name == 'Effect Scenery' and index == -1:
                if source.unpack('h', row + 2)[0] != -1:
                    raise ValueError('Named null effect placement requires review')
                continue
            if not 0 <= index < len(palette):
                raise ValueError(f'{name}: invalid palette index {index}')
            datum = source.u(palette[index] + 12)
            key = source.tags[datum & 65535]['group'], source.name(datum & 65535)
            if key not in getattr(importer, 'omitted_assets', ()):
                importer.import_tag(datum)
    prepared = prepare(source, target, ss, ds, {key: value[1] for key, value in importer.resolved.items()}, placements,
                       getattr(importer, 'omitted_assets', ()), bool(getattr(importer, 'gulch_partition', None)))
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
        if len(powerup_adjustments) != 2:
            raise ValueError('Prisoner must have exactly two native powerup placements')
        prepared['arrays']['Equipment'] = count, bytes(payload)
    island_start = []
    if getattr(importer, 'forge_partition_side', None) == 'island':
        from forge_island_spawn import relocate_marker
        island_start = relocate_marker(importer, prepared, ds)
    stage(importer.builder, prepared, ds)
    return {'counts': {name: count for name, (count, _) in prepared['arrays'].items()},
            'variants': variant_report, 'unresolved': prepared['unresolved'],
            'powerup_adjustments': powerup_adjustments, 'island_start': island_start}


def stage_spawn_settings(importer):
    """Transfer starting loadout, fallback starts and authored spawn influences."""
    import xml.etree.ElementTree as ET
    from tag_metadata import MetadataConverter
    source = importer.source
    ss = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
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
                # Warlock's single empty record has no overrides or zones.
                # Retail's additional reserved words likewise initialize zero.
                if any(source.data[row:row + stride]):
                    raise ValueError('Nonempty Spawn Data needs a dedicated mapping')
                payload.extend(bytes(int(df.get('elementSize'), 0)))
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
