"""Explicit native-camera fallback for the identified Dune MCC source.

Original H3 has no SSAO camera extension. This narrowly approved conversion
omits that effect, not an equivalent replacement or a host renderer change.
"""
import struct

SCENARIO = r'levels\multi\dune\dune'
BUILD = b'Jun 27 2023 08:39:36'
SSAO = struct.pack('<I3f', 0x12, 1.0, 0.75, 0.5)
NOTE = ('Dune-only native camera fallback (2026-11-14): active MCC SSAO '
        'omitted; intensity 1.0, radius 0.75, sample-z threshold 0.5. Original H3 '
        'has no equivalent camera effect. Exposure, bloom and supported lighting '
        'remain authored; contact/corner darkening can differ. No visual '
        'equivalence or runtime acceptance is claimed.')


def allow_native_camera(source, name, root, extension_offset):
    if extension_offset != 0xe4 or name != SCENARIO:
        return False
    if [source.name(k) for k, tag in source.tags.items() if tag['group'] == 'scnr'] != [SCENARIO]:
        return False
    build = source.data[0xa0:0xc0].split(b'\0')[0]
    if build != BUILD or source.data[root + 0xe4:root + 0xf4] != SSAO:
        raise ValueError('Dune camera differs from the explicitly audited native fallback')
    return True
