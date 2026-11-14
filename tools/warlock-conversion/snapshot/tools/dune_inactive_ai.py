"""Guarded omission of Dune's non-spawning editor character dependencies.

The authored squad, group, zone and hint metadata remain intact. Four character
palette slots remain at their original indices, but contain native null refs.
This is not a general AI stripping rule or support for spawning these actors.
"""
import copy
import hashlib
import struct

from assemble_scenario import field
from dune_flare import SCENARIO, BUILD, SOURCE_SHA256

PRESERVED_BLOCKS = ('Squad Groups', 'Squads', 'Zones', 'Reference Frames')
CHARACTERS = (
    r'h2\objects\characters\grunt\ai\h2 grunt',
    r'h2\objects\characters\elites\ai\h2 elite',
    r'h2\objects\characters\brute\ai\h2 brute',
    r'h2\objects\characters\brute\h2a_brute\ai\h2a_brute',
)
ROW_HASHES = {
    'Squad Groups': (40, ('d977915ea6555781c5d7e965f71f541cf5159dcf96265242f67116b3f084e625',)),
    'Squads': (64, ('c36a9a7b5aa93f08fa8343a59183a1a484f9893dbccea83bdcc9c86f9b6cad3e',)),
    'Fire-Teams': (96, ('fe30d269a74b5ac7205f86196e518142e4d37063d2e6c675b70b31d9baea9244',)),
    'Starting Locations': (136, ('16fec578b21c20d2e55a7b1d42f7b0b5135a736e9337bdec869b452a31c19df0',)),
    'Character Palette': (16, (
        'b398236676e79a373067e68eaa0f6e863ff6eb0139c020f9849279bc899e2296',
        '7ef2719c5641596e0a6e0d46e9ef6e4887efc559037fc803597b40c7ce9f6be5',
        'edce005ae4fc0a02e646035b0d8b988228ca420e1793db5e72ebbae069627b17',
        'cbe8a9d77c7eaf10035db7612809f6ce09b71a4353bffd3bcc267c1b4333a0df')),
    'Reference Frames': (16, (
        'f5049f0e2d680713ce2c88267b474b27d960de3cf98d2c3f518c1ec9b81adca0',
        '57abbea883b949a797669bfdeb9517ad417f0222152cee3b7adabff9ce178ab6',
        'f69dbcc4fedbff51d05f12c7ece91633b91fa2188b17c4b373f726b4781a9ce4')),
    'Points': (60, (
        '4029ce5b9d9d7a568a00fe611b639778cba3e7c9e46ed0356976845b1a8c3dc2',
        '7a731590f92996437ed5f42afe7786fddb3a375aa7e5a2745341343c2860de3a',
        '044097d88502c2236bac23b16a75e5094c7304614d573ad46b80a3e6d2305c73',
        '90b279c37b5ea86ec22b605fdaf0309bf74d09e49a345eee10a622658afe678f',
        '1e925ba884be94b3396154d6b5a5082feed070c2ce1bb13391073bc8ec3c5cb8')),
    'Firing Positions': (40, (
        '7069f8e72802bc782166eb047e9ba27566c56b2060f05463dc22f2d8ae52ba39',
        'ab63c791e637a27ed3ee3b2140c545e02044a6fd5dcc736ee594c826134e0f1a',
        '354a7acc29f72db2bf7b032d5974ed81752d0229fc73d0cecbd90e7951f93716')),
}
SCRIPT_TABLES = {
    'Scripts': (52, 41, 'b825e338a7de132821eb70ca95c3e36668945ca589a451f5635cf2f038ae5e33'),
    'Globals': (40, 7, '6ebd90b8d4aa041203725a5ffae89dd89837eeb46b6021cf6f7c4affe16331ea'),
    'Script Expressions': (24, 2735, '36018ce798f068c74dce2919a8de3788248021f5b0fee82a47cdaf09343c61fa'),
}
NULL_REFERENCE = struct.pack('>4I', 0xffffffff, 0, 0, 0xffffffff)
NOTE = (
    'Dune/Relic candidate: four non-spawning editor AI character definitions '
    '(H2 Grunt, Elite, Brute and H2A Brute) are omitted, with four native null '
    'palette slots preserving indices. The authored squad/group/zone/hint '
    'records and scripts remain. Exact-source audit found Initially Placed '
    'off, zero fireteam/start difficulty masks, no placement scripts/objectives '
    'and no actor creation or wake calls in any allocated script expression. '
    'Forced developer/debug spawning of these editor actors is not supported. '
    'Ordinary multiplayer inactivity is static evidence, not runtime acceptance.'
)


