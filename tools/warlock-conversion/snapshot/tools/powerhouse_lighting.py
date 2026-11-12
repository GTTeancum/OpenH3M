"""Opt-in Powerhouse ambient calibration; no exposure or directional edits."""
import struct
import numpy as np


def configure(source, quarter_stops):
    if quarter_stops not in range(9):
        raise ValueError('Ambient calibration must be 0..8 quarter stops')
    if quarter_stops:
        names = [source.name(k) for k, t in source.tags.items() if t['group'] == 'scnr']
        if not source.mcc or names != [r'levels\multi\s3d_powerhouse\s3d_powerhouse']:
            raise ValueError('Ambient calibration is restricted to Powerhouse')
    source.powerhouse_ambient_quarter_stops = quarter_stops


def boost_vertices(payload, quarter_stops):
    """C0 is vector 1 in [dominant,C0,C1,C2,C3], each signed RGBE ABGR.

    Incrementing its exponent by q multiplies ambient by 2**(q/4),
    without requantizing RGB or touching direction, intensity or zero vectors.
    """
    if quarter_stops not in range(9) or len(payload) % 20:
        raise ValueError('Invalid ambient adjustment or lighting vertex layout')
    if not quarter_stops:
        return payload
    values = np.frombuffer(payload, dtype=np.uint8).reshape(-1, 20).copy()
    active = np.any(values[:, 5:8] != 0, axis=1)
    exponent = values[:, 4].view(np.int8).astype(np.int16)
    if np.any(exponent[active] + quarter_stops > 127):
        raise ValueError('Ambient RGBE exponent overflow')
    values[active, 4] = ((exponent[active] + quarter_stops) & 255).astype(np.uint8)
    return values.tobytes()


def boost_atlas(bsp, quarter_stops):
    if quarter_stops not in range(9):
        raise ValueError('Invalid ambient adjustment')
    if not quarter_stops:
        return bsp
    result = bytearray(bsp)
    scale = struct.unpack_from('>f', result, 8)[0]
    if not np.isfinite(scale) or scale < 0:
        raise ValueError('Invalid lightmap C0 luminance scale')
    struct.pack_into('>f', result, 8, scale * 2 ** (quarter_stops / 4))
    return result
