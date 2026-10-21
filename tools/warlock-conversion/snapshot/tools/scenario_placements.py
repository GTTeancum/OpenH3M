"""Convert placement records by schema, with explicit unresolved dependencies.

This module does not publish a map. Its output is for the scenario assembly stage;
that stage must also rebuild palettes and remap object-name/parent indices.
"""
import collections
import struct


FORMATS = {
    'int8': 'b', 'int16': 'h', 'int32': 'i',
    'enum8': 'b', 'enum16': 'h', 'enum32': 'i',
    'flags8': 'B', 'flags16': 'H', 'flags32': 'I',
    'float32': 'f', 'degree': 'f', 'point3': '3f', 'degree3': '3f',
    'color32': 'I', 'datum': 'I', 'stringid': 'I', 'rangef': '2f', 'ranged': '2f',
}


def fields(schema):
    # Duplicate names (e.g. Parent Marker) are distinguished by occurrence.
    occurrences = collections.Counter()
    result = {}
    for field in schema:
        if field.get('offset') is None:
            continue
        name = field.get('name')
        result[name, occurrences[name]] = field
        occurrences[name] += 1
    return result


def translate_flags(value, source, target):
    old = {int(x.get('index')): x.get('name') for x in source if x.tag == 'bit'}
    new = {x.get('name'): int(x.get('index')) for x in target if x.tag == 'bit'}
    result = 0
    for bit in range(32):
        if not value & (1 << bit):
            continue
        name = old.get(bit)
        if name is None or name not in new:
            raise ValueError(f"Unmapped {source.get('name')} bit {bit}: {name}")
        result |= 1 << new[name]
    return result


def translate_enum(value, source, target):
    old = {int(x.get('value'), 0): x.get('name') for x in source if x.tag == 'option'}
    new = {x.get('name'): int(x.get('value'), 0) for x in target if x.tag == 'option'}
    if value == -1:
        return value
    if value in old and old[value] in new:
        return new[old[value]]
    if old == {v: k for k, v in new.items()}:
        return value
    raise ValueError(f"Unmapped {source.get('name')} enum {value}")


def convert_record(cache, row, source_schema, target_schema):
    source_fields = fields(source_schema)
    target_fields = fields(target_schema)
    if source_fields.keys() != target_fields.keys():
        raise ValueError('Placement field sets differ; requires an explicit mapping')
    out = bytearray(int(target_schema.get('elementSize'), 0))
    covered = set()
    for key, dest in target_fields.items():
        src = source_fields[key]
        kind = src.tag.lower()
        if dest.tag.lower() != kind:
            raise ValueError(f'Field type changed: {key}')
        offset, at = int(dest.get('offset'), 0), row + int(src.get('offset'), 0)
        if kind == 'tagblock':
            if cache.u(at):
                raise ValueError(f'Nonempty nested block: {key}')
            size = 12
        else:
            if kind not in FORMATS:
                raise ValueError(f'Unsupported field: {kind} {key}')
            fmt = FORMATS[kind]
            values = cache.unpack(fmt, at)
            if kind == 'stringid' and values[0] != 0:
                raise ValueError(f'String ID needs remapping: {key} {values[0]:#x}')
            if kind.startswith('flags'):
                values = (translate_flags(values[0], src, dest),)
            elif kind.startswith('enum'):
                values = (translate_enum(values[0], src, dest),)
            struct.pack_into('>' + fmt, out, offset, *values)
            size = struct.calcsize('>' + fmt)
        covered.update(range(offset, offset + size))
    if covered != set(range(len(out))):
        raise ValueError('Placement schema leaves bytes uncovered')
    return bytes(out)


def plan_placements(source, target, source_schema, target_schema, imported=None, placements=None, omitted=(), omit_null_effects=False):
    source_scenario = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    retail_names = {(t['group'], target.name(i)): (t['salt'] << 16) | i
                    for i, t in target.tags.items()}
    # The dependency importer owns allocation and supplies actual retail datums.
    # Mapping does not authorize a different tag name as a silent substitute.
    retail_names.update(imported or {})
    result = {}
    pairs = placements or [('Scenery', 'Scenery Palette'), ('Weapons', 'Weapon Palette'),
                           ('Equipment', 'Equipment Palette'), ('Crates', 'Crates Palette')]
    for name, palette in pairs:
        sf = next(x for x in source_schema if x.get('name') == name)
        df = next(x for x in target_schema if x.get('name') == name)
        pf = next(x for x in source_schema if x.get('name') == palette)
        rows = source.block(source_scenario + int(sf.get('offset'), 0), int(sf.get('elementSize'), 0))
        palettes = source.block(source_scenario + int(pf.get('offset'), 0), int(pf.get('elementSize'), 0))
        converted, unresolved = [], []
        for index, row in enumerate(rows):
            palette_index = source.unpack('h', row)[0]
            if omit_null_effects and name == 'Effect Scenery' and palette_index == -1:
                if source.unpack('h', row + 2)[0] != -1:
                    raise ValueError('Named null effect placement requires review')
                continue
            if not 0 <= palette_index < len(palettes):
                raise ValueError(f'{name}[{index}]: invalid palette index {palette_index}')
            tid = source.u(palettes[palette_index] + 12) & 0xffff
            key = source.tags[tid]['group'], source.name(tid)
            if key in omitted:
                continue
            try:
                data = convert_record(source, row, sf, df)
            except ValueError as exc:
                unresolved.append({'index': index, 'tag': key, 'reason': str(exc)})
                continue
            if key not in retail_names:
                unresolved.append({'index': index, 'tag': key, 'reason': 'Dependency requires import'})
                continue
            converted.append({'source_index': index, 'source_offset': row,
                              'palette_index': palette_index, 'retail_datum': retail_names[key],
                              'retail_group': key[0],
                              'record': data})
        result[name] = {'source_count': len(rows), 'converted': converted, 'unresolved': unresolved}
    return result
