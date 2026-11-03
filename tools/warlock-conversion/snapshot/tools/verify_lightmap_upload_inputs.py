"""Read-only check of cache inputs consumed by the native lightmap upload path.

Does not prove that the path executes or that GPU constants receive these values.
Run from the repository with -B; private cache paths must remain private.
"""
import argparse
import hashlib
import json
from pathlib import Path

from cache_reader import Cache


def inspect(path):
    cache = Cache(path)
    try:
        scenarios = [t for t in cache.tags.values() if t['group'] == 'scnr']
        assert len(scenarios) == 1, 'Expected one scenario'
        scenario = scenarios[0]['offset']
        datum = cache.u(scenario + 1788)
        tag = cache.tags[datum & 65535]
        assert tag['group'] == 'sLdT' and tag['salt'] == datum >> 16
        bsps = cache.block(scenario + 20, 108)
        rows = []
        for row in cache.block(tag['offset'] + 4, 436):
            index = cache.unpack('h', row + 2)[0]
            assert 0 <= index < len(bsps), 'Invalid BSP index'
            bsp_datum = cache.u(bsps[index] + 12)
            bsp = cache.tags[bsp_datum & 65535]
            assert bsp['group'] == 'sbsp' and bsp['salt'] == bsp_datum >> 16
            checks = {
                'bsp_checksum_matches': cache.u(row + 4) == cache.u(bsp['offset']),
                'geometry_mesh_count_matches': cache.u(row + 308) == cache.u(bsp['offset'] + 740),
            }
            textures = {}
            for name, offset in (('lightprobe', 236), ('dominant', 252)):
                texture_datum = cache.u(row + offset)
                texture = cache.tags[texture_datum & 65535]
                assert texture['group'] == 'bitm' and texture['salt'] == texture_datum >> 16
                images = cache.block(texture['offset'] + 96, 48)
                assert images, 'Bitmap contains no image records'
                image = images[0]
                textures[name] = dict(datum=hex(texture_datum),
                                     dimensions=list(cache.unpack('HHB', image + 4)))
            checks['eight_layer_upload_gate'] = textures['lightprobe']['dimensions'][2] == 8
            scales = [cache.unpack('f', row + 8 + i * 24)[0] for i in range(9)]
            rows.append(dict(bsp=index, flags=cache.unpack('H', row)[0],
                             checks=checks, scales=scales, textures=textures))
        return dict(cache=str(path), bsps=rows,
                    scope='Static prerequisites only; live upload and visual correctness remain unverified.')
    finally:
        cache.close()


def verify_guest_path(root):
    """Fail if the inspected guest function no longer contains the observed path."""
    path = root / 'halo3mp/generated/default/halo3mp_recomp.41.cpp'
    data = path.read_bytes()
    function = data.decode().split('DEFINE_REX_FUNC(sub_821835D0) {', 1)[1].split('DEFINE_REX_FUNC', 1)[0]
    expected = ['loc_82183D2C:', '// lwz r4,236(r30)', '// bl 0x82180008',
                '// lbz r11,8(r11)', '// cmplwi cr6,r11,8',
                '// bne cr6,0x82183ef4']
    expected += [f'// lfs f{reg},{offset}(r30)' for reg, offset in
                 ((11, 8), (12, 32), (13, 56), (11, 80), (12, 104),
                  (13, 128), (11, 152), (12, 176), (13, 200))]
    expected += [f'// stfs f11,{offset}(r11)' for offset in (9376, 9392, 9408)]
    for marker in expected:
        assert marker in function, f'Guest path changed: {marker}'
    return dict(function='0x821835d0', lightprobe_case='0x82183d2c',
                source_sha256=hashlib.sha256(data).hexdigest(),
                device_vector_offsets=[9376, 9392, 9408],
                compression_byte_offsets=list(range(8, 201, 24)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    args = parser.parse_args()
    result = inspect(args.cache)
    result['native_path'] = verify_guest_path(Path.cwd())
    print(json.dumps(result, indent=2))
    assert all(all(row['checks'].values()) for row in result['bsps']), 'Native prerequisites failed'
