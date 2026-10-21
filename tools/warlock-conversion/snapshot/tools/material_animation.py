"""Remap authored rmsh animation routes across native shader entry points."""
import struct
from tag_functions import convert_function


def convert_material_animation(materials, source_post, target_post):
    s, b, registry = materials.source, materials.builder, materials.registry
    source_template = s.tags[s.u(source_post + 12) & 65535]['offset']
    datum = struct.unpack_from('>I', target_post, 12)[0]
    target_template = struct.unpack_from('>I', registry.tags, (datum & 65535) * 8 + 4)[0]

    def target_rows(at, stride):
        count, pointer = struct.unpack('>II', b.read(at, 8))
        return [b.read(pointer + j * stride, stride) for j in range(count)]

    def source_rows(at, stride):
        return [bytes(s.data[row:row + stride]) for row in s.block(at, stride)]

    def indices(payload, endian):
        return [struct.unpack(endian + 'H', row)[0] for row in payload]

    def span(packed, count):
        start, length = packed & 1023, packed >> 10
        if start + length > count:
            raise ValueError('Material animation range exceeds table')
        return range(start, start + length)

    se = indices(source_rows(source_template + 36, 2), '<')
    te = indices(target_rows(target_template + 36, 2), '>')
    ae = indices(source_rows(source_post + 56, 2), '<')
    sp, tp = source_rows(source_template + 48, 32), target_rows(target_template + 48, 28)
    sr, tr = source_rows(source_template + 60, 4), target_rows(target_template + 60, 4)
    ap, ar = source_rows(source_post + 68, 6), source_rows(source_post + 80, 4)
    overlays = source_rows(source_post + 92, 36)
    if len(se) != len(te) or len(ae) != len(se):
        raise ValueError('Material animation entry points differ across platforms')
    source_names = materials.parameters(s, materials.source_strings, source_post)
    target_names = []
    for offset in (108, 72):
        target_names.append([materials.target_strings.text(struct.unpack('>I', row)[0])
                             for row in target_rows(target_template + offset, 4)])
    routed = {}
    seen_functions = set()
    seen_routes = set()
    for entry in range(len(se)):
        source_passes = list(span(se[entry], len(sp)))
        target_passes = list(span(te[entry], len(tp)))
        animation_passes = list(span(ae[entry], len(ap)))
        if not animation_passes:
            continue
        # MCC may list an empty animation pass for an entry absent on retail.
        # No function/register routes exist to translate in that case.
        if not target_passes and all(
                not (struct.unpack_from('<H', ap[ai], usage*2)[0] >> 10)
                for ai in animation_passes for usage in range(3)):
            continue
        if len(source_passes) != len(target_passes) or len(source_passes) != len(animation_passes):
            raise ValueError('Material animation pass counts differ')
        for si, ti, ai in zip(source_passes, target_passes, animation_passes):
            usages = []
            for usage, template_usage in enumerate((0, 1, 4)):
                output = []
                src_routes = span(struct.unpack_from('<H', sp[si], template_usage * 2)[0], len(sr))
                dst_routes = span(struct.unpack_from('>H', tp[ti], template_usage * 2)[0], len(tr))
                for ri in span(struct.unpack_from('<H', ap[ai], usage * 2)[0], len(ar)):
                    register, function, constant = struct.unpack('<HBB', ar[ri])
                    if function >= len(overlays):
                        raise ValueError('Material animation function index outside table')
                    kind = 0 if usage == 0 else 1
                    name = source_names[kind][constant]
                    target_constant = target_names[kind].index(name)
                    source_matches = [struct.unpack('<HBB', sr[r]) for r in src_routes
                                      if struct.unpack('<HBB', sr[r])[:2] == (register, constant)]
                    target_matches = [struct.unpack('>HBB', tr[r]) for r in dst_routes
                                      if struct.unpack('>HBB', tr[r])[1] == target_constant]
                    if (len(source_matches) != 1 or len(target_matches) != 1
                            or source_matches[0][2] != target_matches[0][2]):
                        raise ValueError('Material animation shader register mapping is ambiguous')
                    output.append(struct.pack('>HBB', target_matches[0][0], function, target_constant))
                    seen_functions.add(function)
                    seen_routes.add(ri)
                usages.append(output)
            if ti in routed and routed[ti] != usages:
                raise ValueError('Shared material pass has conflicting animations')
            routed[ti] = usages
    if seen_routes != set(range(len(ar))) or seen_functions != set(range(len(overlays))):
        raise ValueError('Unmapped material animation data')
    routes, passes = bytearray(), bytearray()
    for ti in range(len(tp)):
        for rows in routed.get(ti, ([], [], [])):
            start = len(routes) // 4
            if start > 1023 or len(rows) > 63:
                raise ValueError('Material animation routing exceeds packed range')
            passes.extend(struct.pack('>H', (len(rows) << 10) | start))
            routes.extend(b''.join(rows))
    functions = bytearray()
    for row in overlays:
        kind, input_id, range_id, period = struct.unpack_from('<IIIf', row)
        size, pointer = struct.unpack_from('<I', row, 16)[0], s.pointer(struct.unpack_from('<I', row, 28)[0])
        function = convert_function(bytes(s.data[pointer:pointer + size]))
        functions.extend(struct.pack('>IIIf5I', kind,
            materials.source_strings.translate(input_id, materials.target_strings),
            materials.source_strings.translate(range_id, materials.target_strings), period,
            len(function), 0, 0, b.alloc(function), 0))
    payloads = {56: (len(te), struct.pack('>' + 'H' * len(te), *te)),
                68: (len(tp), passes), 80: (len(routes) // 4, routes),
                92: (len(overlays), functions)}
    for offset, (count, data) in payloads.items():
        struct.pack_into('>III', target_post, offset, count, b.alloc(data) if data else 0, 0)
    return len(overlays)
