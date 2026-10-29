"""Endian conversion for observed identity, constant, transition and spline functions."""
import struct


def convert_function(data):
    if len(data) < 32 or data[2] > 4 or data[3]:
        raise ValueError('Invalid tag-function header')
    out = bytearray(data)

    def words(start, count):
        end = start + count * 4
        if end > len(data):
            raise ValueError('Truncated tag-function data')
        for at in range(start, end, 4):
            out[at:at + 4] = data[at:at + 4][::-1]
        return end

    words(4, 7)
    if struct.unpack_from('<I', data, 28)[0] != len(data) - 32:
        raise ValueError('Tag-function payload length mismatch')
    at = 32
    for _ in range(2 if data[1] & 1 else 1):
        if data[0] in (0, 1):
            continue
        if data[0] in (2, 3):
            # Transition selector and three pad bytes remain bytes.
            at = words(at + 4, 2 if data[0] == 2 else 4)
        elif data[0] in (4, 5, 7, 9, 10):
            # Fixed float payloads described by TagTool's TagFunctionType
            # 4/5/7/9/AData serializers (Tags/TagFunction.cs).
            at = words(at, {4: 2, 5: 20, 7: 4, 9: 3, 10: 7}[data[0]])
        elif data[0] == 8:
            count = struct.unpack_from('<I', data, at)[0]
            at = words(at, 1)
            if count > 1024:
                raise ValueError('Excessive tag-function spline sections')
            for _ in range(count):
                if at >= len(data):
                    raise ValueError('Unsupported spline section layout')
                at = words(at + 4, 3 if data[at] == 4 else 5 if data[at] == 7 else 8)
        else:
            raise ValueError(f'Tag-function opcode {data[0]} is not implemented')
    if (data[0] == 8 and data[1] == 0x34
            and data[at:] == bytes.fromhex('070000cd0000000000000000cdcc4c3d')):
        # Banshee hull-destruction retains an unused 16-byte editor tail
        # beyond its one counted spline section. The original bunkerworld
        # effect has these exact bytes, including the little-endian residue.
        # Preserve the verified tail rather than treating it as live floats.
        at = len(data)
    if at != len(data):
        raise ValueError(f'Unconsumed tag-function data: opcode={data[0]} flags={data[1]:#x} consumed={at} size={len(data)}')
    return bytes(out)