def validate_rows(label, rows):
    size, expected = ROW_HASHES[label]
    if (len(rows) != len(expected) or any(len(row) != size for row in rows)
            or tuple(hashlib.sha256(row).hexdigest() for row in rows) != expected):
        raise ValueError('Dune inactive AI records changed: ' + label)


def require_inactive_state(flags, masks, placement_indices, placement_names, objectives):
    if (flags != 0 or tuple(masks) != (0, 0)
            or tuple(placement_indices) != (-1, -1)
            or len(placement_names) != 2 or any(any(name) for name in placement_names)
            or tuple(objectives) != (-1, -1)):
        raise ValueError('Dune AI activation state changed')


def validate_source(source, schema):
    scenarios = [(source.name(k), t['offset']) for k, t in source.tags.items()
                 if t['group'] == 'scnr']
    if len(scenarios) != 1 or scenarios[0][0] != SCENARIO:
        return None
    if (bytes(source.data[0xa0:0xc0]).split(b'\0')[0] != BUILD.encode()
            or hashlib.sha256(source.data).hexdigest() != SOURCE_SHA256):
        raise ValueError('Dune inactive AI omission requires the exact audited source')
    root = scenarios[0][1]

    def rows(parent, parent_schema, label, verify=True):
        node = field(parent_schema, label)
        size = int(node.get('elementSize'), 0)
        result = source.block(parent + int(node.get('offset'), 0), size)
        if verify:
            if size != ROW_HASHES[label][0]:
                raise ValueError('Dune inactive AI schema changed: ' + label)
            validate_rows(label, [bytes(source.data[r:r + size]) for r in result])
        return result, node

    def integer(at, node, name, fmt):
        return source.unpack(fmt, at + int(field(node, name).get('offset'), 0))[0]

    groups, group_schema = rows(root, schema, 'Squad Groups')
    squads, squad_schema = rows(root, schema, 'Squads')
    fireteams, fireteam_schema = rows(squads[0], squad_schema, 'Fire-Teams')
    starts, start_schema = rows(fireteams[0], fireteam_schema, 'Starting Locations')
    palette, _ = rows(root, schema, 'Character Palette')
    rows(root, schema, 'Reference Frames')
    masks, placement_indices, placement_names = [], [], []
    for at, node in ((fireteams[0], fireteam_schema), (starts[0], start_schema)):
        masks.append(integer(at, node, 'Place On', 'H'))
        placement_indices.append(integer(at, node, 'Placement Script Index', 'h'))
        name = field(node, 'Placement Script Name')
        offset = at + int(name.get('offset'), 0)
        placement_names.append(source.data[offset:offset + int(name.get('size'), 0)])
    require_inactive_state(integer(squads[0], squad_schema, 'Flags', 'I'),
                           masks, placement_indices, placement_names,
                           [integer(at, node, 'Initial Objective Index', 'h')
                            for at, node in ((groups[0], group_schema), (squads[0], squad_schema))])
    for name in ('Bipeds', 'Flocks', 'Creatures Palette', 'Campaign Players',
                 'AI Objectives', 'Triggers', 'Mission Dialogue'):
        if source.u(root + int(field(schema, name).get('offset'), 0)):
            raise ValueError('Dune AI activation-related block is populated: ' + name)
    for row, expected in zip(palette, CHARACTERS):
        datum = source.u(row + 12)
        tag = source.tags.get(datum & 65535)
        if (tag is None or tag['salt'] != datum >> 16 or tag['group'] != 'char'
                or source.name(datum & 65535) != expected):
            raise ValueError('Dune editor character palette changed')
    # The independent 41-body/all-1977-live-node audit includes startup,
    # continuous, dormant, static and global roots, not only reachable startup
    # scripts. These exact table hashes and the whole-file guard pin that proof.
    for name, (size, count, digest) in SCRIPT_TABLES.items():
        script_rows, node = rows(root, schema, name, verify=False)
        payload = b''.join(source.data[r:r + size] for r in script_rows)
        if (int(node.get('elementSize'), 0) != size or len(script_rows) != count
                or hashlib.sha256(payload).hexdigest() != digest):
            raise ValueError('Dune inactive AI script proof changed: ' + name)
    return dict(source_sha256=SOURCE_SHA256, scripts=41, active_expression_nodes=1977,
                initially_placed=False, placement_difficulty_masks=[0, 0],
                omitted_characters=list(CHARACTERS), preserved_character_slots=4)


