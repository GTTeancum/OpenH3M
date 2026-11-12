"""Compare generated HLSL against original retail microcode through ReXGlue.

Both executors use explicit level-zero bilinear texture sampling. This checks
shader instructions/control flow, not live particle simulation or Xenos LOD.
"""
import json
import hashlib
import os
from pathlib import Path
import random
import struct
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/h4-forge-research/isolated'
SHADERS = WORK / 'marker-shaders'
BINARIES = ROOT / 'work/rexglue-sdk/out/win-amd64'
FIELDS = json.loads((WORK / 'marker-effect-fields.json').read_text())
environment = dict(os.environ, TEMP=str(ROOT / 'work/build-temp'), TMP=str(ROOT / 'work/build-temp'))


def run(tool, material, program, cases, output):
    command = [str(BINARIES / tool), str(material), str(program), str(cases),
               str(WORK / 'marker-bitmaps'), str(output)]
    result = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, timeout=60)
    (SHADERS / f'{material}-{tool}.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    print(result.stdout.strip())


report = []
for material, tag in ((331, '16658'), (16, '16660')):
    randomizer = random.Random(419 + material)
    post = FIELDS[tag]['fields']['Postprocess Definition@0x5C'][0]
    constants = np.zeros((256, 4), dtype='<f4')
    constants[0] = (1, 1, 1, 1)
    constants[2] = (1, 1, 1, 0)
    for index, values in enumerate(post['Float Constants@0x18']):
        constants[160+index] = list(values.values())
    for index, values in enumerate(post['Texture Constants@0xC']):
        constants[184+index] = list(values.values())
    original = np.frombuffer((SHADERS / f'{material}-ps-0.constants').read_bytes(), dtype='>f4')
    constants[250:252] = original[8:16].reshape(2, 4)
    constants[204] = (0, 0, 1, 0)
    constants[205] = (.8, .9, 1, 0)
    constants[206] = (.2, .3, .4, 0)
    data = []
    for index in range(1408):
        c = constants.copy()
        b = np.zeros(8, dtype='<u4')
        b[4] = post['Boolean Constants@0x3C']
        r = np.zeros((8, 4), dtype='<f4')
        u, v = (index % 32 + .5)/32, (index//32 % 32 + .5)/32
        r[0] = (u, v, u, v)
        r[1] = (0, 0, 1, 1)
        r[2] = (0, 0, .5, 0)
        r[3] = (0, 0, 0, 1) if material == 331 else (1, .4, .1, 1)
        r[4] = (1, 1, 1, 1) if material == 331 else (0, 0, 0, 0)
        c[1, 0] = .375
        c[3, 0] = post['Alpha Blend Mode@0x78']['value']
        if index >= 1024:
            # Exercise every shader's runtime branches, nontrivial tint,
            # intensity, texture offsets, and both sides of compare operations.
            b[4] = randomizer.randrange(16)
            b[7] = randomizer.randrange(16) << 4
            c[1, 0] = randomizer.uniform(0, 30)
            c[3, 0] = randomizer.choice((0, 1, 2, 5, 9, 18))
            c[208, 0] = randomizer.uniform(0, .2)
            r[:] = np.array([[randomizer.uniform(.1, 1) for _ in range(4)] for _ in range(8)])
            if index >= 1280:
                # Fully faded particles and coincident black/white alpha points
                # can create reciprocal infinities which Xenos zero-multiply
                # must suppress. These are relevant endpoints, not random NaNs.
                r[1, 3] = 0
                r[4, 3] = 0
                r[5, 3] = 0
        data.append(c.tobytes() + b.tobytes() + r.tobytes())
    cases = SHADERS / f'{material}-cases.bin'
    cases.write_bytes(struct.pack('<I', len(data)) + b''.join(data))
    reference = SHADERS / f'{material}-reference.rgba32f'
    actual = SHADERS / f'{material}-translated.rgba32f'
    run('h4_forge_marker_shader_check.exe', material, SHADERS / f'{material}-ps-0.ucode', cases, reference)
    run('h4_forge_marker_shader_gpu.exe', material, SHADERS / f'{material}-ps.generated.hlsl', cases, actual)
    expected = np.frombuffer(reference.read_bytes(), dtype='<f4').reshape(-1, 4)
    result = np.frombuffer(actual.read_bytes(), dtype='<f4').reshape(-1, 4)
    if expected.shape != (len(data), 4) or result.shape != expected.shape or not np.all(np.isfinite(result)):
        raise ValueError('Invalid shader output shape or values')
    error = np.abs(expected-result)
    tolerance = 2e-5 + np.abs(expected)*2e-5
    bad = np.where(np.any(error > tolerance, axis=1))[0]
    if len(bad):
        first = int(bad[0])
        raise ValueError(f'Material {material}: {len(bad)} mismatches; first case {first}: '
                         f'original={expected[first]}, HLSL={result[first]}, max error={error.max()}')
    if not np.any(expected[:1024, :3] > 0):
        raise ValueError('Representative material grid produced no color')
    report.append(dict(material=material, cases=len(data), max_absolute_error=float(error.max()),
                       microcode_sha256=hashlib.sha256((SHADERS / f'{material}-ps-0.ucode').read_bytes()).hexdigest(),
                       generated_hlsl_sha256=hashlib.sha256((SHADERS / f'{material}-ps.generated.hlsl').read_bytes()).hexdigest(),
                       cases_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
                       reference='Original retail microcode executed by ReXGlue ShaderInterpreter',
                       translated='Generated HLSL executed by D3D11 WARP',
                       limitations='Level-zero bilinear textures; synthetic depth; supplied interpolants, not live particles.'))
(SHADERS / 'execution-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
