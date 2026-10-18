"""Endian-convert Halo 3 animation resources without resampling animations.

Layouts follow TagTool's ModelAnimationTagResource and codec readers. Unsupported
codecs/movement payloads fail before the scratch resource can be registered.
"""
import struct


def convert_codec(data, frames):
    out = bytearray(data)
    if len(data) < 32:
        raise ValueError('Truncated animation codec')
    codec, rotations, translations, scales = data[:4]

    def swap(start, end, width):
        if not 0 <= start <= end <= len(data) or (end - start) % width:
            raise ValueError('Invalid animation stream bounds/alignment')
        for at in range(start, end, width):
            out[at:at + width] = data[at:at + width][::-1]

    if codec in (1, 3, 8):
        swap(4, 32, 4)
        tr, sc, rb, tb, sb = struct.unpack_from('<5I', data, 12)
        if codec == 1:
            # Static codecs store one pose per node, contiguously.
            tr = 32 + rotations * 8
            sc = tr + translations * 12
            end = sc + scales * 4
        else:
            rotation_width = 16 if codec == 8 else 8
            if (rb, tb, sb) != (frames * rotation_width, frames * 12, frames * 4):
                raise ValueError('Unexpected animation node stride')
            if tr != 32 + rb * rotations or sc != tr + tb * translations:
                raise ValueError('Animation node offsets disagree with strides')
            end = sc + sb * scales
        if end > len(data) or any(data[end:]):
            raise ValueError('Unexpected animation codec trailing data')
        swap(32, tr, 4 if codec == 8 else 2)
        swap(tr, end, 4)
    elif codec in (4, 6):
        if len(data) < 48:
            raise ValueError('Truncated keyframe codec')
        ti, si, rk, tk, sk, rf, tf, sf, padding = struct.unpack_from('<9I', data, 12)
        if not (ti == 48 + rotations * 4 and si == ti + translations * 4
                and rk == si + scales * 4 and rk <= tk <= sk <= rf <= tf <= sf <= len(data)):
            raise ValueError('Invalid keyframe stream offsets')
        if padding:
            raise ValueError('Unexpected keyframe codec padding')
        swap(4, rk, 4)
        # Byte key indices stay byte-for-byte; reverse codecs use the same
        # representation, with reversed node ordering interpreted by the engine.
        swap(rf, tf, 2)
        swap(tf, len(data), 4)
    else:
        raise ValueError(f'Animation codec {codec} is not implemented')
    return bytes(out)


def convert_animation_resource(source, translate_string):
    count = source.unpack('I', source.root)[0]
    table = source.ptr(source.root + 4) if count else 0
    control = bytearray(12 + count * 48)
    struct.pack_into('>I', control, 0, count)
    fixups = [(4, 0x2000000c)] if count else []
    raw = bytearray()
    codecs = set()
    for index in range(count):
        at, dst = table + index * 48, 12 + index * 48
        values = list(source.unpack('IIHBB2B3H2I', at))
        name, checksum, frames, nodes, movement, sf, af, md, pill, static, unpacked, compressed = values
        if movement or md or pill or unpacked:
            raise ValueError('Animation movement/uncompressed payload is not implemented')
        size = source.unpack('I', at + 28)[0]
        if any(source.unpack('II', at + 32)) or source.unpack('I', at + 44)[0]:
            raise ValueError('Unexpected animation data-reference flags')
        pointer = source.fix[at + 40]
        segment = {0x40000000: 0, 0x60000000: 1}.get(pointer & 0xe0000000)
        start = pointer & 0x1fffffff
        if segment is None or segment >= len(source.raw):
            raise ValueError('Invalid animation resource segment')
        data = source.raw[segment][start:start + size]
        if len(data) != size or size != static + compressed + sf + af or (sf + af) % 4:
            raise ValueError('Animation payload size does not match member header')
        payload = bytearray()
        if static:
            if data[0] != 1:
                raise ValueError('Unexpected static animation codec')
            payload.extend(convert_codec(data[:static], frames))
            codecs.add(1)
        codecs.add(data[static])
        payload.extend(convert_codec(data[static:static + compressed], frames))
        for pos in range(static + compressed, size, 4):
            payload.extend(data[pos:pos + 4][::-1])
        values[0] = translate_string(name)
        struct.pack_into('>IIHBB2B3H2I', control, dst, *values)
        struct.pack_into('>I', control, dst + 28, size)
        raw.extend(bytes((-len(raw)) % 16))
        fixups.append((dst + 40, 0x40000000 | len(raw)))
        raw.extend(payload)
    return {'control': bytes(control), 'raw': bytes(raw), 'root': 0,
            'fixups': fixups, 'interops': [], 'members': count, 'codecs': sorted(codecs)}
