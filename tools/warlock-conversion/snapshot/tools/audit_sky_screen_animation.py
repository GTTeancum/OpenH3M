"""Text-only audit of Sky Bridge screen_lines animation consumers."""
import hashlib
import json
from pathlib import Path
import struct

from cache_reader import Cache
from string_ids import StringTable
from tag_functions import convert_function


def audit(source):
    strings = StringTable(source)
    tag = source.tags[12515]
    assert tag['group'] == 'rmsh' and source.name(12515).endswith('screen_lines')
    post, = source.block(tag['offset'] + 40, 140)
    template = source.tags[source.u(post + 12) & 65535]['offset']
    names = {usage: [strings.text(source.u(x)) for x in source.block(template + off, 4)]
             for usage, off in ((0, 108), (4, 72), (5, 84), (6, 96))}
    routes = source.block(post + 80, 4)
    passes = source.block(post + 68, 6)
    functions = source.block(post + 92, 36)
    template_routes = source.block(template + 60, 4)
    template_passes = source.block(template + 48, 32)
    entries = source.block(template + 36, 2)
    animation_entries = source.block(post + 56, 2)
    assert len(entries) == len(animation_entries)

    def span(packed, rows):
        start, count = packed & 1023, packed >> 10
        assert start + count <= len(rows)
        return range(start, start + count)

    consumers, seen = [], set()
    for entry, (ep, ae) in enumerate(zip(entries, animation_entries)):
        tp = list(span(source.unpack('H', ep)[0], template_passes))
        ap = list(span(source.unpack('H', ae)[0], passes))
        assert len(tp) == len(ap)
        for ti, ai in zip(tp, ap):
            for usage, template_usage in enumerate((0, 1, 4)):
                for ri in span(source.unpack('H', passes[ai] + usage * 2)[0], routes):
                    register, function, constant = source.unpack('HBB', routes[ri])
                    assert function < len(functions)
                    name = names[0 if usage == 0 else 4][constant]
                    matches = [source.unpack('HBB', template_routes[r]) for r in span(
                        source.unpack('H', template_passes[ti] + template_usage * 2)[0], template_routes)
                        if source.unpack('HBB', template_routes[r])[:2] == (register, constant)]
                    assert len(matches) == 1
                    consumers.append(dict(entry=entry, usage=usage, route=ri, register=register,
                                          function=function, constant=constant, name=name, flags=matches[0][2]))
                    seen.add(ri)
    assert seen == set(range(len(routes)))
    assert {x['function'] for x in consumers} == set(range(len(functions)))
    payloads = []
    for index, row in enumerate(functions):
        kind, input_id, range_id, period = source.unpack('IIIf', row)
        size = source.u(row + 16)
        pointer = source.pointer(source.u(row + 28))
        raw = bytes(source.data[pointer:pointer + size])
        converted = convert_function(raw)
        payloads.append(dict(index=index, kind=kind, input=strings.text(input_id),
                             range=strings.text(range_id), period=period, bytes=size,
                             source_hex=raw.hex(), converted_hex=converted.hex(),
                             sha256=hashlib.sha256(raw).hexdigest()))
    value = source.unpack('4f', source.block(post + 28, 16)[names[4].index('primary_change_color_blend')])
    safe = value == (0.,) * 4 and all(x['name'] != 'primary_change_color_blend' for x in consumers)
    return dict(material=source.name(12515), names=names, functions=payloads, consumers=consumers,
                animated_parameters=sorted({x['name'] for x in consumers}),
                primary_change_color_blend=value, zero_blend_specialization_safe=safe)


if __name__ == '__main__':
    source = Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map', True)
    try:
        report = audit(source)
    finally:
        source.close()
    out = Path('work/sky-bridge/screen-native-01/animation-audit.json')
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ('animated_parameters', 'primary_change_color_blend', 'zero_blend_specialization_safe')}))
