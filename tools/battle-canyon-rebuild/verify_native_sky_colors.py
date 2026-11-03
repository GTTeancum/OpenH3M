"""Verify restored sky RGB in the actual native GPU resource, not tag metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/battle-canyon/rebuild'
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource


def read_colors(path, mcc):
    c = Cache(path, mcc)
    try:
        scenario = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
        skies = c.block(scenario+(0x34 if mcc else 0x30), 20)
        assert len(skies) == 1
        def follow(at, field, group):
            d = c.u(at+field+12)
            t = c.tags[d & 65535]
            assert t['group'] == group and t['salt'] == d >> 16
            return t['offset']
        sky = follow(skies[0], 0, 'scen')
        model = follow(sky, 0x34, 'hlmt')
        render = follow(model, 0, 'mode')
        resource = Resource(c, c.u(render+0xe0))
        rows = [b for b in resource.buffers('vertex') if resource.unpack('H', b+4)[0] == 14]
        assert len(rows) == 1
        b = rows[0]
        count, fmt, stride, size = resource.unpack('IHHI', b)
        assert (count, fmt, stride, size) == (6577, 14, 12, 6577*12)
        address = resource.fix[b+20]
        segment = {0x40000000:0, 0x60000000:1}[address & 0xe0000000]
        start = address & 0x1fffffff
        raw = resource.raw[segment][start:start+size]
        assert len(raw) == size
        rgb = np.frombuffer(raw, dtype='<f4' if mcc else '>f4').reshape(count, 3).copy()
        assert np.isfinite(rgb).all()
        return rgb
    finally:
        c.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiled', type=Path, required=True)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    assert all(path.resolve().is_relative_to(WORK) for path in (a.compiled, a.native, a.report))
    source, native = read_colors(a.compiled, True), read_colors(a.native, False)
    assert np.array_equal(source, native), 'Native GPU RGB differs from official compiler output'
    assert np.count_nonzero(np.any(source, axis=1)) == 3683
    report = dict(compiled=str(a.compiled), native=str(a.native), vertices=len(source),
                  nonzero_vertices=int(np.count_nonzero(np.any(native, axis=1))),
                  exact_native_float_values=True,
                  rgb_float32_le_sha256=hashlib.sha256(native.astype('<f4').tobytes()).hexdigest(),
                  scope='All actual GPU RGB values preserved; visual appearance still requires user testing.')
    a.report.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
