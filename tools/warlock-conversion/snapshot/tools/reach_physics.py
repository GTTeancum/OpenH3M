"""Narrow Reach-to-retail physics conversion for fixed Forerunner pieces.

Offsets come from paired Assembly schemas; runtime shape IDs were compared
against the same Reach pieces in the working Halo 3 workshop cache. Dynamic
objects, phantom forces and unrelated shapes deliberately require review.
"""
import struct
import math
from scenario_placements import fields, translate_enum
from tag_metadata import SCALARS
from collision_physics import retail_mopp


def convert_tag_mopp(header,code):
    """Reach's 96-byte resource TagMopp header -> H3's 64-byte header.

    Caller must allocate code and supply the data-block fixup at native +52.
    Unlike convert_mopp, input bytecode is a separately referenced tag block.
    """
    if len(header)!=96:raise ValueError('Expected Reach resource MOPP header')
    if any(struct.unpack_from('<Q',header,p)[0] for p in (0,16,48)):
        raise ValueError('Reach resource MOPP has runtime pointers/user data')
    if struct.unpack_from('<I',header,24)[0]:
        raise ValueError('Reach resource MOPP uses unreviewed type')
    size,capacity=struct.unpack_from('<II',header,56)
    if size!=len(code) or struct.unpack_from('<I',header,80)[0]!=size or (capacity&0x7fffffff)<size:
        raise ValueError('Reach resource MOPP allocation mismatch')
    if header[64] not in (0,1) or header[92] not in (0,1):
        raise ValueError('Unknown Reach MOPP build type')
    if header[64]!=header[92]:raise ValueError('Reach runtime/tag MOPP build types disagree')
    if any(header[12:16]+header[28:32]+header[65:80]+header[93:96]):
        raise ValueError('Nonzero unrepresented Reach MOPP metadata')
    out=bytearray(64)
    struct.pack_into('>HH',out,4,*struct.unpack_from('<HH',header,8))
    struct.pack_into('>4I',out,16,*struct.unpack_from('<4I',header,32))
    struct.pack_into('>II',out,36,size,capacity)
    struct.pack_into('>I',out,48,size)
    out[60]=header[92]
    return bytes(out),bytes(retail_mopp(code))


def convert_mopp(payload):
    """Reach MCC uses an 80-byte header; retail uses an aligned 48-byte one."""
    result = bytearray()
    offset = 0
    while offset < len(payload):
        if offset + 80 > len(payload):
            raise ValueError('Truncated Reach MOPP header')
        if any(struct.unpack_from('<Q', payload, offset + p)[0] for p in (0, 48)):
            raise ValueError('Reach MOPP contains runtime pointers')
        size, capacity = struct.unpack_from('<II', payload, offset + 56)
        if (capacity & 0x7fffffff) < size or struct.unpack_from('<I', payload, offset + 64)[0] != 1:
            raise ValueError('Unreviewed Reach MOPP allocation/build type')
        end = offset + 80 + size
        aligned = (end + 15) & ~15
        if aligned > len(payload):
            raise ValueError('Reach MOPP data outside allocation')
        header = bytearray(48)
        struct.pack_into('>HH', header, 4, *struct.unpack_from('<HH', payload, offset + 8))
        struct.pack_into('>4I', header, 16, *struct.unpack_from('<4I', payload, offset + 32))
        struct.pack_into('>II', header, 36, size, capacity)
        result.extend(header)
        result.extend(retail_mopp(payload[offset + 80:end]))
        result.extend(bytes(aligned - end))
        offset = aligned
    return bytes(result)


