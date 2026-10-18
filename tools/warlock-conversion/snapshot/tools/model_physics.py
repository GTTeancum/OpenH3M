"""Convert the observed MCC rigid/polyhedron/list physics layouts.

Runtime pointers must be null. Other shapes remain unsupported rather than
being truncated to 32 bits. Layouts are from the paired Assembly schemas.
"""
import struct
from scenario_placements import fields, translate_enum, translate_flags


def convert_model_physics(conv, offset, ss, ds, path):
    if not path.startswith('phmo:') or path.count('/') != 1 or ss.get('name') not in (
            'Rigid Bodies', 'Polyhedra', 'Lists', 'List Shapes', 'Phantoms'):
        return None
    from tag_metadata import SCALARS
    block = ss.get('name')
    sizes = {'Rigid Bodies': (192, 176), 'Polyhedra': (160, 128),
             'Lists': (96, 80), 'List Shapes': (32, 16), 'Phantoms': (88, 44)}
    source_size, target_size = sizes[block]
    if (int(ss.get('elementSize'), 0), int(ds.get('elementSize'), 0)) != sizes[block]:
        raise ValueError(f'{path}: unexpected physics layout')
    out = bytearray(target_size)
    source_fields = fields(ss)
    # Unknown alignment words are not matched by ordinal across layouts.
    for key, src in source_fields.items():
        name = key[0]
        if name == 'Unknown' or name == 'Runtime Shape Pointer Pad':
            at = int(src.get('offset'), 0)
            fmt = SCALARS.get(src.tag.lower(), 'I')
            value = conv.source.unpack(fmt, offset + at)[0]
            if block == 'List Shapes' and at == 12:
                struct.pack_into('>I', out, 8, value)
            elif value:
                raise ValueError(f'{path}: nonzero physics padding at {at:#x}')
    for key, dst in fields(ds).items():
        name = key[0]
        if name == 'Unknown':
            continue
        src = source_fields.get(key)
        if src is None:
            raise ValueError(f'{path}/{name}: missing physics field')
        kind = dst.tag.lower()
        fmt = SCALARS.get(kind)
        source_fmt = 'Q' if src.tag.lower() == 'uint64' else SCALARS.get(src.tag.lower())
        if fmt is None or source_fmt is None:
            raise ValueError(f'{path}/{name}: unsupported physics field')
        values = conv.source.unpack(source_fmt, offset + int(src.get('offset'), 0))
        if name.startswith('Runtime') and 'Pointer' in name and any(values):
            raise ValueError(f'{path}/{name}: populated runtime pointer')
        if name == 'User Data':
            value = values[0]
            if block == 'Polyhedra':
                if value < 32 or (value - 32) % source_size:
                    raise ValueError(f'{path}: invalid polyhedron self offset')
                value = (value - 32) // source_size * target_size + 32
            elif block == 'Lists' and value:
                raise ValueError(f'{path}: unsupported list user data')
            # Phantom user data contains a shape index, not a byte offset.
            values = (value,)
        elif kind == 'stringid':
            values = (conv.strings.translate(values[0], conv.target_strings),)
        elif block == 'Lists' and name == 'w Axis-Aligned Bounding Box Center':
            # MCC serializes a homogeneous point (w=1); retail stores w=0.
            if values[0] not in (0.0, 1.0):
                raise ValueError(f'{path}: unexpected AABB homogeneous component')
            values = (0.0,)
        elif kind.startswith('enum'):
            values = (translate_enum(values[0], src, dst),)
        elif kind.startswith('flags'):
            if block == 'Polyhedra' and name == 'Flags':
                # Assembly labels only bit 0. Native receiver/jump-pad shapes
                # retain the same 0x45/0x90 shape flags as their MCC records.
                # Original armory missile-pod geometry and its projectile confirm 0x46/0x8b.
                if values[0] not in (0x39, 0x45, 0x46, 0x8b, 0x90):
                    raise ValueError(f'{path}: unverified polyhedron flags')
            else:
                values = (translate_flags(values[0], src, dst),)
        struct.pack_into('>' + fmt, out, int(dst.get('offset'), 0), *values)
    return bytes(out)
