"""Reproduce the native-tested Powerhouse river and splash programs with the installed XDK.

Inputs are the pinned HaloShaderGenerator source cache, not game shader binaries.
Generated files and compiler temporary data remain inside this repository.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import lightmap_register_reservations

REPOSITORY = Path(__file__).resolve().parents[4]
REFERENCE = Path(__file__).resolve().parents[1] / 'reference/powerhouse-water-shaders'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def confined(value):
    path = (REPOSITORY / value).resolve()
    if not path.is_relative_to(REPOSITORY):
        raise ValueError('Shader inputs and outputs must remain inside the repository')
    return path


def build(source, output, compiler, kind="water"):
    reference = REFERENCE.parent / f"powerhouse-{kind}-shaders"
    extended = kind in ('concrete', 'grate', 'window', 'opaque-grate', 'corrugated')
    route_name = 'route-plan.json' if extended else 'splash-route-plan.json'
    program_prefix = 'concrete-' if extended else 'splash-'
    source, output = confined(source), confined(output)
    recipe = json.loads((REFERENCE / 'recipe.json').read_text())
    if kind != 'water':
        recipe.update(json.loads((reference / 'recipe.json').read_text()))
    reviewed = recipe.get('reviewed_candidate', 59)
    for name, expected in recipe['source_hashes'].items():
        path = confined(source / name)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError('Pinned shader source missing or changed: ' + str(path))
    inputs = [REFERENCE / 'recipe.json', REFERENCE / 'xenos-compatibility.patch',
              reference / 'recipe.json', reference / route_name,
              reference / 'native-interface-audit.json', Path(__file__),
              Path(lightmap_register_reservations.__file__)]
    if recipe.get('profile_compatibility_patch'):
        inputs.append(reference / 'profile-compatibility.patch')
    fingerprint = digest(b''.join(path.read_bytes() for path in inputs))
    marker = output / 'build-manifest.json'
    if marker.is_file():
        cached = json.loads(marker.read_text())
        if cached.get('recipe_sha256') == fingerprint and all(
                confined(output / name).is_file() and
                digest(confined(output / name).read_bytes()) == expected
                for name, expected in cached.get('outputs', {}).items()) and cached.get('outputs'):
            print(f'Verified cached Powerhouse {kind} shaders: ' + str(output))
            return
    if not compiler.is_file():
        raise ValueError('Installed Xbox 360 fxc is required: ' + str(compiler))
    output.mkdir(parents=True, exist_ok=True)
    adapted = output / 'xenos-source'
    for name in recipe['source_hashes']:
        target = confined(adapted / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    patch = REFERENCE / 'xenos-compatibility.patch'
    for name in re.findall(r'^\+\+\+ xenos-source/(\S+)$', patch.read_text(), re.M):
        target = confined(adapted / name)
        target.write_text(target.read_text(), newline='\n')
    temporary = confined('.local/build-temp')
    temporary.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TEMP=str(temporary), TMP=str(temporary))
    subprocess.run(['git', 'apply', '--whitespace=nowarn',
                    '--directory=' + adapted.relative_to(REPOSITORY).as_posix(),
                    str(patch)],
                   cwd=REPOSITORY, env=env, check=True, timeout=30)
    if recipe.get('reserve_shared_upload_blocks') and not recipe.get('shared_padding_from_profile'):
        header = adapted / 'hlsl_constant_persist.fx'
        header.write_text(lightmap_register_reservations.reserve_shared_source(header.read_text()))
    elif recipe.get('reserve_lightmap_upload_blocks'):
        header = adapted / 'hlsl_constant_persist.fx'
        header.write_text(lightmap_register_reservations.reserve_source(header.read_text()))
    if recipe.get('profile_compatibility_patch'):
        for name in re.findall(r'^\+\+\+ xenos-source/(\S+)$', (reference / 'profile-compatibility.patch').read_text(), re.M):
            target = confined(adapted / name)
            target.write_text(target.read_text(), newline='\n')
        subprocess.run(['git', 'apply', '--whitespace=nowarn',
                        '--directory=' + adapted.relative_to(REPOSITORY).as_posix(),
                        str(reference / 'profile-compatibility.patch')],
                       cwd=REPOSITORY, env=env, check=True, timeout=30)
    wrapper = output / 'water-xenos.fx'
    wrapper.write_text(('#define H3_MATERIAL_TEXTURE_FLOAT 1\n' if kind in ('water', 'grate', 'window', 'opaque-grate', 'corrugated') else '') +
                       'float4 v_squish_params;\nbool v_mesh_squished;\n'
                       '#define BUMP_GET_CHANNELS(BM) ((BM).rg)\n'
                       '#include "xenos-source/shader.fx"\n')
    plan = json.loads((reference / route_name).read_text())
    if recipe.get('reserve_lightmap_upload_blocks'):
        lightmap_register_reservations.require_safe_material_routes(plan)
    if recipe.get('reserve_shared_upload_blocks'):
        lightmap_register_reservations.require_safe_shared_float_uploads(plan)
    expected_registers = {p['entry']: p['registers'] for p in plan['programs']}
    results = []
    for program in recipe['programs']:
        index, name = program['entry'], program['name']
        entry = ('static_prt_ps' if name.startswith('static_prt_') else
                 'dynamic_light_cine_ps' if index == 17 else name + '_ps')
        binary, assembly = (output / (program_prefix + name + ext) for ext in ('.bin', '.asm'))
        command = [str(compiler), '/T', 'ps_3_0', '/E', entry,
                   '/Fo', str(binary), '/Fc', str(assembly),
                   *recipe['defines'], '/Dentry_point=' + name, str(wrapper)]
        result = subprocess.run(command, cwd=REPOSITORY, env=env,
                                capture_output=True, text=True, timeout=60)
        (output / (program_prefix + name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('XDK compilation failed: ' + name)
        raw = binary.read_bytes()
        magic, debug_size, code_size = struct.unpack_from('>III', raw)
        if (magic >> 16 != 0x102a or debug_size + code_size != len(raw) or
                digest(raw[debug_size:]) != program['microcode_sha256']):
            raise ValueError(f'Generated microcode differs from native-tested candidate{reviewed}: ' + name)
        registers = [dict(name=n, set={'b': 0, 'i': 1, 'c': 2, 's': 3}[kind],
                          register=int(reg), count=int(count)) for n, kind, reg, count in
                     re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',
                                assembly.read_text(), re.M)]
        if index in expected_registers and registers != expected_registers[index]:
            raise ValueError('Generated reflection differs from reviewed routes: ' + name)
        results.append(dict(entry=index, name=name, success=True,
                            bytes=len(raw), sha256=digest(raw)))
    for name in (route_name, 'native-interface-audit.json'):
        shutil.copyfile(reference / name, output / name)
    if extended:
        (output / 'compilation.json').write_text(json.dumps({'programs': results}, indent=2))
    else:
        (output / 'splash-entrypoint-compilation.json').write_text(json.dumps(results, indent=2))
    artifacts = [p for p in output.iterdir() if p.is_file() and
                 p.suffix in ('.bin', '.asm', '.json') and p != marker]
    marker.write_text(json.dumps(dict(recipe_sha256=fingerprint,
        reviewed_candidate=reviewed, shader_kind=kind, compiler=recipe['compiler'],
        outputs={p.name: digest(p.read_bytes()) for p in artifacts}), indent=2))
    print(f'Built 13 Powerhouse {kind} programs matching the reviewed recipe: ' + str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='work/powerhouse/shader-toolchain/reference/halo_online_shaders')
    parser.add_argument('--kind', choices=('water', 'splash', 'concrete', 'grate', 'window', 'opaque-grate', 'corrugated'), default='water')
    parser.add_argument('--output')
    parser.add_argument('--compiler', type=Path,
                        default=Path(os.environ.get('XEDK', r'C:\Program Files (x86)\Microsoft Xbox 360 SDK')) / 'bin/win32/fxc.exe')
    args = parser.parse_args()
    build(args.source, args.output or f'work/powerhouse/native-{args.kind}-shaders', args.compiler, args.kind)
