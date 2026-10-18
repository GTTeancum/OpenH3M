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
        if data[0] == 2:
            # Transition selector and three pad bytes remain bytes.
            at = words(at + 4, 2)
        elif data[0] == 8:
            count = struct.unpack_from('<I', data, at)[0]
            at = words(at, 1)
            if count > 1024:
                raise ValueError('Excessive tag-function spline sections')
            for _ in range(count):
                if at >= len(data) or data[at] not in (4, 7):
                    raise ValueError('Unsupported spline section layout')
                at = words(at + 4, 3 if data[at] == 4 else 5)
        else:
            raise ValueError(f'Tag-function opcode {data[0]} is not implemented')
    if at != len(data):
        raise ValueError('Unconsumed tag-function data')
    return bytes(out)