def prepare(importer, source_schema, target_schema):
    evidence = validate_source(importer.source, source_schema)
    if evidence is None:
        return None
    node = field(target_schema, 'Character Palette')
    fields = [f for f in node if f.get('offset') is not None]
    if (int(node.get('elementSize'), 0) != 16 or len(fields) != 1
            or fields[0].tag.lower() != 'tagref' or int(fields[0].get('offset'), 0) != 0):
        raise ValueError('Dune native character palette schema changed')
    importer.scenario_compatibility_notes = [dict(
        source=SCENARIO, group='scnr', compatibility_notes=[NOTE],
        inactive_editor_ai_omission=evidence)]
    importer.dune_inactive_ai_guard = evidence
    return {'Character Palette': (4, NULL_REFERENCE * 4)}


def reference_frame_schemas(source_node, target_node):
    """Object identifiers are not tag datums; preserve them across endianness."""
    nodes = copy.deepcopy(source_node), copy.deepcopy(target_node)
    for node in nodes:
        uid = field(node, 'Unique ID')
        if (node.get('name') != 'Reference Frames' or int(node.get('elementSize'), 0) != 16
                or uid.tag.lower() != 'datum' or int(uid.get('offset'), 0) != 0):
            raise ValueError('Dune reference-frame object identity layout changed')
        uid.tag = 'uint32'
    return nodes


def palette_slot(payload, count, group, datum):
    """Keep existing placed-palette indices; append only an absent identity."""
    if len(payload) != count * 48 or len(group) != 4 or datum == 0xffffffff:
        raise ValueError('Dune AI target placement palette is malformed')
    matches = [n for n in range(count)
               if struct.unpack_from('>I', payload, n * 48 + 12)[0] == datum]
    if matches:
        if len(matches) != 1 or payload[matches[0] * 48:matches[0] * 48 + 4] != group.encode():
            raise ValueError('Dune AI target palette identity is ambiguous')
        return matches[0], count, payload, False
    row = group.encode() + bytes(8) + struct.pack('>I', datum) + bytes(32)
    return count, count + 1, payload + row, True


