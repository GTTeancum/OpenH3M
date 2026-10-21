"""Build native soft-ceiling geometry using the offline TagTool MOPP compiler."""
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import numpy as np
from forge_gulch_boundary import BOUNDARY

COMPILER_SHA256 = '27e45ec9dc5e06e0f51afb78991d8f8f1ba6cdb057f04e6ef2f0feaa4fcf618e'


def split_vertical_extent(original):
    """Overlap the closed outer shell so the divider cannot be flown under/over."""
    vertices = np.asarray(original)[:, 8:].reshape(-1, 3)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    if BOUNDARY[0][0] >= low[0]-4 or BOUNDARY[-1][0] <= high[0]+4:
        raise ValueError('Split endpoints must extend beyond the outer containment shell')
    # Four units exceed the measured <1-unit monitor penetration at the split.
    return min(-40., float(low[2])-4.), max(160., float(high[2])+4.)


def triangles(source, root):
    ceilings = source.block(root + 16, 20)
    if len(ceilings) != 1 or source.unpack('hh', ceilings[0] + 4) != (0, 0):
        raise ValueError('Expected one acceleration soft ceiling')
    original = [source.unpack('17f', row) for row in source.block(ceilings[0] + 8, 68)]
    bottom, top = split_vertical_extent(original)
    result = list(original)
    for start, end in zip(BOUNDARY, BOUNDARY[1:]):
        a = np.array([*start, bottom])
        b = np.array([*end, bottom])
        c, d = b + [0., 0., top-bottom], a + [0., 0., top-bottom]
        # Normal points into Gulch (negative Y), matching the source ceiling's
        # inward-facing convention. Keep both triangles in the existing group.
        for vertices in ((a, c, d), (a, b, c)):
            p, q, r = vertices
            normal = np.cross(q-p, r-p)
            normal /= np.linalg.norm(normal)
            center = (p+q+r)/3
            radius = max(np.linalg.norm(v-center) for v in vertices)
            if normal[1] >= 0:
                raise ValueError('Boundary triangle faces out of Gulch')
            result.append(tuple(normal) + (float(normal @ p),) + tuple(center)
                          + (float(radius),) + tuple(p) + tuple(q) + tuple(r))
    return result, len(original)


def compile_mopp(rows):
    repo = Path(__file__).resolve().parents[4]
    work = repo / 'work/forge-world'
    compiler = work / 'tools/mopp.exe'
    if not compiler.exists():
        import urllib.request
        data = urllib.request.urlopen(
            'https://raw.githubusercontent.com/TheGuardians/TagTool/master/Tools/mopp.exe',
            timeout=30).read()
        if hashlib.sha256(data).hexdigest() != COMPILER_SHA256:
            raise ValueError('Downloaded MOPP compiler differs from the pinned version')
        compiler.parent.mkdir(parents=True, exist_ok=True)
        compiler.write_bytes(data)
    if hashlib.sha256(compiler.read_bytes()).hexdigest() != COMPILER_SHA256:
        raise ValueError('Unverified offline MOPP compiler')
    temporary = work / 'temp'
    temporary.mkdir(parents=True, exist_ok=True)
    input_path, output_path = temporary / 'boundary.input', temporary / 'boundary.output'
    lines = [';### vertices ###', str(len(rows)*3)]
    for row in rows:
        for at in (8, 11, 14):
            lines.append('	'.join(format(v, '.10f') for v in row[at:at+3]))
    lines.extend(['', ';### surfaces ###', str(len(rows))])
    for index in range(len(rows)):
        lines.extend(['3', f'{index*3}\t{index*3+1}\t{index*3+2}'])
    input_path.write_text('\n'.join(lines)+'\n')
    env = dict(os.environ, TEMP=str(temporary), TMP=str(temporary),
               LOCALAPPDATA=str(temporary), APPDATA=str(temporary))
    try:
        run = subprocess.run([str(compiler), 'generate-collision-mopp', str(input_path), str(output_path)],
                             cwd=repo, env=env, capture_output=True, timeout=60,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        if run.returncode:
            raise ValueError(f'MOPP compiler failed ({run.returncode:#x}): '
                             + (run.stdout + run.stderr).decode(errors='replace'))
        return output_path.read_bytes()
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def apply(importer, source_root, payload):
    """Replace only the design's soft-ceiling table/tree; keep water intact."""
    rows, original_count = triangles(importer.source, source_root)
    compiled = compile_mopp(rows)
    if len(compiled) < 48 or any(struct.unpack_from('<I', compiled, o)[0] for o in (0, 8, 12, 32)):
        raise ValueError('Unexpected compiler header/runtime pointers')
    size, capacity = struct.unpack_from('<II', compiled, 36)
    if size > capacity or 48 + size > len(compiled) or len(compiled) - 48 - size > 15:
        raise ValueError('Invalid compiled MOPP allocation')
    from collision_physics import retail_mopp
    code = compiled[48:48+size]
    if retail_mopp(code) != code:
        raise ValueError('Boundary compiler emitted nonretail shape keys')
    b = importer.builder
    out = bytearray(payload)
    count, pointer = struct.unpack_from('>II', out, 16)
    if count != 1:
        raise ValueError('Converted design must contain one soft ceiling')
    ceiling = bytearray(b.read(pointer, 20))
    packed = b''.join(struct.pack('>17f', *row) for row in rows)
    struct.pack_into('>III', ceiling, 8, len(rows), b.alloc(packed), 0)
    struct.pack_into('>III', out, 16, 1, b.alloc(ceiling), 0)
    header = bytearray(64)
    struct.pack_into('>HH', header, 4, *struct.unpack_from('<HH', compiled, 4))
    struct.pack_into('>4f', header, 16, *struct.unpack_from('<4f', compiled, 16))
    struct.pack_into('>II', header, 36, size, size | 0x80000000)
    struct.pack_into('>III', header, 48, size, b.alloc(code), 0)
    struct.pack_into('>III', out, 4, 1, b.alloc(header), 0)
    importer.gulch_containment_report = {
        'original_triangles_preserved': original_count,
        'boundary_triangles_added': len(rows)-original_count,
        'compiled_code_bytes': size,
        'compiler_sha256': COMPILER_SHA256,
        'native_behavior_verified': False,
    }
    return bytes(out)
