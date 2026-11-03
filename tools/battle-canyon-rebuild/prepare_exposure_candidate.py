"""Create a Battle Canyon user-review candidate with more adaptation headroom.

The restored sky RGB is a source-data correction. This separate camera change
is brightness calibration, not a claim to have fixed or measured auto exposure.
Only the authored 1.8-stop ceiling becomes 4; target/minimum/bloom remain exact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/battle-canyon/rebuild'
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from build_scenario_checkpoint import resource_salt
from warlock_handoff import preflight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(strict=True), args.output.resolve()
    assert source.is_relative_to(WORK) and output.is_relative_to(WORK)
    assert not output.exists(), 'Do not overwrite an existing candidate'
    xex = Path('C:/X360/ISOs/H3M/default.xex')
    before_check = preflight(source, xex)
    cache = Cache(source)
    try:
        scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
        datum = cache.u(scenario+0x6b0+12)
        tag = cache.tags[datum & 65535]
        assert tag['group'] == 'cfxs' and tag['salt'] == datum >> 16
        at = tag['offset']
        camera = bytes(cache.data[at:at+0xe4])
        flags = struct.unpack_from('>H', camera)[0]
        bounds_target = struct.unpack_from('>3f', camera, 0x10)
        assert flags == 20
        assert abs(bounds_target[0]) < 1e-6 and abs(bounds_target[1]-1.8) < 1e-6
        assert abs(bounds_target[2]+3.321928094887362) < 1e-6
        assert struct.unpack_from('>f', camera, 0x24)[0] == 1.0
        assert cache.u(scenario+8) in (30, 1733)
        header_name = cache.data[0x18c:0x1ac].split(b'\0')[0]
        assert header_name in (b'zanzibar', b'battle_canyon')
        old = cache.u(at+0x14)
    finally:
        cache.close()
    header = bytearray(source.read_bytes()[:0x3000])
    replacement = struct.pack('>f', 4.0)
    checksum = struct.unpack_from('>I', header, 0x2c4)[0] ^ old ^ struct.unpack('>I', replacement)[0]
    struct.pack_into('>I', header, 0x2c4, checksum)
    normalized = bytearray(header)
    for start, length in ((0x320,4),(0x328,8),(0x330,0x13c),(0x1c,0x100),
                          (0x144,8),(0x16c,0x20),(0x49c,0x10)):
        normalized[start:start+length] = bytes(length)
    header[0x330:0x344] = hashlib.sha1(resource_salt(xex)+normalized).digest()
    shutil.copyfile(source, output)
    with output.open('r+b') as stream:
        stream.write(header)
        stream.seek(at+0x14)
        stream.write(replacement)
    # Independently prove byte preservation, including every lighting resource.
    original, adjusted = source.read_bytes(), bytearray(output.read_bytes())
    for offset, size in ((at+0x14,4),(0x2c4,4),(0x330,20)):
        adjusted[offset:offset+size] = original[offset:offset+size]
    assert adjusted == original, 'Change escaped camera ceiling/checksum/header authentication'
    checked = preflight(output, xex)
    report = dict(status='candidate for user visual review; not installed or runtime accepted',
                  source=before_check, output=checked, camera_datum=hex(datum),
                  camera_offset=at, before_bounds_and_target=bounds_target,
                  after_bounds_and_target=[0.0,4.0,bounds_target[2]],
                  only_ceiling_checksum_auth_changed=True,
                  rationale='User rejected darkness; permit adaptation beyond 1.8 stops without changing target or minimum.',
                  limitations='Current exposure saturation is not measured; no claim that this alone resolves darkness.')
    output.with_suffix('.exposure.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
