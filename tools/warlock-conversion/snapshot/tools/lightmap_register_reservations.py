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
