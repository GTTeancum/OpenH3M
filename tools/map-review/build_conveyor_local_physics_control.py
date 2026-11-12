"""Private one-bit diagnostic; never deploys a map."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt

work = ROOT / 'work/map-review-20261105'
b = MapBuilder(ROOT / 'work/elongation/zanzibar-06.map', 0)
assert hashlib.sha256(b.original).hexdigest() == 'd16fc47ddff19aedded262731bd7fdf4dcbcd4ba6b2c9d300928643c42ff989f'
t = b.cache.tags[0x24f9]
assert t['group'] == 'mach'
at = t['offset'] + 2
assert b.cache.unpack('H', at)[0] == 192
b.put(at - b.cache.start + b.cache.base, 'H', 64)
result = b.finish(resource_salt('C:/X360/ISOs/H3M/default.xex'))
allowed = {at, at + 1} | set(range(0x2c4, 0x2c8)) | set(range(0x330, 0x344))
diff = np.flatnonzero(np.frombuffer(result, dtype=np.uint8) != np.frombuffer(b.original, dtype=np.uint8)).tolist()
assert set(diff) <= allowed
out = work / 'elongation-local-physics-control.map'
assert not out.exists()
out.write_bytes(result)
(work / 'elongation-local-physics-control.json').write_text(json.dumps({
    'status': 'Private diagnostic; not installed',
    'change': 'Clear Early Mover Localized Physics only; retain Early Mover',
    'hypothesis': 'Overlapping localized frames may interfere with animated shape transport',
    'evidence': 'Source and native OBB blocks are empty. Sampled player reference at 0xa4 alternates red/blue machine handles. This offset is not yet independently verified against Xbox360 code. Stock Last Resort wheel has neither early-mover flag.',
    'preserved': 'All animation, shapes, placements, scripts, collision and simulation settings',
    'changed_bytes': len(diff), 'sha256': hashlib.sha256(result).hexdigest()
}, indent=2))
b.close()
print(out)
