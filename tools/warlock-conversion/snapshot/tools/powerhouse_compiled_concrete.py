"""Experimental native Xenos concrete programs with audited H3 shader interfaces.

The compiler outputs and named route plan are generated inside the repository.
Clone both tags so other native materials retain their original programs.
"""
import hashlib
import json
import re
import struct
from pathlib import Path


def bind_compiled_concrete(materials, post, names, directory, *, blend_mode=0, river=False, grate=False, window=False, opaque_grate=False, corrugated=False):
    if sum((river, grate, window, opaque_grate, corrugated)) > 1:
        raise ValueError('Choose one reviewed material profile')
    if blend_mode != (3 if river else 0):
        raise ValueError('Reviewed compiled material blend mode changed')
    directory = Path(directory).resolve()
    repository = Path(__file__).resolve().parents[4]
    if not directory.is_relative_to(repository):
        raise ValueError('Compiled concrete inputs must stay inside the repository')
    plan = json.loads((directory / 'route-plan.json').read_text())
    compiled = {x['entry']: x for x in json.loads(
        (directory / 'compilation.json').read_text())['programs']}
    audit = json.loads((directory / 'native-interface-audit.json').read_text())
    if (plan['unresolved'] or len(audit) != 12 or
            any(not x['inputs_match'] or any(not r['equal'] for r in x['fixed_register_checks']) for x in audit)):
        raise ValueError('Compiled concrete interface audit has unresolved differences')
    b, registry = materials.builder, materials.registry
    post = bytearray(post)

    def address(datum):
        return struct.unpack_from('>I', registry.tags, (datum & 65535) * 8 + 4)[0]

    def rows(root, offset, stride):
        count, pointer = struct.unpack_from('>II', root, offset)
        return [bytes(b.read(pointer + j * stride, stride)) for j in range(count)]

    root = bytearray(b.read(address(struct.unpack_from('>I', post, 12)[0]), 132))
    pixel = bytearray(b.read(address(struct.unpack_from('>I', root, 28)[0]), 32))
    programs = rows(pixel, 20, 80)
    if len(programs) != len(plan['programs']) or struct.unpack_from('>I', root, 120)[0]:
        raise ValueError('Compiled concrete donor shape changed')
    textures, constants = names
    added_constants = (['bump_detail_coefficient', 'detail_map2', 'detail_map3'] if river else
                       ['bump_detail_coefficient', 'env_tint_color', 'environment_map_specular_contribution'])
    added_textures = ['detail_map2', 'detail_map3'] if river else ['environment_map']
    added_booleans = []
    if grate:
        added_constants = ['specular_tint', 'fresnel_color', 'roughness', 'material_texture', 'albedo_blend', 'use_material_texture']
        added_textures = ['material_texture']
    if window:
        added_constants = ['bump_detail_coefficient', 'height_map', 'height_scale']
        added_textures = ['height_map']
    if opaque_grate:
        added_constants = ['bump_detail_coefficient']
        added_textures = []
    if corrugated:
        added_constants = ['specular_mask_texture', 'self_illum_map', 'self_illum_intensity']
        added_textures = ['specular_mask_texture', 'self_illum_map']
        from lightmap_register_reservations import require_safe_material_routes, require_safe_shared_float_uploads
        require_safe_material_routes(plan)
        require_safe_shared_float_uploads(plan)
        for program in plan['programs']:
            if any(100 <= route[0] < 104 for route in program['usages'][4]):
                raise ValueError('Corrugated material overlaps fourth-color upload block')
            color = [r for r in program['registers'] if r['name'] == 'self_illum_color']
            if color and (color != [dict(name='self_illum_color', set=2, register=102, count=1)]
                          or [102, 18, 0] not in program['usages'][10]):
                raise ValueError('Corrugated fourth-color external binding changed')
    if textures + added_textures != plan['names']['0'] or constants + added_constants != plan['names']['4']:
        raise ValueError('Compiled concrete donor parameter names changed')
    for offset,expected in ((108,textures),(72,constants)):
        actual=[materials.target_strings.text(struct.unpack('>I',x)[0]) for x in rows(root,offset,4)]
        if actual != expected:
            raise ValueError('Reused native template parameter order differs from donor')
    pixel_entries=rows(pixel,4,2)
    entries = rows(root, 36, 2)
    passes = [bytearray(x) for x in rows(root, 48, 28)]
    old_routes = rows(root, 60, 4)
    new_usages = {}
    evidence = []
    for program in plan['programs']:
        entry, name, index = program['entry'], program['name'], program['shader']
        if tuple(pixel_entries[entry]) != (index,1):
            raise ValueError('Reused native pixel entry mapping differs from donor')
        raw = (directory / ('concrete-' + name + '.bin')).read_bytes()
        if not compiled[entry]['success'] or hashlib.sha256(raw).hexdigest() != compiled[entry]['sha256']:
            raise ValueError('Compiled concrete bytecode does not match audited manifest')
        magic, debug_size, code_size = struct.unpack_from('>III', raw)
        if magic >> 16 != 0x102a or debug_size < 28 or code_size == 0 or debug_size + code_size != len(raw):
            raise ValueError('Compiled concrete debug/microcode bounds invalid')
        assembly = (directory / ('concrete-' + name + '.asm')).read_text()
        registers = [dict(name=n, set={'b':0,'i':1,'c':2,'s':3}[kind], register=int(reg), count=int(count))
            for n,kind,reg,count in re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',assembly,re.M)]
        if registers != program['registers']:
            raise ValueError('Compiled concrete reflection differs from route plan')
        # H3 also binds these shared textures outside material-route updates.
        # Compiler-selected slots can therefore read stale or vertex-fetch data
        # even when every named material route has been remapped correctly.
        fixed_samplers = {'albedo_texture': 10, 'normal_texture': 11,
                          'lightprobe_texture_array': 12,
                          'dominant_light_intensity_map': 13,
                          'scene_ldr_texture': 10, 'depth_buffer': 11}
        for register in registers:
            expected = fixed_samplers.get(register['name'].lower())
            if expected is not None and (register['set'], register['register'], register['count']) != (3, expected, 1):
                raise ValueError('Compiled shader changes an H3 fixed sampler: ' + register['name'])
        info = bytearray(40)
        struct.pack_into('>I', info, 16, b.alloc(raw[debug_size:]))
        info.extend(raw[:debug_size])
        row = bytearray(programs[index])
        row[:40] = bytes(40)
        reflection = b''.join(struct.pack('>IHBB', materials.target_strings.id_for_text(v['name'].lower()),
            v['register'], v['count'], v['set']) for v in registers)
        struct.pack_into('>III', row, 40, len(registers), b.alloc(reflection), 0)
        row[56:68] = bytes(12)
        gprs = int(re.search(r'PsMaxReg=(\d+)', assembly).group(1)) + 1
        struct.pack_into('>II', row, 72, gprs, b.alloc(info))
        programs[index] = bytes(row)
        packed = struct.unpack('>H', entries[entry])[0]
        if packed >> 10 != 1:
            raise ValueError('Compiled concrete needs one pass per entry')
        new_usages[packed & 1023] = program['usages']
        evidence.append(dict(entry=entry, name=name, sha256=compiled[entry]['sha256'], gprs=gprs))
    struct.pack_into('>III', pixel, 20, len(programs), b.alloc(b''.join(programs)), 0)
    pixel_datum, _ = registry.newtag('pixl', pixel)
    struct.pack_into('>I', root, 28, pixel_datum)
    routes = bytearray()
    for index, p in enumerate(passes):
        for usage in range(12):
            packed = struct.unpack_from('>H', p, usage * 2)[0]
            if index in new_usages:
                payload = b''.join(struct.pack('>HBB', *x) for x in new_usages[index][usage])
            else:
                payload = b''.join(old_routes[packed & 1023:(packed & 1023) + (packed >> 10)])
            start, count = len(routes)//4, len(payload)//4
            if start > 1023 or count > 63:
                raise ValueError('Compiled concrete routing exceeds H3 limits')
            struct.pack_into('>H', p, usage * 2, start | count << 10)
            routes.extend(payload)
    real_names = b''.join(rows(root,72,4)) + b''.join(
        struct.pack('>I', materials.target_strings.id_for_text(n)) for n in added_constants)
    texture_names = b''.join(rows(root,108,4)) + b''.join(
        struct.pack('>I', materials.target_strings.id_for_text(n)) for n in added_textures)
    boolean_rows = rows(root,96,4)
    boolean_names = [materials.target_strings.text(struct.unpack('>I', x)[0]) for x in boolean_rows]
    if boolean_names + added_booleans != plan['names']['6']:
        raise ValueError('Compiled material donor boolean names changed')
    if added_booleans:
        payload = b''.join(boolean_rows) + b''.join(struct.pack('>I', materials.target_strings.id_for_text(n)) for n in added_booleans)
        struct.pack_into('>III', root, 96, len(boolean_names)+len(added_booleans), b.alloc(payload), 0)
    for offset,count,payload in ((48,len(passes),b''.join(passes)),(60,len(routes)//4,routes),
                                 (72,len(constants)+len(added_constants),real_names),
                                 (108,len(textures)+len(added_textures),texture_names)):
        struct.pack_into('>III',root,offset,count,b.alloc(payload),0)
    template_datum, _ = registry.newtag('rmt2',root)
    struct.pack_into('>I',post,12,template_datum)
    count,pointer = struct.unpack_from('>II',post,28)
    if count != len(constants):
        raise ValueError('Compiled concrete donor constant count changed')
    payload = bytes(b.read(pointer,count*16)) + struct.pack('>4f',1,1,1,1)*len(added_constants)
    struct.pack_into('>III',post,28,count+len(added_constants),b.alloc(payload),0)
    count,pointer = struct.unpack_from('>II',post,16)
    if count != len(textures):
        raise ValueError('Compiled concrete donor texture count changed')
    payload = bytes(b.read(pointer,count*24)) + (b'bitm' + bytes(8) + struct.pack('>IhBBBbH',0xffffffff,0,0,0,0,-1,0))*len(added_textures)
    struct.pack_into('>III',post,16,count+len(added_textures),b.alloc(payload),0)
    struct.pack_into('>i',post,104,blend_mode)
    return post,(textures+added_textures,constants+added_constants),evidence
