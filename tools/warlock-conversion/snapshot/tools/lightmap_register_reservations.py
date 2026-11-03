"""Protect H3 persistent lightmap scales from rounded material constant uploads.

Native constant uploads operate on four-register blocks. Assigning a material
parameter to c208/c209 can overwrite c210/c211 with padding, even when reflection
shows no direct overlap. Reserve both blocks containing c210 through c212.
"""
import re

LIGHTMAP_BLOCK = range(208, 216)
PADDING = (208, 209, 213, 214, 215)


def reserve_source(source):
    for index in range(3):
        pattern = rf'PIXEL_CONSTANT\(float4,\s*p_lightmap_compress_constant_{index},\s*c{210 + index}\);'
        if len(re.findall(pattern, source)) != 1:
            raise ValueError('Native lightmap declarations missing or changed')
    missing = []
    for register in PADDING:
        declaration = f'   PIXEL_CONSTANT(float4, p_lightmap_upload_padding_{register}, c{register});'
        if declaration not in source:
            missing.append(declaration)
    if not missing:
        return source
    anchor = re.search(r'(?m)^\s*PIXEL_CONSTANT\(float4,\s*p_lightmap_compress_constant_0,\s*c210\);', source)
    return source[:anchor.start()] + '\n// Reserve complete native lightmap upload blocks.\n' + '\n'.join(missing) + '\n' + source[anchor.start():]


def material_collisions(plan):
    """Inspect material float routes, excluding the engine's persistent routes."""
    collisions = []
    for program in plan['programs']:
        for register, parameter, flags in program['usages'][4]:
            if register in LIGHTMAP_BLOCK:
                collisions.append(dict(entry=program['entry'], name=program['name'],
                                       register=register, parameter=parameter, flags=flags))
    return collisions


def require_safe_material_routes(plan):
    collisions = material_collisions(plan)
    if collisions:
        raise ValueError('Material routes overlap persistent lightmap upload blocks: ' + str(collisions))


def shared_float_upload_collisions(plan):
    """Check material uploads against rounded blocks used by reflected globals.

    Union all programs because engine constants can persist across draw passes.
    This covers globals present in the plan, not unobserved engine registers.
    """
    blocks = {}
    for program in plan['programs']:
        fixed = set(program.get('persistent', []))
        external = {route[0] for route in program['usages'][10]}
        for value in program['registers']:
            if value['set'] != 2:
                continue
            start, count = value['register'], value['count']
            if value['name'].lower() not in fixed and not any(start <= r < start + count for r in external):
                continue
            for register in range(start // 4 * 4, (start + count + 3) // 4 * 4):
                blocks.setdefault(register, set()).add(value['name'].lower())
    return [dict(entry=program['entry'], name=program['name'], register=register,
                 parameter=parameter, shared=sorted(blocks[register]))
            for program in plan['programs']
            for register, parameter, flags in program['usages'][4]
            if register in blocks]


def require_safe_shared_float_uploads(plan):
    collisions = shared_float_upload_collisions(plan)
    if collisions:
        raise ValueError('Material uploads overlap shared float blocks: ' + str(collisions))
