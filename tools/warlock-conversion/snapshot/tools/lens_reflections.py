"""Recover retail reflection ranges from MCC's legacy linear flare curves."""
import struct
import math


def _legacy_linear_payload(data):
    # Type8Section: byte 36 is its opcode; bytes 37..39 are unused padding.
    # TagFunction.cs Type8Section.Read confirms these are not coefficients.
    # H3EK allocations contain varying padding (CD, 3F, etc.). Require every
    # semantic byte of the existing supported single-section curve unchanged.
    return (len(data) >= 52
            and data[28:37] == bytes.fromhex('140000000100000004')
            and data[40:52] == bytes.fromhex('ffff7f7f0000803f00000000'))


def convert_reflection(source, at):
    flags, pad, bitmap, pad2 = source.unpack('4H', at)
    if (flags & ~0x1fff or pad or pad2
            or source.u(at + 20) != 0xffffffff or any(source.unpack('6I', at + 32))):
        raise ValueError('Lens reflection requires no override and default offset/range fields')

    def function(offset):
        size = source.u(at + offset)
        pointer = source.pointer(source.u(at + offset + 12))
        if size < 32 or pointer < 0 or pointer + size > len(source.data):
            raise ValueError('Lens curve data is outside source cache')
        return bytes(source.data[pointer:pointer + size])

    # MCC added independent X/Y scaling; unit constants preserve H3's circular
    # reflection. Reject non-unit scaling instead of silently distorting it.
    unit = bytes.fromhex('012400000000803f000000000000000000000000000000000000000000000000')
    unit_range = bytes.fromhex('013400000000803f0000803f0000000000000000000000000000000000000000')
    # H3EK also writes the constant opcode with both bounds explicitly one.
    # This is still a unit scale, not independent anisotropic scaling.
    unit_both = bytes.fromhex('012400000000803f0000803f0000000000000000000000000000000000000000')
    if function(76) not in (unit, unit_range, unit_both) or function(96) not in (unit, unit_range, unit_both):
        raise ValueError('Non-unit lens reflection scaling has no retail representation')
    ranges = []
    for offset in (56, 116):
        data = function(offset)
        # Equal scalar ScaleBounds produce a constant even when the editor
        # leaves nonzero timing values in the header. TagTool TagFunction's
        # scalar header and ScaleOutput establish this independently of timing.
        if (data[:4] in (bytes.fromhex('00340000'), bytes.fromhex('01340000'),
                         bytes.fromhex('08240000'))
                and data[4:8] == data[8:12] and math.isfinite(struct.unpack_from('<f', data, 4)[0])
                and ((data[0] in (0,1) and len(data)==32) or
                     (data[0]==8 and len(data)>=52 and _legacy_linear_payload(data)))):
            ranges.extend(struct.unpack_from('<2I', data, 4))
            continue
        # Identity function with range endpoints: the retail legacy range is
        # the same interpolation, without MCC's function allocation.
        if len(data) == 32 and data[:4] == bytes.fromhex('00340000') and data[12:] == bytes(20):
            ranges.extend(struct.unpack_from('<2I', data, 4))
            continue
        # Header declares exactly 20 live spline bytes. Longer allocations
        # contain stale editor capacity, not additional runtime sections.
        if (len(data) < 52 or data[:4] != bytes.fromhex('08240000')
                or data[12:28] != bytes(16) or not _legacy_linear_payload(data)):
            raise ValueError('Lens curve is not the verified legacy linear range')
        ranges.extend(struct.unpack_from('<2I', data, 4))
    if not flags & 0x1000 and any(value & 0x7fffffff for value in ranges[2:]):
        # Modern curves can use a different input domain. A verified identically
        # zero brightness curve is invisible in either domain; preserve that
        # disabled reflection without generalizing nonlegacy animation behavior.
        raise ValueError('Nonlegacy lens reflection requires identically zero brightness')
    if source.unpack('f', at + 28)[0] != 0.0:
        raise ValueError('MCC lens axis offset has no verified retail representation')
    # Original executable sub_82471B78 reads bitmap at +4; sub_82472380
    # reads rotation at +8. The old plugin incorrectly packed these at +2/+4.
    # Retail always uses this legacy path; bit 12 is MCC's selector, absent
    # in the matching original-disc reflection records.
    return (struct.pack('>H2xH2xI', flags & ~0x1000, bitmap, source.u(at + 24))
            + struct.pack('>4I', *ranges)
            + struct.pack('>I3II', source.u(at + 148), *source.unpack('3I', at + 136), source.u(at + 152)))
