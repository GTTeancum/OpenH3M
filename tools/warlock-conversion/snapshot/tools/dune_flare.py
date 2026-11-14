"""Explicit Dune candidate fallback to native H3 flare behavior, not fidelity."""
import hashlib
from forge_sun_flare import import_flare

SCENARIO = r'levels\multi\dune\dune'
NAME = r'levels\multi\cyclotron\sky\sun_flare_01'
BUILD = 'Jun 27 2023 08:39:36'
SOURCE_SHA256 = '5c04689665e86ced3263611e1937ce95ca45607406795d164a43f7ae6516817b'


def matches(source, name):
    return (name == NAME and [source.name(k) for k, t in source.tags.items()
                             if t['group'] == 'scnr'] == [SCENARIO])


def validate_fingerprint(build, digest, reflections, images, occlusion):
    if (build != BUILD or digest != SOURCE_SHA256 or reflections != 17
            or images != 9 or occlusion != 24):
        raise ValueError('Dune candidate flare source changed; re-audit required')


def import_dune_flare(importer, datum):
    source = importer.source
    if not matches(source, source.name(datum & 65535)):
        raise ValueError('Dune flare fallback is scoped to the audited map/material')
    root = source.tags[datum & 65535]['offset']
    rows = source.block(root + 68, 156)
    images = {(source.u(row + 20), source.unpack('H', row + 4)[0]) for row in rows}
    build = bytes(source.data[0xa0:0xc0]).split(b'\0', 1)[0].decode('ascii')
    validate_fingerprint(build, hashlib.sha256(source.data).hexdigest(), len(rows),
                         len(images), source.unpack('i', root + 8)[0])
    result = import_flare(importer, datum, native_placement=True, expected_reflections=17,
                          preserve_authored_bitmap_chains=True)
    report = importer.added[-1]
    report['dune_candidate_fallback'] = True
    report['source_sha256'] = SOURCE_SHA256
    report['differences'].extend([
        '15 authored axis offsets (-0.18 through 1.0) are replaced by native H3 placement; all offset bounds are zero',
        'Six anisotropic layers (0,2,6,10,15,16) become equal-area circles',
        'Radius curves0/1 (170..250 and100..200) and brightness curve1 (0..0.3) lose curve shape; endpoint ranges retained',
        'Source occlusion index24 exceeds17 reflections; native first-reflection occlusion used, not claimed equivalent',
        'All17 reflection layers and9 authored bitmap images retained in source order; original source unchanged',
    ])
    return result
