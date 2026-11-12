"""Compare each original fade ALU block with generated HLSL and endpoint expectations."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'work/h4-forge-research/isolated'
SHADERS = WORK/'marker-shaders'
BIN = ROOT/'work/rexglue-sdk/out/win-amd64'
fields = json.loads((WORK/'marker-effect-fields.json').read_text())
systems = fields['16657']['fields']['Events@0x34'][0]['Particle Systems@0x38']
env = dict(os.environ, TEMP=str(ROOT/'work/build-temp'), TMP=str(ROOT/'work/build-temp'))
reports = []
for material, system in zip((331, 16), systems):
    near_range = system['Near Fade Range@0x3C']
    near_cutoff = system['Near Fade Cutoff@0x40']
    far_range = system['Far Fade Range@0x48']
    far_cutoff = system['Far Fade Cutoff@0x4C']
    boundaries = (near_cutoff, near_cutoff+near_range, far_cutoff-far_range, far_cutoff)
    depths = list(np.linspace(-2, 26, 1025))
    depths += [v+d for v in boundaries for d in (-1e-5, 0, 1e-5)]
    data = []; expected = []
    for depth in depths:
        c = np.zeros((256,4), dtype='<f4');r = np.zeros((8,4),dtype='<f4');b=np.zeros(8,dtype='<u4')
        c[87,:2] = near_range,near_cutoff;c[88,:2] = far_range,far_cutoff
        r[0,2 if material==331 else 0] = depth
        r[3,0] = 1 # Original predicate setup against c247.w=0.
        data.append(c.tobytes()+b.tobytes()+r.tobytes())
        actual_depth=float(r[0,2 if material==331 else 0])
        expected.append((np.clip((actual_depth-near_cutoff)/near_range,0,1),
                         np.clip((far_cutoff-actual_depth)/far_range,0,1)))
    cases = SHADERS/f'{material}-fade-cases.bin'
    cases.write_bytes(struct.pack('<I',len(data))+b''.join(data))
    outputs=[]
    for tool,program,suffix in (
        ('h4_forge_marker_shader_check.exe',f'{material}-fade-block.ucode','reference'),
        ('h4_forge_marker_shader_gpu.exe',f'{material}-fade-block.generated.hlsl','translated')):
        output=SHADERS/f'{material}-fade-{suffix}.rgba32f';outputs.append(output)
        result=subprocess.run([str(BIN/tool),'fade',str(SHADERS/program),str(cases),
            str(WORK/'marker-bitmaps'),str(output)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
        (SHADERS/f'{material}-fade-{suffix}.log').write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        print(result.stdout.strip())
    reference, translated=[np.frombuffer(p.read_bytes(),dtype='<f4').reshape(-1,4) for p in outputs]
    assert reference.shape==translated.shape==(len(data),4)
    assert np.isfinite(reference).all() and np.isfinite(translated).all()
    error=float(np.max(np.abs(reference-translated)))
    assert np.allclose(reference,translated,atol=2e-6,rtol=2e-6),error
    assert np.allclose(reference[:,:2],expected,atol=2e-6,rtol=2e-6),reference[:5]
    extraction=json.loads((SHADERS/f'{material}-fade-block-extraction.json').read_text())
    reports.append(dict(material=material,cases=len(data),max_absolute_error=error,
        extraction=extraction, cases_sha256=hashlib.sha256(cases.read_bytes()).hexdigest(),
        near_range=near_range,near_cutoff=near_cutoff,far_range=far_range,far_cutoff=far_cutoff,
        limitation='Fade ALU fragment with supplied camera-axis depth; not full original vertex/particle execution.'))
(SHADERS/'fade-validation.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
