"""Build private lightmap-safe variants of existing reviewed Powerhouse profiles.

First reproduce each baseline through its pinned recipe. Change only the lightmap
register reservations, remap named material routes, and recheck native interfaces.
These outputs require native visual validation before recipe promotion.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

import build_powerhouse_water_shaders as baseline
from lightmap_register_reservations import material_collisions, reserve_shared_source, require_safe_material_routes, shared_float_upload_collisions, require_safe_shared_float_uploads


def reflection(text):
    return [dict(name=name, set={'b': 0, 'i': 1, 'c': 2, 's': 3}[kind],
                 register=int(register), count=int(count))
            for name, kind, register, count in re.findall(
                r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$', text, re.M)]


def remap(program, registers):
    previous = {r['name'].lower(): r for r in program['registers']}
    current = {r['name'].lower(): r for r in registers}
    if previous.keys() != current.keys():
        raise ValueError('Shader parameter names changed')
    local = set()
    result = copy.deepcopy(program)
    for route in result['usages'][4]:
        register = route[0]
        matches = [r for r in previous.values() if r['set'] == 2 and
                   r['register'] <= register < r['register'] + r['count']]
        if len(matches) != 1:
            raise ValueError('Ambiguous material route')
        old = matches[0]
        name = old['name'].lower()
        route[0] = current[name]['register'] + register - old['register']
        local.add(name)
    for name, old in previous.items():
        new = current[name]
        if (old['set'], old['count']) != (new['set'], new['count']):
            raise ValueError('Shader parameter type or extent changed: ' + name)
        if name not in local and old['register'] != new['register']:
            raise ValueError('Non-material register changed: ' + name)
    result['registers'] = registers
    return result


def build(kind, destination, compiler, baseline_root=None):
    destination = baseline.confined(destination)
    original = destination / 'baseline'
    supplied = baseline.confined(baseline_root) / kind if baseline_root else None
    if supplied is not None and supplied.is_dir():
        manifest_name = 'compilation.json' if (supplied / 'compilation.json').is_file() else 'splash-entrypoint-compilation.json'
        manifest = json.loads((supplied / manifest_name).read_text())
        programs = manifest['programs'] if isinstance(manifest, dict) else manifest
        prefix = 'concrete-' if manifest_name == 'compilation.json' else 'splash-'
        if len(programs) != 13:
            raise ValueError('Supplied baseline must contain all thirteen compiled entries')
        for program in programs:
            raw = (supplied / (prefix + program['name'] + '.bin')).read_bytes()
            if not program['success'] or hashlib.sha256(raw).hexdigest() != program['sha256']:
                raise ValueError('Supplied baseline binary differs from its manifest')
        shutil.copytree(supplied, original, dirs_exist_ok=True)
    else:
        baseline.build('work/powerhouse/shader-toolchain/reference/halo_online_shaders', original, compiler, kind)
    extended = kind in ('concrete', 'grate', 'window', 'opaque-grate')
    plan_name = 'route-plan.json' if extended else 'splash-route-plan.json'
    prefix = 'concrete-' if extended else 'splash-'
    plan = json.loads((original / plan_name).read_text())
    original_collisions = shared_float_upload_collisions(plan)
    audit = json.loads((original / 'native-interface-audit.json').read_text())
    recipe = json.loads((baseline.REFERENCE / 'recipe.json').read_text())
    recipe.update(json.loads((baseline.REFERENCE.parent / f'powerhouse-{kind}-shaders/recipe.json').read_text()))
    adapted = destination / 'xenos-source'
    shutil.copytree(original / 'xenos-source', adapted, dirs_exist_ok=True)
    header = adapted / 'hlsl_constant_persist.fx'
    header.write_text(reserve_shared_source(header.read_text()))
    wrapper = destination / 'water-xenos.fx'
    shutil.copyfile(original / 'water-xenos.fx', wrapper)
    env = dict(os.environ, TEMP=str(baseline.confined('.local/build-temp')),
               TMP=str(baseline.confined('.local/build-temp')))
    compiled, assemblies = [], {}
    for program in recipe['programs']:
        index, name = program['entry'], program['name']
        entry = ('static_prt_ps' if name.startswith('static_prt_') else
                 'dynamic_light_cine_ps' if index == 17 else name + '_ps')
        binary, assembly = [destination / (prefix + name + ext) for ext in ('.bin', '.asm')]
        command = [str(compiler), '/T', 'ps_3_0', '/E', entry, '/Fo', str(binary),
                   '/Fc', str(assembly), *recipe['defines'], '/Dentry_point=' + name, str(wrapper)]
        result = subprocess.run(command, cwd=baseline.REPOSITORY, env=env,
                                capture_output=True, text=True, timeout=60)
        (destination / (prefix + name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('Compilation failed: ' + name)
        raw = binary.read_bytes()
        magic, debug_size, code_size = struct.unpack_from('>III', raw)
        if magic >> 16 != 0x102a or debug_size + code_size != len(raw):
            raise ValueError('Invalid compiled shader bounds')
        assemblies[index] = assembly.read_text()
        compiled.append(dict(entry=index, name=name, success=True, bytes=len(raw),
                             sha256=hashlib.sha256(raw).hexdigest()))
    plan['programs'] = [remap(p, reflection(assemblies[p['entry']])) for p in plan['programs']]
    require_safe_material_routes(plan)
    require_safe_shared_float_uploads(plan)
    for row in audit:
        text = assemblies[row['entry']]
        registers = {r['name'].lower(): r for r in reflection(text)}
        row['compiled_inputs'] = re.findall(r'^dcl[^\r\n]*', text, re.M)
        row['inputs_match'] = row['compiled_inputs'] == row['native_inputs']
        for check in row['fixed_register_checks']:
            actual = registers[check['name'].lower()]
            check['actual'] = [{0: 'b', 1: 'i', 2: 'c', 3: 's'}[actual['set']],
                               actual['register'], actual['count']]
            check['equal'] = check['actual'] == check['expected']
        if not row['inputs_match'] or any(not c['equal'] for c in row['fixed_register_checks']):
            raise ValueError('Native interface changed: ' + row['name'])
    (destination / plan_name).write_text(json.dumps(plan, indent=2) + '\n')
    (destination / 'native-interface-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    (destination / ('compilation.json' if extended else 'splash-entrypoint-compilation.json')).write_text(
        json.dumps(dict(programs=compiled) if extended else compiled, indent=2) + '\n')
    report = dict(kind=kind, compiled=len(compiled), interfaces=len(audit),
                  removed_collisions=original_collisions, remaining_collisions=shared_float_upload_collisions(plan),
                  baseline_origin=str(supplied) if supplied and supplied.is_dir() else "pinned recipe",
                  scope='Private compiler and interface validation; native visuals remain unverified.')
    (destination / 'register-correction.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kinds', nargs='+', choices=('concrete', 'grate', 'window', 'water', 'splash', 'opaque-grate'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline-root', help='Validated private profiles matching the candidate; absent kinds use pinned recipes.')
    parser.add_argument('--compiler', type=Path, default=Path(r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe'))
    args = parser.parse_args()
    for kind in args.kinds:
        report = build(kind, Path(args.output) / kind, args.compiler, args.baseline_root)
        print(json.dumps({k: v for k, v in report.items() if k != 'removed_collisions'}), flush=True)
