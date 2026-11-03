"""Patch exact baseline shader identities in a private cache; never install.

Only matched pixel programs, their reflection, matching template route tables
and dependent animation register destinations may change. Original metadata
outside those fields is checked byte-for-byte.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from build_powerhouse_water_shaders import confined
from build_scenario_checkpoint import resource_salt
from lightmap_register_reservations import require_safe_material_routes, require_safe_shared_float_uploads
from map_builder import MapBuilder
from material_animation_registers import animation_register_updates
from string_ids import StringTable


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch(source, output, profiles, xex):
    source, output, profiles = map(confined, (source, output, profiles))
    if output.exists():
        raise ValueError('Refuse to overwrite a candidate')
    known = {}
    for directory in sorted(profiles.iterdir()):
        if not directory.is_dir() or not (directory / 'register-correction.json').is_file():
            continue
        plan_name = 'route-plan.json' if (directory / 'route-plan.json').is_file() else 'splash-route-plan.json'
        prefix = 'concrete-' if plan_name == 'route-plan.json' else 'splash-'
        old = json.loads((directory / 'baseline' / plan_name).read_text())
        new = json.loads((directory / plan_name).read_text())
        require_safe_material_routes(new)
        require_safe_shared_float_uploads(new)
        assert not new['unresolved'] and old['names'] == new['names']
        signature = []
        for program in sorted(old['programs'], key=lambda p: p['shader']):
            raw = (directory / 'baseline' / (prefix + program['name'] + '.bin')).read_bytes()
            signature.append(digest(raw[struct.unpack_from('>I', raw, 4)[0]:]))
        signature = tuple(signature)
        assert signature not in known, 'Ambiguous baseline shader identities'
        known[signature] = (directory, prefix, old, new)
    assert known, 'No validated shader profiles found'
    b = MapBuilder(source, reserve=0x400000)
    c = b.cache
    strings = StringTable(c)
    allowed, changed, matches = [], [], {}

    def replace(offset, data):
        relative = offset - c.start
        assert 0 <= relative <= len(b.meta) - b.reserve - len(data)
        b.meta[b.reserve + relative:b.reserve + relative + len(data)] = data
        allowed.append((relative, len(data)))

    try:
        for index, tag in c.tags.items():
            if tag['group'] != 'pixl':
                continue
            rows = c.block(tag['offset'] + 20, 80)
            signature = []
            for row in rows:
                pointer = c.u(row + 76)
                if not pointer:
                    signature.append(None)
                    continue
                header = c.pointer(pointer)
                start = c.pointer(c.u(header + 16))
                size = c.u(header + 48)
                signature.append(digest(bytes(c.data[start:start + size])))
            profile = known.get(tuple(signature))
            if profile is None:
                continue
            directory, prefix, old, new = profile
            for program in new['programs']:
                row = rows[program['shader']]
                raw = (directory / (prefix + program['name'] + '.bin')).read_bytes()
                debug_size = struct.unpack_from('>I', raw, 4)[0]
                info = bytearray(40)
                struct.pack_into('>I', info, 16, b.alloc(raw[debug_size:]))
                info.extend(raw[:debug_size])
                old_ids = {strings.text(c.u(r)).lower(): c.u(r) for r in c.block(row + 40, 8)}
                assert set(old_ids) == {r['name'].lower() for r in program['registers']}
                reflection = b''.join(struct.pack('>IHBB', old_ids[r['name'].lower()],
                    r['register'], r['count'], r['set']) for r in program['registers'])
                assembly = (directory / (prefix + program['name'] + '.asm')).read_text()
                gprs = int(re.search(r'PsMaxReg=(\d+)', assembly).group(1)) + 1
                data = bytearray(c.data[row:row + 80])
                data[:40] = bytes(40)
                struct.pack_into('>III', data, 40, len(program['registers']), b.alloc(reflection), 0)
                data[56:68] = bytes(12)
                struct.pack_into('>II', data, 72, gprs, b.alloc(info))
                replace(row, data)
            matches[index] = profile
            changed.append(dict(pixel_tag=index, profile=directory.name))
        assert matches, 'No exact shader profiles matched'
        assert {v[0] for v in matches.values()} == {v[0] for v in known.values()}, 'Some requested profiles did not match'
        templates = []
        animation_templates = {}
        for index, tag in c.tags.items():
            if tag['group'] != 'rmt2':
                continue
            pixel = c.u(tag['offset'] + 28) & 65535
            if pixel not in matches:
                continue
            directory, _, old, new = matches[pixel]
            entries = c.block(tag['offset'] + 36, 2)
            passes = c.block(tag['offset'] + 48, 28)
            routes = c.block(tag['offset'] + 60, 4)
            updates = {}
            for previous, program in zip(old['programs'], new['programs']):
                assert previous['entry'] == program['entry']
                packed = c.unpack('H', entries[program['entry']])[0]
                assert packed >> 10 == 1
                pass_index = packed & 1023
                for usage in range(12):
                    packed_route = c.unpack('H', passes[pass_index] + usage * 2)[0]
                    actual = [list(c.unpack('HBB', r)) for r in
                              routes[packed_route & 1023:(packed_route & 1023) + (packed_route >> 10)]]
                    assert actual == previous['usages'][usage], 'Existing material routes differ from baseline'
                updates[pass_index] = program['usages']
            payload = bytearray()
            for pass_index, row in enumerate(passes):
                data = bytearray(c.data[row:row + 28])
                for usage in range(12):
                    packed = c.unpack('H', row + usage * 2)[0]
                    values = (updates[pass_index][usage] if pass_index in updates else
                              [c.unpack('HBB', r) for r in routes[packed & 1023:(packed & 1023) + (packed >> 10)]])
                    start, count = len(payload) // 4, len(values)
                    assert start <= 1023 and count <= 63
                    struct.pack_into('>H', data, usage * 2, start | count << 10)
                    payload.extend(b''.join(struct.pack('>HBB', *v) for v in values))
                replace(row, data)
            replace(tag['offset'] + 60, struct.pack('>III', len(payload) // 4, b.alloc(payload), 0))
            animation_templates[index] = updates
            templates.append(dict(template_tag=index, pixel_tag=pixel, profile=directory.name))
        assert set(matches) == {r['pixel_tag'] for r in templates}, 'Matched shader has no template'
        animation_edits, animation_audit = animation_register_updates(c, set(animation_templates), animation_templates)
        for offset, register in animation_edits.items():
            replace(offset, struct.pack('>H', register))
        original = bytearray(c.data[c.start:c.start + c.u(0x490)])
        updated = bytearray(b.meta[b.reserve:])
        for offset, size in allowed:
            original[offset:offset + size] = updated[offset:offset + size]
        assert original == updated, 'Unrelated original metadata changed'
        result = b.finish(resource_salt(xex))
        output.write_bytes(result)
        return dict(source=str(source), output=str(output), sha256=digest(result),
                    pixels=changed, templates=templates, allocated_metadata=b.used,
                    animation_register_edits=len(animation_edits), animation_routes=animation_audit,
                    unchanged_original_metadata_outside_shader_fields=True,
                    raw_asset_payload_unchanged=not b.raw.strip(b'\0'),
                    scope='Private shader and animation-register patch. No geometry, placements, material values, animation functions or flare changes. Native validation pending.')
    finally:
        b.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--profiles', required=True)
    parser.add_argument('--xex', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(patch(args.source, args.output, args.profiles, args.xex), indent=2))