def serialize_physics(cache, root, source_schema, target_schema, builder,
                      translate_string, material_index):
    source_fields = fields(source_schema)
    materials = source_fields['Materials', 0]
    # An empty override uses the authored material name. Resolve that name
    # against H3's material table rather than copying Reach's runtime index.
    material_names = [cache.u(row + 8) or cache.u(row) for row in cache.block(
        root + int(materials.get('offset'), 0), int(materials.get('elementSize'), 0))]
    allowed = {'Rigid Bodies', 'Materials', 'Polyhedra', 'Polyhedron Four Vectors',
               'Polyhedron Plane Equations', 'Mass Distributions', 'Lists',
               'List Shapes', 'MOPPs', 'Regions', 'Permutations', 'Nodes'}

    def read(at, field):
        kind = field.tag.lower()
        fmt = SCALARS.get(kind, 'Q' if kind == 'uint64' else None)
        if fmt is None:
            raise ValueError('Unsupported Reach physics scalar: ' + kind)
        return cache.unpack(fmt, at + int(field.get('offset'), 0))

    def convert(at, ss, ds, parent='', ordinal=0):
        name = ss.get('name', 'root')
        sf, df = fields(ss), fields(ds)
        out = bytearray(int(ds.get('baseSize') or ds.get('elementSize'), 0))

        def require(key, expected):
            if read(at, sf[key, 0]) != expected:
                raise ValueError(f'{name}: unsupported {key}')

        if name == 'root':
            scale = read(at, sf['Mass Scale', 0])[0]
            # Reach's compiler has already applied this authoring multiplier
            # to the serialized fixed body's mass; H3 has no authoring field.
            bodies = sf['Rigid Bodies', 0]
            rows = cache.block(at + int(bodies.get('offset'), 0), int(bodies.get('elementSize'), 0))
            mass_field = fields(bodies)['Mass', 0]
            total = sum(read(row, mass_field)[0] for row in rows)
            if not math.isfinite(scale) or scale <= 0 or not math.isclose(
                    total, read(at, sf['Mass', 0])[0], rel_tol=0.00001, abs_tol=0.01):
                raise ValueError('Reach fixed-body mass does not match compiled total')
            require('Flags', (2,))
        elif name == 'Rigid Bodies' and parent == 'root':
            require('Motion Type', (5,))
            require('Proxy Collision Group', (0,))
            require('Collision Group Mask', (0,))
            require('Mass Body Override', (0.0,))
            if read(at, sf['Inertia Tensor Scale', 1]) != (1.0, 1.0, 1.0):
                raise ValueError('Reach per-axis inertia override requires conversion')
        elif name == 'Materials':
            require('Flags', (0,))
        elif name == 'Polyhedra':
            require('Material Flags', (0,))
            require('Use SPU Buffer', (0,))
        elif name == 'Lists':
            for i in range(8):
                require(f'Enabled Children {i}', (-1,))
        elif name == 'MOPPs':
            require('Scale', (0.0,))
            require('Child Size', (0,))
            require('Runtime MOPP Code Pointer 2', (0,))

        for key, dst in df.items():
            label, _ = key
            kind = dst.tag.lower()
            write = int(dst.get('offset'), 0)
            src = sf.get(key)
            # Alignment/runtime-only slots are rebuilt, never copied by ordinal.
            if label == 'Unknown' or label == 'Runtime Shape Pointer Pad':
                continue
            if src is None and (name, label) != ('Polyhedra', 'Flags'):
                raise ValueError(f'{name}: missing Reach field {label}')
            if kind == 'tagblock':
                rows = cache.block(at + int(src.get('offset'), 0), int(src.get('elementSize'), 0))
                if rows and label not in allowed:
                    raise ValueError('Unsupported Reach physics block: ' + label)
                payload = b''.join(convert(row, src, dst, name, index) for index, row in enumerate(rows))
                struct.pack_into('>III', out, write, len(rows), builder.alloc(payload) if rows else 0, 0)
                continue
            if kind == 'dataref':
                if label != 'MOPP Codes':
                    raise ValueError('Unsupported Reach physics data reference')
                pos = at + int(src.get('offset'), 0)
                length = cache.u(pos)
                if length:
                    offset = cache.pointer(cache.u(pos + 12))
                    payload = convert_mopp(bytes(cache.data[offset:offset + length]))
                    struct.pack_into('>I', out, write, len(payload))
                    struct.pack_into('>I', out, write + 12, builder.alloc(payload))
                continue
            fmt = SCALARS.get(kind)
            if fmt is None:
                raise ValueError(f'Unsupported retail physics scalar {kind}')
            if (name, label) == ('Polyhedra', 'Flags'):
                # This unnamed retail short is the runtime material type, not
                # the new Reach material-behavior flags adjacent to its index.
                index = read(at, sf['Material Index', 0])[0]
                if not 0 <= index < len(material_names):
                    raise ValueError('Physics shape material index outside table')
                values = (material_index(material_names[index]),)
            else:
                values = read(at, src)
            if label.startswith('Runtime') and 'Pointer' in label:
                if any(values):
                    raise ValueError('Populated Reach runtime physics pointer: ' + label)
                values = (0,)
            elif name == 'root' and label == 'Flags':
                values = (0,)
            elif label == 'User Data':
                source_stride = int(ss.get('elementSize'), 0)
                target_stride = len(out)
                prefix = 32 if name == 'Polyhedra' else 0
                if values != (ordinal * source_stride + prefix,):
                    raise ValueError(f'{name}: unexpected shape self-offset')
                values = (ordinal * target_stride + prefix,)
            elif label == 'Type' and name in ('Polyhedra', 'Lists', 'MOPPs'):
                source_type, target_type = {'Polyhedra': (6, 8), 'Lists': (9, 10), 'MOPPs': (10, 27)}[name]
                if values != (source_type,):
                    raise ValueError('Unreviewed Havok shape type')
                values = (target_type,)
            elif kind == 'stringid':
                if name == 'Materials' and label == 'Global Material Name' and not values[0]:
                    values = (cache.u(at),)
                values = (translate_string(values[0]),)
            elif label == 'Proxy Collision Group' and values == (0,):
                values = (0,)  # Reach "None" and Halo 3 "NONE".
            elif kind.startswith('enum'):
                values = (translate_enum(values[0], src, dst),)
            elif name == 'Lists' and label == 'w Axis-Aligned Bounding Box Center':
                if values not in ((0.0,), (1.0,)):
                    raise ValueError('Invalid homogeneous bounding-box coordinate')
                values = (0.0,)
            struct.pack_into('>' + fmt, out, write, *values)
        return bytes(out)

    return convert(root, source_schema, target_schema)
