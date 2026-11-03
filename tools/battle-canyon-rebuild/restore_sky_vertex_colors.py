"""Restore Reach sky vertex RGB lost by the existing JMS export.

Stage a separate JMS; never edit the original Reach tags or compile/bake here.
Match every emitted triangle corner against source position, normal and UV,
then replace only its RGB line. Geometry, material bindings and lights stay exact.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/battle-canyon/rebuild'
REL = Path('levels/dlc/cex_beaver_creek/beavercreek_sky')


def values(fields):
    return {f['name']: f.get('value', f.get('elements')) for f in fields}


def main():
    source = ROOT / 'work/editing-kits/hrek/tags' / REL / 'beavercreek_sky.render_model'
    original = ROOT / 'work/editing-kits/h3ek/data' / REL / 'render/beavercreek_sky.JMS'
    stage = WORK / 'sky-color-repair'
    stage.mkdir(exist_ok=True)
    env = dict(os.environ, TEMP=str(WORK / 'temp'), TMP=str(WORK / 'temp'))

    def inspect(field):
        command = [str(WORK / 'blam-target/release/blam-tag-shell.exe'),
                   '-g', 'haloreach_mcc', 'inspect', str(source), field, '--full', '--json']
        return json.loads(subprocess.check_output(command, cwd=WORK / 'blam-tags', env=env))

    meshes = inspect('render geometry/meshes')
    assert len(meshes) == 1, 'Review multi-mesh sky before restoring colors'
    mesh = values(meshes[0])
    assert mesh['index buffer type']['name'] == 'triangle strip'
    assert mesh['mesh flags']['value'] & 1, 'Source must explicitly carry vertex color'
    raw = [values(v) for v in inspect('render geometry/per mesh temporary[0]/raw vertices')]
    indices = [row[0]['value'] & 65535
               for row in inspect('render geometry/per mesh temporary[0]/raw indices')]
    assert 65535 not in indices, 'Review restart sentinel semantics before proceeding'
    bounds = values(inspect('render geometry/compression info')[0])
    assert bounds['compression flags']['value'] == 3
    pos_bounds = [bounds[f'position bounds {n}'][axis] for n in (0, 1) for axis in 'xyz']
    uv_bounds = [bounds[f'texcoord bounds {n}'][axis] for n in (0, 1) for axis in 'xy']

    def array(name, axes):
        return np.array([[v[name][a] for a in axes] for v in raw], dtype=np.float32)

    positions = array('position', 'xyz')
    uvs = array('texcoord', 'xy')
    for i in range(3):
        low, high = np.float32(pos_bounds[i*2:i*2+2])
        positions[:, i] = (low + positions[:, i] * (high-low)) * np.float32(100)
    for i in range(2):
        low, high = np.float32(uv_bounds[i*2:i*2+2])
        uvs[:, i] = low + uvs[:, i] * (high-low)
    uvs[:, 1] = np.float32(1) - uvs[:, 1]
    normals = array('normal', 'xyz')
    colors = array('vertex color', 'xyz')
    assert np.isfinite(colors).all() and np.any(colors != 0)

    corners, materials = [], []
    for part in mesh['parts']:
        p = values(part)
        strip = indices[p['index start']:p['index start']+p['index count']]
        for i in range(len(strip)-2):
            a, b, c = strip[i:i+3]
            if len({a, b, c}) < 3:
                continue
            corners.extend((a, b, c) if i % 2 == 0 else (a, c, b))
            materials.append(p['render method index'])

    # Preserve original line endings and every byte except the color records.
    before = original.read_bytes()
    lines = before.decode('ascii').splitlines(keepends=True)
    vertex_lines = [i for i, line in enumerate(lines) if re.fullmatch(r';VERTEX \d+\s*', line)]
    triangle_lines = [i for i, line in enumerate(lines) if re.fullmatch(r';TRIANGLE \d+\s*', line)]
    assert len(vertex_lines) == len(corners) and len(triangle_lines) == len(materials)
    max_error = {'position': 0.0, 'normal': 0.0, 'uv': 0.0}
    changed, old_nonzero = 0, 0
    color_lines = set()
    for ordinal, (at, vi) in enumerate(zip(vertex_lines, corners)):
        assert lines[at].strip() == f';VERTEX {ordinal}'
        assert int(lines[at+3]) == 1 and int(lines[at+4]) == 0
        assert float(lines[at+5]) == 1 and int(lines[at+6]) == 1
        for key, offset, expected in [('position', 1, positions[vi]),
                                      ('normal', 2, normals[vi]), ('uv', 7, uvs[vi])]:
            actual = np.array(list(map(float, lines[at+offset].split())))
            error = float(np.max(np.abs(actual - expected)))
            max_error[key] = max(max_error[key], error)
            assert error < 1e-6, (ordinal, key, actual, expected)
        old = np.array(list(map(float, lines[at+8].split())))
        old_nonzero += bool(np.any(old))
        assert np.all(old == 0) or np.allclose(old, colors[vi], rtol=0, atol=1e-9)
        changed += bool(np.any(np.abs(old-colors[vi]) > 1e-9))
        newline = '\r\n' if lines[at+8].endswith('\r\n') else '\n'
        lines[at+8] = '\t'.join(f'{x:.10f}' for x in colors[vi]) + newline
        color_lines.add(at+8)
    for ordinal, (at, material) in enumerate(zip(triangle_lines, materials)):
        assert int(lines[at+1]) == material
        assert list(map(int, lines[at+2].split())) == list(range(3*ordinal, 3*ordinal+3))
    after = ''.join(lines).encode('ascii')
    original_lines = before.decode('ascii').splitlines(keepends=True)
    assert all(original_lines[i] == line for i, line in enumerate(lines) if i not in color_lines)
    output = stage / 'beavercreek_sky.JMS'
    output.write_bytes(after)
    report = dict(source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  original_jms_sha256=hashlib.sha256(before).hexdigest(),
                  restored_jms_sha256=hashlib.sha256(after).hexdigest(), output=str(output),
                  source_vertices=len(raw), exported_corners=len(corners), triangles=len(materials),
                  old_nonzero_corners=int(old_nonzero), changed_color_corners=int(changed),
                  source_nonzero_vertices=int(np.count_nonzero(np.any(colors != 0, axis=1))),
                  max_corner_match_error=max_error, only_rgb_lines_changed=True,
                  scope='Original source RGB restored in staged JMS; compilation and visual review separate.')
    (stage / 'restoration.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
