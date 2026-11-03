"""Verify every official recompiled sky vertex against original Reach RGB."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/battle-canyon/rebuild'
REL = Path('levels/dlc/cex_beaver_creek/beavercreek_sky/beavercreek_sky.render_model')
NEW = Path('levels/mod_levels/bc_sky_rgb_repair/beavercreek_sky/beavercreek_sky.render_model')


def main():
    env = dict(os.environ, TEMP=str(WORK / 'temp'), TMP=str(WORK / 'temp'))
    def inspect(kit, game, rel, field):
        return json.loads(subprocess.check_output([
            str(WORK / 'blam-target/release/blam-tag-shell.exe'), '-g', game, 'inspect',
            str(ROOT / 'work/editing-kits' / kit / 'tags' / rel), field, '--full', '--json'],
            cwd=WORK / 'blam-tags', env=env))

    def vertices(kit, game, rel):
        rows = inspect(kit, game, rel, 'render geometry/per mesh temporary[0]/raw vertices')
        return [{f['name']: f.get('value', f.get('elements')) for f in row} for row in rows]

    source = vertices('hrek', 'haloreach_mcc', REL)
    old = vertices('h3ek', 'halo3_mcc', REL)
    new = vertices('h3ek', 'halo3_mcc', NEW)
    assert len(source) == len(old) == len(new)
    def geometry(v):
        return [v[k][a] for k, axes in [('position', 'xyz'), ('normal', 'xyz'),
                                       ('texcoord', 'xy')] for a in axes]
    src_geom = np.array([geometry(v) for v in source])
    src_rgb = np.array([[v['vertex color'][a] for a in 'xyz'] for v in source])
    buckets = {}
    for i, row in enumerate(src_geom):
        buckets.setdefault(tuple(np.round(row, 5)), []).append(i)
    errors = {'source_geometry': 0.0, 'source_color': 0.0}
    matched_source = set()
    for before, after in zip(old, new):
        # The compiler reorders Reach vertices, but its old/new geometry must agree.
        assert geometry(before) == geometry(after)
        row = np.array(geometry(after))
        candidates = buckets.get(tuple(np.round(row, 5)))
        if not candidates:
            candidates = np.flatnonzero(np.max(np.abs(src_geom-row), axis=1) < 2e-6).tolist()
        assert candidates, 'Compiled vertex has no original-source geometry match'
        rgb = np.array([after['vertex color'][a] for a in 'xyz'])
        matching = [i for i in candidates if np.max(np.abs(src_geom[i]-row)) < 2e-6
                    and np.max(np.abs(src_rgb[i]-rgb)) < 1e-6]
        assert matching, (candidates, rgb, src_rgb[candidates])
        i = matching[0]
        matched_source.update(matching)
        errors['source_geometry'] = max(errors['source_geometry'], float(np.max(np.abs(src_geom[i]-row))))
        errors['source_color'] = max(errors['source_color'], float(np.max(np.abs(src_rgb[i]-rgb))))
    assert len(matched_source) == len(source), 'Some original vertices were not verified'
    preserved = {}
    for field in ('sky lights', 'materials', 'nodes', 'render geometry/compression info',
                  'render geometry/meshes', 'render geometry/per mesh temporary[0]/raw indices'):
        a = inspect('h3ek', 'halo3_mcc', REL, field)
        b = inspect('h3ek', 'halo3_mcc', NEW, field)
        assert a == b, field
        preserved[field] = len(a)
    path = ROOT / 'work/editing-kits/h3ek/tags' / NEW
    report = dict(compiled_render_model=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  vertices=len(new), source_vertices_matched=len(matched_source),
                  nonzero_source_vertices=int(np.count_nonzero(np.any(src_rgb, axis=1))),
                  old_nonzero_vertices=sum(any(v['vertex color'].values()) for v in old),
                  restored_nonzero_vertices=sum(any(v['vertex color'].values()) for v in new),
                  max_error=errors, preserved_fields=preserved,
                  scope='All original RGB verified by geometry correspondence; no game run or new bake.')
    (WORK / 'sky-color-repair/compiled-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
