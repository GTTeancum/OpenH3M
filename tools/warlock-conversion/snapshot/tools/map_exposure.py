"""Explicit per-map camera corrections; never changes shared stock cameras."""
import struct

# EV offsets are candidate tuning values, recorded in the build report.
# Match both source cache and tag: similarly named cameras in other maps
# must retain their original values.
PROFILES = {
    # The resulting -3.321928 auto target matches stock Cyberdyne's indoor
    # camera. Preserve this map's adaptation speed and narrower bounds.
    ('h2_elongation.map', r'levels\dlc\fortress\fortress_fx - copy'): 1.0,
    # Separate candidates for the other dark ports; require native inspection.
    ('lockoutfix.map', r'levels\multi\lockoutfix\chill'): 1.0,
    ('sancr.map', r'levels\multi\sancr\base_camera'): 0.65,
    # Rodentia: preserve authored source lighting (user decision 2026-11-05).
    # No per-map exposure override is permitted.
    ('cex_beavercreek.map', r'levels\multi\cex_beavercreek\cex_beaver_creek'): 0.35,
    ('cex_beavercreek.map', r'levels\multi\020_sword_slayer\post_fx\20_sword_slayer'): 0.65,
}


def adjust_camera(source, name, payload, notes):
    key = (source.file.name.replace('\\', '/').rsplit('/', 1)[-1], name)
    if key == ('s3d_powerhouse.map', r'levels\multi\s3d_powerhouse\s3d_powerhouse'):
        data = bytearray(payload)
        flags = struct.unpack_from('>H', data)[0]
        bounds = struct.unpack_from('>2f', data, 0x10)
        sensitivity_flags = struct.unpack_from('>H', data, 0x20)[0]
        sensitivity = struct.unpack_from('>f', data, 0x24)[0]
        if (flags != 20 or bounds != (0.0, 2.0) or sensitivity_flags != 0
                or not abs(sensitivity - 0.3) <= 1e-6):
            raise ValueError('Powerhouse camera profile requires authored range 0..2 and sensitivity 0.3')
        struct.pack_into('>f', data, 0x14, 4.0)
        struct.pack_into('>f', data, 0x24, 1.0)
        notes.append('Powerhouse indoor adaptation ceiling: 2 -> 4 stops; authored target, '
                     'minimum and speed retained. Bright-area sensitivity: 0.3 -> 1; '
                     'bloom and color settings retained. Requires functioning '
                     'native brightness feedback; no baked ambient compensation.')
        return data
    stops = PROFILES.get(key)
    if stops is None:
        return payload
    data = bytearray(payload)
    flags = struct.unpack_from('>H', data)[0]
    if flags & 1 or not flags & 4:
        raise ValueError(f'{name}: expected explicit authored auto-exposure')
    before = {offset: struct.unpack_from('>f', data, offset)[0]
              for offset in (0x10, 0x14, 0x18)}
    for offset, value in before.items():
        struct.pack_into('>f', data, offset, value + stops)
    notes.append(f'Per-map brightness candidate: auto-exposure target and bounds '
                 f'+{stops:g} EV; prior bounds {before[0x10]:g}..{before[0x14]:g}, '
                 f'target {before[0x18]:g}. Bloom/color settings unchanged.')
    return data
