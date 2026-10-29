"""Read back primary geometry positions/UVs independently of the encoder."""
import json
import sys
from pathlib import Path
import numpy as np
from cache_reader import Cache
from resource_reader import Resource

ROOT = Path(__file__).resolve().parents[4]


def audit(candidate):
    source = Cache(r'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map', True)
    target = Cache(candidate)
    report = {'buffers': [], 'errors': []}
    try:
        sr = [t['offset'] for t in source.tags.values() if t['group'] == 'Lbsp']
        dr = [b for t in target.tags.values() if t['group'] == 'sLdT'
              for b in target.block(t['offset'] + 4, 436)]
        if len(sr) != len(dr):
            raise ValueError('Lighting BSP count mismatch')
        for bi, (sroot, droot) in enumerate(zip(sr, dr)):
            a = Resource(source, source.u(sroot + 0x1ac))
            b = Resource(target, target.u(droot + 0x1ac),
                         {'maps\\shared.map': ROOT / '../../maps/shared.map'})
            av, bv = a.buffers('vertex'), b.buffers('vertex')
            if len(av) != len(bv):
                raise ValueError('Vertex buffer count mismatch')
            for vi, (x, y) in enumerate(zip(av, bv)):
                n, fmt, stride = a.unpack('IHH', x)
                nn, ff, ds = b.unpack('IHH', y)
                if fmt not in (1, 2, 3):
                    continue
                if (n, fmt) != (nn, ff):
                    raise ValueError('Primary vertex descriptor mismatch')
                unit, columns = (4, 5) if fmt == 1 else (2, 6)
                sv = np.ndarray((n, columns), dtype=f'<u{unit}', buffer=a.raw[0],
                                offset=a.ptr(x + 20), strides=(stride, unit))
                dv = np.ndarray((n, columns), dtype=f'>u{unit}', buffer=b.raw[0],
                                offset=b.ptr(y + 20), strides=(ds, unit))
                bad = int(np.count_nonzero(np.any(sv != dv, axis=1)))
                row = {'bsp': bi, 'buffer': vi, 'format': fmt,
                       'vertices': n, 'position_uv_mismatches': bad}
                report['buffers'].append(row)
                if bad:
                    report['errors'].append(row)
        return report
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    result = audit(Path(sys.argv[1]))
    (ROOT / 'work/forge-world/position-payload-audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'buffers': len(result['buffers']),
                      'vertices': sum(r['vertices'] for r in result['buffers']),
                      'errors': result['errors']}))
    sys.exit(bool(result['errors']))
