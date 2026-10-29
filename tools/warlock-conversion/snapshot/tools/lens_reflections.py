"""Recover retail reflection ranges from MCC's legacy linear flare curves."""
import struct


def convert_reflection(source, at):
    flags, pad, bitmap, pad2 = source.unpack('4H', at)
    if (not flags & 0x1000 or flags & ~0x1fff or pad or pad2
            or source.u(at + 20) != 0xffffffff or any(source.unpack('6I', at + 32))):
        raise ValueError('Lens reflection requires legacy mode, no override, and default offset/range fields')

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
    if function(76) not in (unit, unit_range) or function(96) not in (unit, unit_range):
        raise ValueError('Non-unit lens reflection scaling has no retail representation')
    ranges = []
    for offset in (56, 116):
        data = function(offset)
        # Identity function with range endpoints: the retail legacy range is
        # the same interpolation, without MCC's function allocation.
        if len(data) == 32 and data[:4] == bytes.fromhex('00340000') and data[12:] == bytes(20):
            ranges.extend(struct.unpack_from('<2I', data, 4))
            continue
        # Header declares exactly 20 live spline bytes. Longer allocations
        # contain stale editor capacity, not additional runtime sections.
        if (len(data) < 52 or data[:4] != bytes.fromhex('08240000')
                or data[12:28] != bytes(16) or data[28:52] != bytes.fromhex(
                    '1400000001000000040000cdffff7f7f0000803f00000000')):
            raise ValueError('Lens curve is not the verified legacy linear range')
        ranges.extend(struct.unpack_from('<2I', data, 4))
    # Retail always uses this legacy path; bit 12 is MCC's selector, absent
    # in the matching original-disc reflection records.
    return (struct.pack('>HH2I', flags & ~0x1000, bitmap, *source.unpack('2I', at + 24))
            + struct.pack('>4I', *ranges)
            + struct.pack('>I3II', source.u(at + 148), *source.unpack('3I', at + 136), source.u(at + 152)))
