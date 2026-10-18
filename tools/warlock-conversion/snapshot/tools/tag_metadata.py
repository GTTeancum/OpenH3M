"""Schema-based MCC-to-retail metadata conversion with explicit dependencies.

Resource datums and opaque data require dedicated handlers; this converter never
copies platform pointers or compiled data blindly. Callers own a scratch builder
and publish it only after the complete dependency graph has converted.
"""
import struct
from scenario_placements import FORMATS, fields, translate_flags, translate_enum


SCALARS = dict(FORMATS, uint8='B', uint16='H', uint32='I', rangef='2f',
               colorf='3f', vector3='3f', vector4='4f', point2='2f',
               plane3='4f', degree2='2f')


class MetadataConverter:
    def __init__(self, source, builder, strings, target_strings, tag_reference,
                 data_reference=None, resource_reference=None):
        self.source, self.builder = source, builder
        self.strings, self.target_strings = strings, target_strings
        self.tag_reference = tag_reference
        self.data_reference = data_reference
        self.resource_reference = resource_reference

    def convert(self, offset, source_schema, target_schema, path='', depth=0):
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
            if src.tag.lower() == 'tagblock' and self.source.u(at) == 0:
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
                if kind == 'tagblock' and key[0] in ('Predicted Resources', 'Predicted Bitmaps'):
                    covered.update(range(at, at + 12))
                    continue
                raise ValueError(f'{name}: retail-only field needs a default')
            if src.tag.lower() != kind:
                raise ValueError(f'{name}: source/retail field types differ')
            read = offset + int(src.get('offset'), 0)
            if kind == 'tagblock':
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
            elif kind == 'undefined':
                if self.source.u(read):
                    raise ValueError(f'{name}: nonzero unknown field')
                width = 4
            else:
                fmt = SCALARS.get(kind)
                if fmt is None:
                    raise ValueError(f'{name}: unsupported field type {kind}')
                values = self.source.unpack(fmt, read)
                if kind == 'stringid':
                    values = (self.strings.translate(values[0], self.target_strings),)
                elif kind == 'datum' and values[0] != 0xffffffff:
                    if self.resource_reference is None:
                        raise ValueError(f'{name}: resource datum needs conversion')
                    values = (self.resource_reference(name, values[0]),)
                elif kind.startswith('flags'):
                    values = (translate_flags(values[0], src, dst),)
                elif kind.startswith('enum'):
                    values = (translate_enum(values[0], src, dst),)
                struct.pack_into('>' + fmt, out, at, *values)
                width = struct.calcsize('>' + fmt)
            if at + width > size or covered.intersection(range(at, at + width)):
                raise ValueError(f'{name}: overlapping or out-of-bounds schema field')
            covered.update(range(at, at + width))
        if len(covered) != size:
            raise ValueError(f'{path}: schema leaves {size-len(covered)} bytes undescribed')
        return bytes(out)
