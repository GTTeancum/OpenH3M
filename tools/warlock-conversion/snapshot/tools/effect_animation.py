"""Preserve single-pass effect animations using named native shader registers."""
import struct
from tag_functions import convert_function


def convert_animation(source, target, builder, source_strings, target_strings, source_post, target_post):
    s, c, b = source, target, builder
    st = s.tags[s.u(source_post + 12) & 65535]['offset']
    tt = c.tags[c.u(target_post + 12) & 65535]['offset']

    def ranges(cache, at, size):
        return [cache.unpack('H', row)[0] for row in cache.block(at, size)]

    # One entry point/one pass is the observed decal layout. Reject multipass
    # cases until per-entry remapping can be represented without ambiguity.
    for cache, post, template in ((s, source_post, st), (c, target_post, tt)):
        if ranges(cache, template + 36, 2) != [1024] or cache.u(template + 48) != 1:
            raise ValueError('Animated effects require one template entry point and pass')
    if ranges(s, source_post + 56, 2) != [1024] or s.u(source_post + 68) != 1:
        raise ValueError('Animated effect postprocess requires one entry point and pass')

    def sliced(rows, packed):
        start, count = packed & 1023, packed >> 10
        if start + count > len(rows):
            raise ValueError('Effect animation routing range exceeds its block')
        return rows[start:start + count]

    source_routes = s.block(source_post + 80, 4)
    source_pass = s.block(source_post + 68, 6)[0]
    sp = s.block(st + 48, 32)[0]
    tp = c.block(tt + 48, 28)[0]
    sr, tr = s.block(st + 60, 4), c.block(tt + 60, 4)
    overlays = s.block(source_post + 92, 36)
    converted_routes, seen = {}, set()
    # Postprocess texture/vertex/pixel ranges correspond to template usages
    # 0/1/4. Registers differ across platforms; constant indices are already
    # checked by the material importer against their ordered parameter names.
    for usage, template_usage in enumerate((0, 1, 4)):
        route_rows = sliced(source_routes, s.unpack('H', source_pass + usage * 2)[0])
        source_template_rows = sliced(sr, s.unpack('H', sp + template_usage * 2)[0])
        target_template_rows = sliced(tr, c.unpack('H', tp + template_usage * 2)[0])
        for row in route_rows:
            register, function, constant = s.unpack('HBB', row)
            if function >= len(overlays):
                raise ValueError('Effect routing references a missing animation function')
            matches = [s.unpack('HBB', r) for r in source_template_rows
                       if s.unpack('HBB', r)[:2] == (register, constant)]
            native = [c.unpack('HBB', r) for r in target_template_rows
                      if c.unpack('HBB', r)[1] == constant]
            if len(matches) != 1 or len(native) != 1 or matches[0][2] != native[0][2]:
                raise ValueError('Animated effect has ambiguous or incompatible register routing')
            payload = struct.pack('>HBB', native[0][0], function, constant)
            if row in converted_routes and converted_routes[row] != payload:
                raise ValueError('Animated effect route is shared across incompatible usages')
            converted_routes[row] = payload
            seen.add(function)
    if len(converted_routes) != len(source_routes) or seen != set(range(len(overlays))):
        raise ValueError('Animated effect has unreferenced routing or functions')

    functions = bytearray()
    for row in overlays:
        kind, input_id, range_id, period = s.unpack('IIIf', row)
        if kind > 8:
            raise ValueError('Unsupported effect animation function type')
        size, pointer = s.u(row + 16), s.pointer(s.u(row + 28))
        if pointer < 0 or pointer + size > len(s.data):
            raise ValueError('Effect animation function exceeds source cache')
        function = convert_function(bytes(s.data[pointer:pointer + size]))
        functions.extend(struct.pack('>IIIf5I', kind,
            source_strings.translate(input_id, target_strings),
            source_strings.translate(range_id, target_strings), period,
            len(function), 0, 0, b.alloc(function), 0))
    payloads = {
        56: (1, struct.pack('>H', 1024)),
        68: (1, struct.pack('>3H', *s.unpack('3H', source_pass))),
        80: (len(source_routes), b''.join(converted_routes[row] for row in source_routes)),
        92: (len(overlays), functions),
    }
    return {offset: struct.pack('>III', count, b.alloc(data) if data else 0, 0)
            for offset, (count, data) in payloads.items()}
