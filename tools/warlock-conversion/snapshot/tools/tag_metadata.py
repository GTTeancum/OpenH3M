"""Schema-based MCC-to-retail metadata conversion with explicit dependencies.

Resource datums and opaque data require dedicated handlers; this converter never
copies platform pointers or compiled data blindly. Callers own a scratch builder
and publish it only after the complete dependency graph has converted.
"""
import struct
from scenario_placements import FORMATS, fields, translate_flags, translate_enum


SCALARS = dict(FORMATS, uint8='B', uint16='H', uint32='I', rangef='2f', range16='2h',
               colorf='3f', vector2='2f', vector3='3f', vector4='4f', point2='2f',
               plane3='4f', plane2='3f', degree2='2f', ranged='2f', point16='2h')

# Original-disc UI defaults; ODST variants use their corresponding H3 family.
WEAPON_UI = {
    r'weap:objects\weapons\pistol\automag\automag': (6, 2),
    r'weap:objects\weapons\turret\missile_pod\missile_pod': (32, 0),
    r'weap:objects\weapons\rifle\smg_silenced\smg_silenced': (14, 0),
    r'weap:objects\weapons\rifle\plasma_rifle_red\plasma_rifle_red': (22, 0),
}


class MetadataConverter:
    def __init__(self, source, builder, strings, target_strings, tag_reference,
                 data_reference=None, resource_reference=None, special_block=None, shader_reference=None):
        self.source, self.builder = source, builder
        self.strings, self.target_strings = strings, target_strings
        self.tag_reference = tag_reference
        self.data_reference = data_reference
        self.resource_reference = resource_reference
        self.special_block = special_block
        self.shader_reference = shader_reference

    def convert(self, offset, source_schema, target_schema, path='', depth=0):
        if self.special_block is not None:
            result = self.special_block(offset, source_schema, target_schema, path)
            if result is not None:
                return result
        from collision_physics import convert_collision_block
        from bsp_metadata import convert_bsp_block
        specialized = convert_bsp_block(self, offset, source_schema, target_schema, path)
        if specialized is not None:
            return specialized
        specialized = convert_collision_block(self, offset, source_schema, target_schema, path)
        if specialized is not None:
            return specialized
        from model_physics import convert_model_physics
        specialized = convert_model_physics(self, offset, source_schema, target_schema, path)
        if specialized is not None:
            return specialized
        if depth > 32:
            raise ValueError(f'{path}: metadata nesting exceeds limit')
        source_fields, target_fields = fields(source_schema), fields(target_schema)
        size = int(target_schema.get('baseSize') or target_schema.get('elementSize'), 0)
        out = bytearray(size)
        covered = set()
        for key, src in source_fields.items():
            if key in target_fields:
                continue
            at = offset + int(src.get('offset'), 0)
            if (path.startswith('scnr:/Player Starting Profile') and key[0] == 'Editor Folder Index'
                    and self.source.unpack('h', at)[0] == -1):
                continue
            if (path.startswith('scnr:/Player Starting Profile') and key[0] == 'Unknown'
                    and self.source.unpack('h', at)[0] == 0):
                continue
            if path in WEAPON_UI:
                if key[0] in ('Private Use Font Icon', 'Private Use Font Icon (Dual)'):
                    # MCC Unicode pickup icons have no retail field. Retail
                    # uses the family message index supplied below instead.
                    continue
                if key[0] == 'First Person Weapon Offset Override':
                    # Only used by MCC's optional centered-crosshair mode.
                    # Retail uses the ordinary first-person weapon offset.
                    continue
            if src.tag.lower() == 'tagblock' and self.source.u(at) == 0:
                continue
            if path.startswith('chdt:') and src.tag.lower() == 'undefined' and self.source.u(at) == 0:
                continue
            if (path.startswith('chdt:') and source_schema.get('name') == 'Text Widgets'
                    and key[0] == 'Unknown' and src.tag.lower() == 'int16'
                    and self.source.unpack('h', at)[0] == 0):
                continue
            if key[0] in ('Instance Flags 3', 'Instance Flags 4') and src.tag.lower() == 'flags32' and self.source.u(at) == 0:
                # MCC extends instance masks to 128 bits. Retail's 64-bit mask
                # can represent this block only when both high words are zero.
                continue
            raise ValueError(f'{path}/{key[0]}: source-only field requires explicit handling')
        for key, dst in target_fields.items():
            kind = dst.tag.lower()
            at = int(dst.get('offset'), 0)
            name = path + '/' + key[0]
            src = source_fields.get(key)
            if src is None:
                if (path.startswith('hlmt:') and '/New Damage Info[' in path
                        and source_schema.get('name') == 'Nodes'
                        and int(source_schema.get('elementSize'), 0) == 2 and size == 16
                        and key[0] == 'Unknown' and kind in ('int16', 'undefined')):
                    width = 2 if kind == 'int16' else 4
                    covered.update(range(at, at + width))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Damage Sections'
                        and int(source_schema.get('elementSize'), 0) == 0x2c and size == 0x44
                        and key[0] in ('null block here 1', 'null block here 2')
                        and kind == 'uint32' and 0x18 <= at < 0x30):
                    covered.update(range(at, at + 4))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'New Damage Info'
                        and int(source_schema.get('elementSize'), 0) == 0xa4 and size == 0x100
                        and key[0] == 'Unknown' and kind in ('undefined', 'int16')):
                    # MCC strips these zero retail fields; confirmed against
                    # original armory missile model damage metadata.
                    width = 4 if kind == 'undefined' else 2
                    covered.update(range(at, at + width))
                    continue
                if path in WEAPON_UI:
                    defaults = {'OLD Message Index': ('h', WEAPON_UI[path][0]), 'Sort Order': ('h', WEAPON_UI[path][1]),
                                'OLD Multiplayer On-Ground Scale': ('f', 0),
                                'OLD Campaign On-Ground Scale': ('f', 0)}
                    if key[0] in defaults:
                        fmt, value = defaults[key[0]]
                        struct.pack_into('>' + fmt, out, at, value)
                        covered.update(range(at, at + struct.calcsize(fmt)))
                        continue
                    if key[0] in ('Collision Sound', 'Aged Weapon'):
                        out[at:at + 4] = b'\xff' * 4
                        struct.pack_into('>I', out, at + 12, 0xffffffff)
                        covered.update(range(at, at + 16))
                        continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Variants'
                        and int(source_schema.get('elementSize'), 0) == 48 and size == 56
                        and kind == 'undefined' and at in (48, 52)):
                    covered.update(range(at, at + 4))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Regions'
                        and int(source_schema.get('elementSize'), 0) == 20 and size == 24
                        and at in (20, 22)):
                    # MCC omits retail's region sorting override and padding.
                    # Neutral order is zero (no camera-relative override).
                    covered.update(range(at, at + 2))
                    continue
                if (path.startswith('hlmt:') and source_schema.get('name') == 'Permutations'
                        and int(source_schema.get('elementSize'), 0) == 24 and size == 36
                        and at >= 24 and self.source.u(offset + 12) == 0):
                    # Retail runtime-state lookup/padding is zero for stateless
                    # permutations, confirmed against native model records.
                    width = 4 if kind == 'undefined' else struct.calcsize('>' + SCALARS[kind])
                    covered.update(range(at, at + width))
                    continue
                if kind == 'tagblock' and key[0] in ('Predicted Resources', 'Predicted Bitmaps'):
                    covered.update(range(at, at + 12))
                    continue
                raise ValueError(f'{name}: retail-only field needs a default')
            compatible_flags = src.tag.lower().startswith('flags') and kind.startswith('flags')
            if src.tag.lower() != kind and not compatible_flags:
                raise ValueError(f'{name}: source/retail field types differ')
            read = offset + int(src.get('offset'), 0)
            if kind == 'ascii':
                width = int(dst.get('size'), 0)
                if src.get('size') != dst.get('size'):
                    raise ValueError(f'{name}: string field size differs')
                out[at:at + width] = self.source.data[read:read + width]
            elif kind == 'tagblock':
                stride = int(src.get('elementSize'), 0)
                rows = self.source.block(read, stride)
                if len(rows) > 1000000:
                    raise ValueError(f'{name}: excessive block count')
                payload = b''.join(self.convert(row, src, dst, name + f'[{i}]', depth + 1)
                                   for i, row in enumerate(rows))
                pointer = self.builder.alloc(payload) if payload else 0
                struct.pack_into('>III', out, at, len(rows), pointer, 0)
                width = 12
            elif kind == 'tagref':
                datum = self.source.u(read + 12)
                if datum == 0xffffffff:
                    out[at:at + 4] = b'\xff' * 4
                    struct.pack_into('>I', out, at + 12, datum)
                else:
                    group, target = self.tag_reference(datum)
                    if len(group) != 4 or target == 0xffffffff:
                        raise ValueError(f'{name}: invalid resolved tag reference')
                    out[at:at + 4] = group.encode('ascii')
                    struct.pack_into('>I', out, at + 12, target)
                width = 16
            elif kind == 'dataref':
                count = self.source.u(read)
                if count:
                    if self.data_reference is None:
                        raise ValueError(f'{name}: opaque data needs a format handler')
                    payload = self.data_reference(name, self.source, read)
                    struct.pack_into('>I', out, at, len(payload))
                    struct.pack_into('>I', out, at + 12, self.builder.alloc(payload))
                width = 20
            elif kind == 'shader':
                if self.shader_reference is None:
                    raise ValueError(f'{name}: native shader needs a dedicated handler')
                pointer = self.shader_reference(self.source.u(read), src.get('type'))
                struct.pack_into('>I', out, at, pointer)
                width = 4
            elif kind == 'undefined':
                if self.source.u(read):
                    raise ValueError(f'{name}: nonzero unknown field')
                width = 4
            else:
                fmt = SCALARS.get(kind)
                if kind == 'colorf' and dst.get('alpha') == 'true':
                    if src.get('alpha') != 'true':
                        raise ValueError(f'{name}: color alpha layout differs')
                    fmt = '4f'
                if fmt is None:
                    raise ValueError(f'{name}: unsupported field type {kind}')
                values = self.source.unpack(SCALARS[src.tag.lower()] if compatible_flags else fmt, read)
                if kind == 'stringid':
                    values = (self.strings.translate(values[0], self.target_strings),)
                elif kind == 'datum' and values[0] != 0xffffffff:
                    if self.resource_reference is None:
                        raise ValueError(f'{name}: resource datum needs conversion')
                    values = (self.resource_reference(name, values[0]),)
                elif kind.startswith('flags'):
                    if path.startswith('effe:') and source_schema.get('name') == 'Particle Systems' and key[0] == 'Flags':
                        # MCC enhanced-graphics near-fade override has no retail
                        # graphics mode. Other particle behavior bits still map.
                        values = (values[0] & ~(1 << 14),)
                    if path.startswith('phmo:') and source_schema.get('baseSize') and key[0] == 'Flags':
                        # This describes the serialized pointer width. Nested
                        # shapes must independently pass their layout handlers.
                        values = (values[0] & ~4,)
                    try:
                        values = (translate_flags(values[0], src, dst),)
                    except ValueError as error:
                        raise ValueError(f'{name}: {error}') from error
                elif kind.startswith('enum'):
                    statistic_alias = next((pair for token, pair in (
                        ('automag', ('Automag', 'Magnum')),
                        ('smg_silenced', ('Silenced SMG', 'SMG')),
                        ('plasma_rifle_red', ('Brute Plasma Rifle', 'Plasma Rifle')))
                        if token in path), None)
                    if (statistic_alias and key[0] in ('Damage Effect Reporting Type', 'Damage Reporting Type')
                            and any(x.get('name') == statistic_alias[0] and int(x.get('value'), 0) == values[0] for x in src)):
                        # Retail statistics use the corresponding weapon family.
                        values = (int(next(x for x in dst if x.get('name') == statistic_alias[1]).get('value'), 0),)
                    else:
                        values = (translate_enum(values[0], src, dst),)
                struct.pack_into('>' + fmt, out, at, *values)
                width = struct.calcsize('>' + fmt)
            if at + width > size or covered.intersection(range(at, at + width)):
                raise ValueError(f'{name}: overlapping or out-of-bounds schema field')
            covered.update(range(at, at + width))
        if len(covered) != size:
            raise ValueError(f'{path}: schema leaves {size-len(covered)} bytes undescribed')
        return bytes(out)
