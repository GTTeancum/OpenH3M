"""Convert the observed MCC rigid/polyhedron/list physics layouts.

Runtime pointers must be null. Other shapes remain unsupported rather than
being truncated to 32 bits. Layouts are from the paired Assembly schemas.
"""
import struct
from scenario_placements import fields, translate_enum, translate_flags


def convert_model_physics(conv, offset, ss, ds, path):
    vehicle_phantom = path.startswith('vehi:') and ss.get('name') == 'Phantom Shapes'
    creature_shapes = {'Dead Sphere Shapes': 'Spheres', 'Sphere Shapes': 'Spheres', 'Pill Shapes': 'Pills'}
    creature_sphere = path.startswith('crea:') and ss.get('name') in creature_shapes
    if creature_sphere:
        # Both MCC and retail creature blocks are identical to phmo Spheres;
        # reuse its pointer-width, user-data offset and numeric conversion.
        import copy
        block_name = creature_shapes[ss.get('name')]
        ss, ds = copy.deepcopy(ss), copy.deepcopy(ds)
        ss.set('name', block_name)
        ds.set('name', block_name)
    if (not vehicle_phantom and not creature_sphere and not path.startswith('phmo:')) or path.count('/') != 1 or ss.get('name') not in (
            'Rigid Bodies', 'Polyhedra', 'Boxes', 'Triangles', 'Lists', 'List Shapes', 'Phantoms', 'Phantom Shapes', 'MOPPs', 'Pills', 'Spheres'):
        return None
    from tag_metadata import SCALARS
    block = ss.get('name')
    sizes = {'Rigid Bodies': (192, 176), 'Polyhedra': (160, 128),
             'Boxes': (224, 176), 'Triangles': (144, 128), 'Lists': (96, 80), 'List Shapes': (32, 16), 'Phantoms': (88, 44),
             'Phantom Shapes': (960, 816), 'MOPPs': (64, 32), 'Pills': (112, 96), 'Spheres': (160, 112)}
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
            if block == 'List Shapes' and at in (8, 12):
                # PhysicsModel.ListShape: CollisionFilter, ShapeSize follow
                # the platform-width shape reference. Preserve both words.
                struct.pack_into('>I', out, at - 4, value)
            elif block == 'List Shapes' and at in (20, 24, 28):
                # MCC's child record aligns 20 bytes of fields to 32 bytes.
                # Official H3EK output leaves arbitrary compiler heap contents
                # in this tail (including UTF-16 names), not just CB fill.
                # Retail has no tail after NumChildShapes at offset 12.
                # The pointer's high word at offset 4 remains checked below.
                continue
            elif block == 'Triangles' and at in (0x48, 0x4c):
                # PointA is aligned to 16 bytes after the welding fields.
                # PhysicsModel.Triangle declares no fields in this gap.
                continue
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
            if block == 'Polyhedra' or (block in ('Boxes', 'Spheres') and key[1] == 1):
                if value < 32 or (value - 32) % source_size:
                    raise ValueError(f'{path}: invalid polyhedron self offset')
                value = (value - 32) // source_size * target_size + 32
            elif block in ('Pills', 'Triangles') or (block in ('Boxes', 'Spheres') and key[1] == 0):
                if value % source_size:
                    raise ValueError(f'{path}: invalid shape self offset')
                value = value // source_size * target_size
            elif block == 'Lists' and value:
                raise ValueError(f'{path}: unsupported list user data')
            elif (vehicle_phantom and key[1] in (1, 2) and value == key[1]):
                # Embedded phantom user data identifies the child, not a
                # byte offset. Retail Chopper/Warthog/Elephant use 1;
                # Scorpion additionally uses 2, matching the MCC records.
                pass
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
            if block in ('Polyhedra', 'Boxes', 'Pills', 'Spheres', 'Triangles') and name == 'Flags':
                # Assembly names only bit 0. These complete values match
                # corresponding MCC/original Sandbox shapes (152 matching
                # tag lists), plus the earlier Armory/equipment comparisons.
                # Extended against same-named Resuscitation/disc models only
                # where all shape flag values and row indices match exactly.
                if values[0] not in (0, 10, 32, 33, 36, 38, 46, 49, 54, 55, 56, 57, 58, 60, 64, 65, 66, 69, 70,
                                     72, 73, 76, 78, 79, 81, 82, 84, 86, 87, 90, 91, 94, 96, 102, 117,
                                     139, 144, 145, 154, 157, 171, 178, 187, 202, 212, 213, 215,
                                     221, 222, 223, 228, 232, 237):
                    # Assembly mislabels Shape+6. TagTool PhysicsModel.Shape
                    # defines this as RuntimeMaterialType (GlobalMaterial),
                    # not a bitmask. Resolve unfamiliar values by the shape's
                    # local material and the target's actual global table.
                    owner_name = path.split('/', 1)[0][5:]
                    owner = next(t for i,t in conv.source.tags.items()
                                 if t['group'] == 'phmo' and conv.source.name(i) == owner_name)
                    local = conv.source.unpack('h', offset + 4)[0]
                    materials = conv.source.block(owner['offset'] + 0x64, 12)
                    if not 0 <= local < len(materials):
                        raise ValueError(f'{path}: invalid local physics material')
                    material = conv.strings.text(conv.source.u(materials[local] + 4))
                    if not material:
                        # An unset explicit global name can use a local name
                        # that itself identifies a stock global material.
                        material = conv.strings.text(conv.source.u(materials[local]))
                    target_cache = conv.builder.cache
                    globals_tag = next(t for t in target_cache.tags.values() if t['group'] == 'matg')
                    matches = [i for i,row in enumerate(target_cache.block(globals_tag['offset'] + 0x17c, 0x170))
                               if conv.target_strings.text(target_cache.u(row)) == material]
                    if len(matches) != 1:
                        raise ValueError(f'{path}: unresolved global physics material {material!r}')
                    values = (matches[0],)
            else:
                values = (translate_flags(values[0], src, dst),)
        struct.pack_into('>' + fmt, out, int(dst.get('offset'), 0), *values)
    return bytes(out)
