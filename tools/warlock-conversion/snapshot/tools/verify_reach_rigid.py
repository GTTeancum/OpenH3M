"""Compare native packed positions/UVs against original Reach MCC vertices.

Regression check for equal-stride, different-layout Reach/H3 rigid records.
Does not substitute for inspection of the rendered result.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from build_dlc_live import confined
from reach_forge_palette import ReachCache
from reach_resource import ReachResource, convert_render_resource


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reach', type=Path, required=True)
    p.add_argument('--shared', type=Path, required=True)
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    output = confined(args.report)
    source = ReachCache(args.reach)
    pages, count, models, worst = {}, 0, 0, 0.
    try:
        for row in json.loads(args.bridge.read_text()):
            if row['group'] != 'mode':
                continue
            models += 1
            r = ReachResource(source, row['resource'], {'maps\\shared.map':args.shared}, pages)
            native = convert_render_resource(r)
            fix = dict(native['fixups'])
            table = fix[28] & 0x1fffffff
            for index, at in enumerate(r.buffers('vertex')):
                vertices, fmt, stride = r.unpack('IHH', at)
                if fmt != 2:
                    continue
                pointer = r.fix[at+20]
                raw = r.raw[{0x40000000:0, 0x60000000:1}[pointer & 0xe0000000]]
                start = pointer & 0x1fffffff
                # Reclaimer's MccHaloReachVertexBuffer schema: float4, UV at16.
                xyz = np.ndarray((vertices,3),dtype='<f4',buffer=raw,offset=start,strides=(36,4))
                uv = np.ndarray((vertices,2),dtype='<u2',buffer=raw,offset=start+16,strides=(36,2))
                descriptor = fix[table+index*12] & 0x1fffffff
                dest = fix[descriptor+20] & 0x1fffffff
                packed = np.ndarray((vertices,3),dtype='>u2',buffer=native['raw'],offset=dest,strides=(24,2))
                native_uv = np.ndarray((vertices,2),dtype='>u2',buffer=native['raw'],offset=dest+8,strides=(24,2))
                error = float(np.max(np.abs(xyz-packed.astype(float)/65535)))
                if error > .5001/65535 or not np.array_equal(uv,native_uv):
                    raise ValueError(f'Rigid position/UV conversion failed: {row["name"]}')
                worst = max(worst,error)
                count += vertices
    finally:
        source.close()
    report = dict(models=models,vertices=count,max_normalized_position_error=worst,
                  bound=.5001/65535,uv_bit_patterns='identical',visual_validation='separate')
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
