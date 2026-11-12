"""Compare adapted AFM3 and untouched H4 Base Round markers in original code.

This isolates marker generation and held-magnet submission, not world physics.
"""
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
from source_marker_data import SourceMarkerCache

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "work/h4-forge-research/isolated"
pack = ROOT / "work/rexglue-sdk/out/win-amd64/advanced-forge/isolated/markers.bin"
models = json.loads((OUT.parent / "ravine-magnets.json").read_text())["data"]
model, = [m for m in models if m["name"].endswith("fw_unsc_c_base_round")]
cache = SourceMarkerCache(OUT.parent / "disc2-assets/ca_forge_ravine.map")
try:
    records = cache.records(model["tag_index"])
finally:
    cache.close()
# The radius is solely a broad-phase envelope. It is not a claim about H4's
# runtime sphere. Enclose every original point plus the diagnostic separation.
poses = [struct.unpack_from(">7f", record, 4) for record in records]
radius = max(sum(v*v for v in pose[:3])**.5 for pose in poses) + 1
payload = struct.pack("<4sIIIfII", b"AFM3", 1, 1730, 0x90002952, radius, len(records), 0)
payload += b"".join(struct.pack("<7f", *pose) for pose in poses)
payload += b"".join(records)
source = OUT / "coincident-source-markers.bin"
source.write_bytes(payload)
results = []
for label, path in (("current-adapted", pack), ("untouched-h4-markers", source)):
    run = subprocess.run([str(OUT / "test_bridge.exe"), "--coincident-pack", str(path)],
                         cwd=ROOT, text=True, capture_output=True, check=True)
    print(label + "\n" + run.stdout, end="")
    match = re.search(r"held-caller opposed=0 target=(\d+) position=([^\n]+)", run.stdout)
    if not match:
        raise RuntimeError("Original held caller did not report the same-facing case")
    position = list(map(float, match[2].split(",")))
    coincident = int(match[1]) == 456 and all(abs(a-b) < 1e-5 for a,b in zip(position, (0,.1,0)))
    results.append(dict(input=label, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        source_model=model["name"], same_facing_target_coincident=coincident,
                        output=run.stdout))
(OUT / "coincident-snap-result.json").write_text(json.dumps(results, indent=2) + "\n")
