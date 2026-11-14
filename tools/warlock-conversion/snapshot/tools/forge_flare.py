"""Exact-source Gulch/Cove candidate adapter to native H3 flare behavior."""
import hashlib
from forge_sun_flare import NAME, import_flare

SCENARIO = r'levels\multi\forge_halo\forge_halo'
BUILD = 'Jan  3 2024 10:08:58'
SOURCE_SHA256 = '142b6246a3c764097c446e2a8c22176b12cb341a9d90cfe72afbf71595e4c5e5'


def matches(importer, name):
    source = importer.source
    return (name == NAME and getattr(importer, 'slot', None) == 'sandbox'
            and bool(getattr(importer, 'gulch_partition', None))
            and getattr(importer, 'forge_partition_side', None) in ('gulch', 'island')
            and [source.name(k) for k,t in source.tags.items() if t['group']=='scnr'] == [SCENARIO])


def validate_fingerprint(build, digest, reflections, images, occlusion):
    if (build, digest, reflections, images, occlusion) != (BUILD, SOURCE_SHA256, 18, 10, 10):
        raise ValueError('Forge partition flare source changed; re-audit required')


def import_forge_flare(importer, datum):
    source = importer.source
    if not matches(importer, source.name(datum & 65535)):
        raise ValueError('Forge flare fallback requires the audited Gulch/Cove partition')
    root = source.tags[datum & 65535]['offset']
    rows = source.block(root+68,156)
    images = {(source.u(row+20),source.unpack('H',row+4)[0]) for row in rows}
    build = bytes(source.data[160:192]).split(b'\0',1)[0].decode('ascii')
    validate_fingerprint(build,hashlib.sha256(source.data).hexdigest(),len(rows),len(images),source.unpack('i',root+8)[0])
    result = import_flare(importer,datum,native_placement=True,expected_reflections=18,
                          preserve_authored_bitmap_chains=True)
    report = importer.added[-1]
    if len(report['bitmap_preservation']) != 10 or sum(x['output_mips'] for x in report['bitmap_preservation']) != 92:
        raise ValueError('Forge flare authored image/mip fingerprint changed')
    report.update(forge_partition_candidate_fallback=True, partition_side=importer.forge_partition_side,
                  source_sha256=SOURCE_SHA256)
    report['differences'].extend([
        '15 nonzero authored axis offsets replaced by native H3 placement; all source offset bounds are zero',
        'Source occlusion reflection10 becomes native first reflection0; source order retained, not equivalent occlusion',
        'Seven anisotropic reflections (0,2,6,10,15,16,17) become equal-area circles',
        'Three nonconstant radius curves (0,1,17) and brightness curve1 reduce to endpoint ranges; curve shapes not preserved',
        'All18 reflections and10 source images retained; all92 authored mips at full source resolution; original source unchanged',
    ])
    return result
