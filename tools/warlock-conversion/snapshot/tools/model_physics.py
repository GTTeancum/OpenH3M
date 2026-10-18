"""Convert the observed MCC rigid/polyhedron/list physics layouts.

Runtime pointers must be null. Other shapes remain unsupported rather than
being truncated to 32 bits. Layouts are from the paired Assembly schemas.
"""
import struct
from scenario_placements import fields, translate_enum, translate_flags


def convert_model_physics(conv, offset, ss, ds, path):
    vehicle_phantom = path.startswith('vehi:') and ss.get('name') == 'Phantom Shapes'
    if (not vehicle_phantom and not path.startswith('phmo:')) or path.count('/') != 1 or ss.get('name') not in (
            'Rigid Bodies', 'Polyhedra', 'Boxes', 'Lists', 'List Shapes', 'Phantoms', 'Phantom Shapes', 'MOPPs', 'Pills'):
        return None
    from tag_metadata import SCALARS
    block = ss.get('name')
    sizes = {'Rigid Bodies': (192, 176), 'Polyhedra': (160, 128),
             'Boxes': (224, 176), 'Lists': (96, 80), 'List Shapes': (32, 16), 'Phantoms': (88, 44),
             'Phantom Shapes': (960, 816), 'MOPPs': (64, 32), 'Pills': (112, 96)}
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
            if block == 'Polyhedra' or (block == 'Boxes' and key[1] == 1):
                if value < 32 or (value - 32) % source_size:
                    raise ValueError(f'{path}: invalid polyhedron self offset')
                value = (value - 32) // source_size * target_size + 32
            elif block == 'Pills' or (block == 'Boxes' and key[1] == 0):
                if value % source_size:
                    raise ValueError(f'{path}: invalid shape self offset')
                value = value // source_size * target_size
            elif block == 'Lists' and value:
                raise ValueError(f'{path}: unsupported list user data')
            elif block in ('Phantom Shapes', 'MOPPs') and value:
                raise ValueError(f'{path}: unsupported vehicle phantom user data')
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
            if block in ('Polyhedra', 'Boxes', 'Pills') and name == 'Flags':
                # Assembly names only bit 0. These complete values match
                # corresponding MCC/original Sandbox shapes (152 matching
                # tag lists), plus the earlier Armory/equipment comparisons.
                if values[0] not in (0, 10, 32, 33, 46, 49, 54, 55, 56, 57, 58, 60, 64, 66, 69, 70,
                                     73, 76, 81, 86, 87, 90, 102, 139, 144, 145, 157, 171, 178, 202, 221, 222, 228):
                    raise ValueError(f'{path}: unverified polyhedron flags')
            else:
                values = (translate_flags(values[0], src, dst),)
        struct.pack_into('>' + fmt, out, int(dst.get('offset'), 0), *values)
    return bytes(out)
