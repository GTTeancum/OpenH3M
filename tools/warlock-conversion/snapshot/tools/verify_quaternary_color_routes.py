"""Audit native fourth-change-color routes through explicit entry/pass mappings."""
import argparse
import json
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable


def audit(path, template):
    c = Cache(path)
    try:
        roots = [(i, t['offset']) for i, t in c.tags.items()
                 if t['group'] == 'rmt2' and c.name(i) == template]
        if len(roots) != 1:
            raise ValueError('Expected one native template')
        tag, root = roots[0]
        pixel = c.tags[c.u(root + 28) & 65535]['offset']
        entries = c.block(root + 36, 2)
        shader_entries = c.block(pixel + 4, 2)
        passes = c.block(root + 48, 28)
        routes = c.block(root + 60, 4)
        programs = c.block(pixel + 20, 80)
        strings = StringTable(c)
        observations = []
        for entry, address in enumerate(entries):
            packed = c.unpack('H', address)[0]
            if not packed >> 10:
                continue
            shader_index, shader_count = c.unpack('BB', shader_entries[entry])
            if not shader_count:
                continue
            if packed >> 10 != 1 or shader_count != 1:
                raise ValueError('Unsupported multi-pass native entry')
            registers = {strings.text(c.u(r)): c.unpack('HBB', r + 4)
                         for r in c.block(programs[shader_index] + 40, 8)}
            value = registers.get('quaternary_change_color')
            if value is None:
                continue
            register, count, kind = value
            if count != 1 or kind != 2:
                raise ValueError('Unexpected change-color reflection')
            row = passes[packed & 1023]
            route_range = c.unpack('H', row + 10 * 2)[0]
            matches = [list(c.unpack('HBB', r)) for r in
                       routes[route_range & 1023:(route_range & 1023) + (route_range >> 10)]
                       if c.unpack('H', r)[0] == register]
            if matches != [[register, 18, 0]]:
                raise ValueError('Native fourth-change-color route differs')
            observations.append(dict(entry=entry, shader_index=shader_index,
                pass_index=packed & 1023, register=register, usage=10, source=18, flags=0))
        if not observations:
            raise ValueError('No verified fourth-change-color binding')
        return dict(map=str(path), template=template, tag=tag, observations=observations,
            scope='Native cache binding evidence only; does not establish the runtime value for a BSP instance.')
    finally:
        c.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--template', default=r'shaders\shader_templates\_4_2_0_1_1_2_0_0_0_1')
    args = parser.parse_args()
    print(json.dumps(audit(args.map, args.template), indent=2))