def remap_palettes(importer, source_schema, target_schema, prepared):
    """Relocate the retained inactive fireteam's compacted object indices."""
    evidence = getattr(importer, 'dune_inactive_ai_guard', None)
    if evidence is None:
        return []
    if evidence.get('source_sha256') != SOURCE_SHA256:
        raise ValueError('Dune AI palette relocation lost its source guard')
    source, builder, cache = importer.source, importer.builder, importer.registry.cache
    source_root = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    native_root = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr') - cache.start + cache.base
    squads = field(target_schema, 'Squads')
    count, pointer = struct.unpack('>II', builder.read(native_root + int(squads.get('offset'), 0), 8))
    if count != 1:
        raise ValueError('Dune staged squad count changed')
    fireteams = field(squads, 'Fire-Teams')
    count, pointer = struct.unpack('>II', builder.read(pointer + int(fireteams.get('offset'), 0), 8))
    if count != 1:
        raise ValueError('Dune staged fireteam count changed')
    records, edits = [], []
    targets = (
        ('Initial Weapon Index', 'Weapon Palette', 30, 'weap',
         r'h2\objects\weapons\support_low\brute_shot\brute_shot',
         r'objects\weapons\support_low\brute_shot\brute_shot'),
        ('Vehicle Type Index', 'Vehicle Palette', 2, 'vehi',
         r'h2\objects\vehicles\ghost\ghost', r'objects\vehicles\ghost\ghost'),
    )
    from generational_assets import stock_aliases
    aliases = stock_aliases()
    for label, name, old, group, source_name, native_name in targets:
        sf, df = field(source_schema, name), field(target_schema, name)
        if int(df.get('elementSize'), 0) != 48:
            raise ValueError('Dune native object palette stride changed')
        source_rows = source.block(source_root + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        datum = source.u(source_rows[old] + 12)
        tag = source.tags.get(datum & 65535)
        if (tag is None or tag['salt'] != datum >> 16 or tag['group'] != group
                or source.name(datum & 65535) != source_name
                or aliases.get((group, source_name)) != (group, native_name, None)):
            raise ValueError('Dune AI stock object identity changed')
        field_schema = field(fireteams, label)
        if field_schema.tag.lower() != 'int16':
            raise ValueError('Dune native AI object index layout changed')
        at = pointer + int(field_schema.get('offset'), 0)
        if struct.unpack('>h', builder.read(at, 2))[0] != old:
            raise ValueError('Dune staged AI object index changed')
        result_group, result_datum = importer.import_tag(datum)
        if result_group != group:
            raise ValueError('Dune AI stock object group changed')
        count, payload = prepared['arrays'][name]
        new, count, payload, appended = palette_slot(payload, count, result_group, result_datum)
        prepared['arrays'][name] = count, payload
        edits.append((at, new))
        records.append(dict(field=label, source_palette_index=old, native_palette_index=new,
            source_object=source_name, native_object=native_name, native_datum=f'{result_datum:08x}',
            appended_unplaced_palette_entry=appended, placement_added=False))
    for at, value in edits:
        builder.put(at, 'h', value)
    evidence['object_palette_relocations'] = records
    importer.scenario_compatibility_notes[0]['compatibility_notes'].append(
        'Retained inactive fireteam object indices are relocated by identity: '
        'original H3 Brute Shot is appended as an unplaced weapon-palette entry '
        'if absent, and Ghost points to the actual compact native vehicle slot. '
        'No weapon or vehicle placement is added.')
    return records


def clear_native_sector_pairs(builder, records):
    """Validate every old pair before changing any of the 4-byte native refs."""
    addresses = [address for address, _ in records]
    if len(set(addresses)) != len(addresses) or any(
            abs(a - b) < 4 for i, a in enumerate(addresses) for b in addresses[i + 1:]):
        raise ValueError('Dune sector corrections overlap')
    for address, expected in records:
        if (len(expected) != 2 or min(expected) < 0
                or builder.read(address, 4) != struct.pack('>hh', *expected)):
            raise ValueError('Dune staged pathfinding sector reference changed')
    for address, _ in records:
        builder.put(address, 'hh', -1, -1)


def sanitize_navigation(importer, source_schema, target_schema):
    """Clear eight proven dangling sector refs, not positional BSP indices.

    Supplied Mythic XEX 820C34A0 is the shared native sector-validity helper.
    Both cs_point+0x30 and firing_position+0x18 reach it. Native constructors
    use the (-1,-1) representation (8252F0B0/B4, 820DCF6C/74). Do not change
    the point-set flags based only on a reconstructed flag name.
    """
    evidence = getattr(importer, 'dune_inactive_ai_guard', None)
    if evidence is None:
        return []
    if (evidence.get('source_sha256') != SOURCE_SHA256
            or getattr(importer, 'dune_empty_pathfinding_counts', None) != (0,) * 8):
        raise ValueError('Dune AI navigation correction requires all eight empty graph checks')
    source, builder, cache = importer.source, importer.builder, importer.registry.cache
    source_root = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    native_root = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr') - cache.start + cache.base
    plans, notes = [], []
    for labels, offset, sectors in (
            (('Zones', 'Firing Positions'), 0x18, (660, 660, 68)),
            (('Scripting Data', 'Point Sets', 'Points'), 0x30, (660, 660, 46, 356, 190))):
        source_at, native_at = source_root, native_root
        ss, ds = source_schema, target_schema
        for position, label in enumerate(labels):
            ss, ds = field(ss, label), field(ds, label)
            source_stride, target_stride = int(ss.get('elementSize'), 0), int(ds.get('elementSize'), 0)
            rows = source.block(source_at + int(ss.get('offset'), 0), source_stride)
            count, pointer = struct.unpack('>II', builder.read(native_at + int(ds.get('offset'), 0), 8))
            expected_count = len(sectors) if position == len(labels) - 1 else 1
            if len(rows) != expected_count or count != expected_count:
                raise ValueError('Dune navigation row count changed: ' + label)
            source_at, native_at = rows[0], pointer
        if source_stride != ROW_HASHES[label][0] or target_stride != source_stride:
            raise ValueError('Dune navigation row layout changed')
        validate_rows(label, [bytes(source.data[r:r + source_stride]) for r in rows])
        for schema in (ss, ds):
            pair = [(f.tag.lower(), f.get('name')) for f in schema
                    if int(f.get('offset', '-1'), 0) in (offset, offset + 2)]
            if pair != [('int16', 'BSP Index'), ('int16', 'Sector Index')]:
                raise ValueError('Dune navigation sector-pair layout changed')
        for index, (row, sector) in enumerate(zip(rows, sectors)):
            if source.unpack('hh', row + offset) != (0, sector):
                raise ValueError('Dune source navigation sector changed')
            plans.append((pointer + index * target_stride + offset, (0, sector)))
            notes.append(dict(block='/'.join(labels), index=index, before=[0, sector],
                              after=[-1, -1], changed_bytes=4))
    clear_native_sector_pairs(builder, plans)
    evidence['dangling_sector_references_cleared'] = notes
    importer.scenario_compatibility_notes[0]['compatibility_notes'].append(
        'Eight pre-existing AI navigation-sector links into absent pathfinding '
        'graphs are changed to the verified native none pair (-1,-1), 32 bytes '
        'in total. All point/firing-position records, XYZ, angles, positional BSP '
        'indices, areas, clusters, reference frames and point-set flags remain. '
        'No navigation graph is invented and no AI spawning is enabled.')
    return notes
