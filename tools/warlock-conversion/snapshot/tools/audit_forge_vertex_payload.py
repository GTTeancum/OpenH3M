"""Compare serialized BSP positions, UVs and shading bases with MCC source.

Reads both native resource payloads independently; never calls the converter.
Water-only formats are outside this primary-vertex audit.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from cache_reader import Cache
from resource_reader import Resource


def audit(source_path, candidate_path):
    source, target = Cache(source_path, True), Cache(candidate_path)
    try:
        sr = sorted((t['offset'] for t in source.tags.values() if t['group'] == 'Lbsp'),
                    key=lambda r: source.unpack('h', r+2)[0])
        dr = [r for t in target.tags.values() if t['group'] == 'sLdT'
              for r in target.block(t['offset']+4, 436)]
        if len(sr) != len(dr) or not sr:
            raise ValueError('Source/target BSP lighting bindings differ')
        results = []
        for bsp, (sroot, droot) in enumerate(zip(sr, dr)):
            a, b = Resource(source, source.u(sroot+0x1ac)), Resource(target, target.u(droot+0x1ac))
            av, bv = a.buffers('vertex'), b.buffers('vertex')
            if len(av) != len(bv):
                raise ValueError('Vertex buffer counts differ')
            checked, total, max_error = 0, 0, 0.
            excluded = {}
            for number, (x, y) in enumerate(zip(av, bv)):
                n, fmt, ss = a.unpack('IHH', x)
                nn, ff, ds = b.unpack('IHH', y)
                if fmt not in (1, 2, 3):
                    excluded[str(fmt)] = excluded.get(str(fmt), 0)+1
                    continue
                expected = {1: (44, 32, 20, 4), 2: (36, 24, 12, 2), 3: (44, 32, 12, 2)}[fmt]
                if n != nn or fmt != ff or (ss, ds) != expected[:2]:
                    raise ValueError(f'BSP {bsp} buffer {number}: primary layout differs')
                prefix, unit = expected[2:]
                sp, dp = a.ptr(x+20), b.ptr(y+20)
                # Numeric equality of every endian-decoded component preserves
                # the exact position/UV bit patterns, including half floats.
                sv = np.ndarray((n, prefix//unit), dtype=f'<u{unit}', buffer=a.raw[0], offset=sp, strides=(ss, unit))
                dv = np.ndarray((n, prefix//unit), dtype=f'>u{unit}', buffer=b.raw[0], offset=dp, strides=(ds, unit))
                if not np.array_equal(sv, dv):
                    raise ValueError(f'BSP {bsp} buffer {number}: position/UV mismatch')
                for channel in range(3):
                    v = np.ndarray((n, 3), dtype='<i2', buffer=a.raw[0], offset=sp+prefix+channel*8, strides=(ss, 2))
                    v = np.maximum(v.astype(float)/32767, -1)
                    p = np.ndarray((n,), dtype='>u4', buffer=b.raw[0], offset=dp+prefix+channel*4, strides=(ds,))
                    for axis, (shift, bits) in enumerate(((0, 10), (10, 11), (21, 11))):
                        q = ((p >> shift) & ((1 << bits)-1)).astype(np.int32)
                        q[q >= 1 << (bits-1)] -= 1 << bits
                        limit = (1 << (bits-1))-1
                        error = float(np.max(abs(q/limit-v[:, axis]))) if n else 0.
                        if error > .50001/limit:
                            raise ValueError(f'BSP {bsp} buffer {number}: basis error exceeds quantization')
                        max_error = max(max_error, error)
                checked += 1
                total += n
            results.append({'bsp': bsp, 'primary_buffers': checked, 'vertices': total,
                            'position_uv_bits_exact': True, 'maximum_basis_component_error': max_error,
                            'excluded_buffer_formats': excluded})
        return {'source_sha256': hashlib.sha256(source.data).hexdigest(),
                'candidate_sha256': hashlib.sha256(target.data).hexdigest(), 'bsps': results,
                'scope': 'Primary vertex payloads only; no shader output or seam-free source claim'}
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--candidate', required=True)
    p.add_argument('--report', required=True, type=Path)
    args = p.parse_args()
    result = audit(args.source, args.candidate)
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['bsps']))
