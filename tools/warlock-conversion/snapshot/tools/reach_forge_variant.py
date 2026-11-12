"""Read original Reach v31 Forge layouts without modifying the source files.

Format references: Blam-Network/blf's Reach scenario_map_variant.ts and
Sopitive/HaloMapStudio's mvar.rs. Bounds and optional string-table compression
are decoded explicitly; unsupported versions and truncated streams fail closed.
"""
import math
import struct
import zlib


class Bits:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def read(self, count):
        if count < 0 or self.pos + count > len(self.data)*8:
            raise ValueError('Truncated variant bitstream')
        value = 0
        for _ in range(count):
            value = (value << 1) | ((self.data[self.pos//8] >> (7-self.pos%8)) & 1)
            self.pos += 1
        return value

    def raw(self, count):
        return bytes(self.read(8) for _ in range(count))

    def string(self, limit, wide=False):
        values = []
        for _ in range(limit):
            value = self.read(16 if wide else 8)
            if not value:
                break
            values.append(value)
        return (b''.join(struct.pack('>H', v) for v in values).decode('utf-16-be')
                if wide else bytes(values).decode('utf-8', errors='replace'))

    def index(self, bits):
        return -1 if self.read(1) else self.read(bits)

    def real(self):
        return struct.unpack('>f', self.raw(4))[0]


def chunks(data):
    at = 0
    while at < len(data):
        if at+12 > len(data):
            raise ValueError('Truncated BLF chunk')
        sig, size, major, minor = struct.unpack_from('>4sIHH', data, at)
        if size < 12 or at+size > len(data):
            raise ValueError('Invalid BLF chunk size')
        yield sig, major, minor, data[at+12:at+size]
        at += size


def labels(bits):
    count = bits.read(9)
    if not count:
        return []
    offsets = [bits.read(12) if bits.read(1) else None for _ in range(count)]
    size = bits.read(13)
    if bits.read(1):
        packed = bits.raw(bits.read(13))
        if len(packed) < 4 or struct.unpack_from('>I', packed)[0] != size:
            raise ValueError('Invalid compressed label size')
        data = zlib.decompress(packed[4:])
    else:
        data = bits.raw(size)
    if len(data) != size:
        raise ValueError('Label buffer size mismatch')
    result = []
    for offset in offsets:
        if offset is None:
            result.append(None)
            continue
        end = data.find(b'\0', offset)
        if not 0 <= offset <= end < len(data):
            raise ValueError('Invalid label offset')
        result.append(data[offset:end].decode('utf-8'))
    return result


def read_variant(data):
    records = [body for sig, _, _, body in chunks(data) if sig == b'mvar']
    if len(records) != 1 or len(records[0]) < 24:
        raise ValueError('Expected one Reach mvar chunk')
    # Chunk prefix: SHA1 (20 bytes), encoded payload length (4 bytes).
    bits = Bits(records[0][24:])
    content_type = bits.read(4)-1
    bits.read(32+4*64)
    activity, mode, engine = bits.read(3)-1, bits.read(3), bits.read(3)
    header_map_id, category = bits.read(32), bits.read(8)
    for _ in range(2):
        bits.read(128)
        bits.string(16)
        bits.read(1)
    title, description = bits.string(128, True), bits.string(128, True)
    if content_type in (3, 4):
        bits.read(32)
    elif content_type == 6:
        bits.read(8)
    if activity == 2:
        bits.read(16)
    if mode == 1:
        bits.read(52)
    elif mode == 2:
        bits.read(34)
    version = bits.read(8)
    if version != 31 or content_type != 5:
        raise ValueError(f'Expected Reach v31 map variant, got {version}/{content_type}')
    checksum, palette_crc = bits.read(32), bits.read(32)
    quota_count, map_id = bits.read(9), bits.read(32)
    built_in, from_xml = bits.read(1), bits.read(1)
    bounds = [bits.real() for _ in range(6)]
    if not all(math.isfinite(v) for v in bounds) or any(bounds[i] >= bounds[i+1] for i in (0, 2, 4)):
        raise ValueError('Invalid world bounds')
    max_budget, spent_budget = bits.read(32), bits.read(32)
    strings = labels(bits)
    extents = [bounds[i+1]-bounds[i] for i in (0, 2, 4)]
    axis_bits = [min(26, (int(min(0x800000, e/(0.00833333333/32*2)+0.9999))-1).bit_length()) for e in extents]
    objects = []
    for slot in range(651):
        if not bits.read(1):
            continue
        flags, folder, item = bits.read(2), bits.index(8), bits.index(5)
        in_bounds = bits.read(1)
        bsp = -1
        if not in_bounds and not bits.read(1):
            bsp = bits.read(2)
        position = [(bits.read(n)+0.5)*extents[i]/(1 << n)+bounds[2*i]
                    for i, n in enumerate(axis_bits)]
        global_up = bits.read(1)
        up = 0 if global_up else bits.read(20)
        angle, parent = bits.read(14), bits.read(10)-1
        shape = bits.read(2)
        boundary = [bits.read(11) for _ in range((0, 1, 3, 4)[shape])]
        sequence, respawn, kind = bits.read(8), bits.read(8), bits.read(5)
        label, placement, team, color = bits.index(8), bits.read(8), bits.read(4)-1, bits.index(3)
        extra = {}
        if kind == 1:
            extra['spare_clips'] = bits.read(8)
        elif kind in (12, 13, 14):
            extra.update(channel=bits.read(5), passability=bits.read(5))
        elif kind == 19:
            extra['location_name'] = bits.index(8)
        if label >= len(strings):
            raise ValueError('Object label outside string table')
        objects.append(dict(slot=slot, flags=flags, folder=folder, item=item,
                            position=position, in_bounds=in_bounds, bsp=bsp,
                            global_up=global_up, up_quantized=up, angle_quantized=angle,
                            parent=parent, shape=shape, boundary_quantized=boundary,
                            sequence=sequence if sequence < 128 else sequence-256,
                            respawn=respawn, type=kind, label=strings[label] if label >= 0 else None,
                            placement=placement, team=team, color=color, **extra))
    if quota_count > 256:
        raise ValueError('Reach quota limit exceeded')
    quotas = [dict(minimum=bits.read(8), maximum=bits.read(8), placed=bits.read(8))
              for _ in range(quota_count)]
    return dict(title=title, description=description, version=version, map_id=map_id,
                header_map_id=header_map_id, checksum=checksum, palette_crc=palette_crc,
                bounds=bounds, max_budget=max_budget, spent_budget=spent_budget,
                built_in=built_in, from_xml=from_xml, labels=strings, objects=objects,
                quotas=quotas, consumed_bits=bits.pos)
