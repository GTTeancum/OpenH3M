"""Halo 3 packed Forge layout codec (BLF mvar 12, body 13/14).

Wire format checked against shipped H3 layouts and HaloMapStudio's documented
engine reader/writer. Quota definitions are palette kind/index pairs, NOT tag
datums. Pose quanta are retained losslessly when reading an existing layout.
This module does not sign or package Xbox saved-content containers.
"""
import math
import struct
from reach_forge_variant import Bits, chunks


class Writer:
    def __init__(self):
        self.data, self.pos = bytearray(), 0

    def write(self, value, count):
        if not isinstance(value, int) or not 0 <= value < 1 << count:
            raise ValueError(f'Value outside {count}-bit unsigned field: {value}')
        for shift in range(count - 1, -1, -1):
            if self.pos % 8 == 0:
                self.data.append(0)
            self.data[-1] |= ((value >> shift) & 1) << (7 - self.pos % 8)
            self.pos += 1

    def string(self, value, limit, wide=False):
        data = value.encode('utf-16-be' if wide else 'utf-8')
        units = list(struct.unpack('>' + 'H' * (len(data) // 2), data)) if wide else list(data)
        if len(units) > limit or 0 in units:
            raise ValueError('Variant string exceeds field capacity or contains NUL')
        for unit in units + ([0] if len(units) < limit else []):
            self.write(unit, 16 if wide else 8)

    def real(self, value):
        if not math.isfinite(value):
            raise ValueError('Nonfinite variant number')
        self.write(struct.unpack('>I', struct.pack('>f', value))[0], 32)


class Fields:
    def __init__(self, stream, writing):
        self.stream, self.writing = stream, writing

    def number(self, obj, name, count, bias=0):
        if self.writing:
            self.stream.write(obj[name] + bias, count)
        else:
            obj[name] = self.stream.read(count) - bias
        return obj[name]

    def string(self, obj, name, limit, wide=False):
        if self.writing:
            self.stream.string(obj[name], limit, wide)
        else:
            obj[name] = self.stream.string(limit, wide)

    def real(self, obj, name):
        if self.writing:
            self.stream.real(obj[name])
        else:
            obj[name] = self.stream.real()
            if not math.isfinite(obj[name]):
                raise ValueError('Nonfinite variant number')


def payload(stream, value=None):
    writing = value is not None
    v = value if writing else {'header': {}}
    f, header = Fields(stream, writing), v['header']
    f.number(header, 'unique_id', 64)
    for name, size, wide in [('name', 16, True), ('description', 128, False), ('author', 16, False)]:
        f.string(header, name, size, wide)
    for name, count, bias in [('file_type', 5, 1), ('author_is_online', 1, 0),
                             ('author_xuid', 64, 0), ('size_bytes', 64, 0), ('date', 64, 0),
                             ('length_seconds', 32, 0), ('campaign_id', 32, 0), ('map_id', 32, 0),
                             ('game_engine_type', 4, 0), ('campaign_difficulty', 3, 1),
                             ('hopper_id', 16, 0), ('game_id', 64, 0)]:
        f.number(header, name, count, bias)
    for name, count in [('version', 8), ('checksum', 32), ('scenario_count', 10),
                        ('slot_count', 10), ('quota_count', 9), ('map_id', 32), ('built_in', 1)]:
        f.number(v, name, count)
    if v['version'] not in (13, 14) or not 0 <= v['scenario_count'] <= v['slot_count'] <= 640 or v['quota_count'] > 256:
        raise ValueError('Unsupported H3 layout version or counts')
    if not writing:
        v['bounds'] = {}
    for name in ('xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'):
        f.real(v['bounds'], name)
    f.number(v, 'engine_subtype', 4)
    f.real(v, 'maximum_budget')
    f.real(v, 'spent_budget')
    if writing:
        objects = {o['slot']: o for o in v['objects']}
        if len(objects) != len(v['objects']) or any(not 0 <= k < v['slot_count'] for k in objects):
            raise ValueError('Duplicate or out-of-range object slots')
    else:
        objects = {}
    for slot in range(v['slot_count']):
        if writing:
            present = slot in objects
            stream.write(int(present), 1)
        else:
            present = stream.read(1)
        if not present:
            continue
        obj = objects[slot] if writing else {'slot': slot}
        objects[slot] = obj
        f.number(obj, 'flags', 16)
        f.number(obj, 'quota', 32)
        if writing:
            stream.write(int(obj.get('parent') is not None), 1)
            has_parent = obj.get('parent') is not None
        else:
            has_parent = stream.read(1)
            obj['parent'] = None
        if has_parent:
            f.number(obj, 'parent', 64)
        if not f.number(obj, 'placed', 1):
            continue
        if obj['quota'] >= v['quota_count']:
            raise ValueError('Placement references missing quota')
        for name in ('x', 'y', 'z'):
            f.number(obj, name + '_q', 16)
        if not f.number(obj, 'global_up', 1):
            f.number(obj, 'up_q', 19)
        for name, count in [('angle_q', 8), ('object_type', 8), ('mp_flags', 8),
                            ('engine_flags', 16), ('shared_storage', 8), ('spawn_time', 8),
                            ('team', 8), ('shape', 8)]:
            f.number(obj, name, count)
        if obj['shape'] > 3:
            raise ValueError('Unknown H3 boundary shape')
        for index in range((0, 1, 3, 4)[obj['shape']]):
            f.number(obj, f'boundary_{index}_q', 16)
    if not writing:
        v['objects'] = list(objects.values())
        v['type_starts'] = {}
        v['quotas'] = [{} for _ in range(v['quota_count'])]
    if len(v['quotas']) != v['quota_count']:
        raise ValueError('Quota count differs from supplied table')
    for index in range(14):
        f.number(v['type_starts'], str(index), 9, 1)
    for quota in v['quotas']:
        for name, count in [('definition', 32), ('minimum', 8), ('maximum', 8),
                            ('placed_on_map', 8), ('maximum_allowed', 8)]:
            f.number(quota, name, count)
        f.real(quota, 'price')
    if v['version'] == 14:
        f.number(v, 'mcc_map_id', 128)
    return v


def read_variant(data):
    found = [(major, minor, body) for sig, major, minor, body in chunks(data) if sig == b'mvar']
    if len(found) != 1 or found[0][:2] != (12, 1):
        # Some native layouts use minor zero; both have the same packed body.
        if len(found) != 1 or found[0][:2] != (12, 0):
            raise ValueError('Expected one Halo 3 mvar chunk')
    return payload(Bits(found[0][2]))


def replace_variant(source, variant):
    writer = Writer()
    payload(writer, variant)
    output = bytearray()
    count = 0
    for sig, major, minor, body in chunks(source):
        if sig == b'mvar':
            if major != 12:
                raise ValueError('Template is not an H3 layout')
            body = bytes(writer.data)
            count += 1
        elif sig == b'_eof':
            if len(body) < 5:
                raise ValueError('Malformed BLF footer')
            body = struct.pack('>I', len(output)) + body[4:]
        output.extend(struct.pack('>4sIHH', sig, 12 + len(body), major, minor))
        output.extend(body)
    if count != 1:
        raise ValueError('Expected exactly one H3 variant chunk')
    return bytes(output)
