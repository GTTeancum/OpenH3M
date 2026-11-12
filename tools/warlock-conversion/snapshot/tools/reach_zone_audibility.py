"""Translate matching Reach/H3 zone-audibility records and split cluster lookup.

Both schemas use 100-byte records. Splitting a geometry cluster does not create
an acoustic room: both children retain the authored room index. Encoded room
payloads remain unchanged; runtime acoustic validation is still required.
"""
import math
import struct


def install_zone_audibility(source, source_scenario, builder, scenario, counts, split):
    records = bytearray()
    reports = []
    for at in source.block(source_scenario + 0xa0, 100):
        doors, rooms, low, high = source.unpack('ii2f', at)
        if doors != 0:
            raise ValueError('Door audibility conversion needs explicit portal remapping')
        if rooms <= 0 or not all(math.isfinite(x) for x in (low, high)) or low > high:
            raise ValueError('Invalid audibility room header')
        specs = [(16, 'I', 4), (28, 'I', 4), (40, 'I', 4), (52, 'B', 1),
                 (64, 'ii', 8), (76, 'ii', 8), (88, 'h', 2)]
        arrays = {off: [source.unpack(fmt, p) for p in source.block(at + off, size)]
                  for off, fmt, size in specs}
        if arrays[16] or arrays[28] or any(v != (0, 0) for v in arrays[64]):
            raise ValueError('Unexpected door data in doorless zone')
        if len(arrays[64]) != len(counts) or len(arrays[76]) != len(counts):
            raise ValueError('Audibility BSP coverage mismatch')
        if len(arrays[52]) != rooms * (rooms - 1) // 2:
            raise ValueError('Unknown room-distance encoding shape')
        old_indices = arrays[88]
        rebuilt = []
        bounds = []
        consumed = []
        for bi, ((start, count), expected) in enumerate(zip(arrays[76], counts)):
            if count != expected or start < 0 or start + count > len(old_indices):
                raise ValueError('Cluster-room bounds do not match source geometry')
            indices = old_indices[start:start + count]
            if any(not -1 <= v[0] < rooms for v in indices):
                raise ValueError('Cluster references invalid acoustic room')
            consumed.extend(range(start, start + count))
            if bi == split['bsp']:
                indices = indices + [indices[split['source_cluster']]]
            bounds.append((len(rebuilt), len(indices)))
            rebuilt.extend(indices)
        if sorted(consumed) != list(range(len(old_indices))):
            raise ValueError('Overlapping or unused source cluster-room indices')
        arrays[76], arrays[88] = bounds, rebuilt
        record = bytearray(struct.pack('>ii2f', doors, rooms, low, high))
        for off, fmt, size in specs:
            data = b''.join(struct.pack('>' + fmt, *v) for v in arrays[off])
            ptr = builder.alloc(data) if data else 0
            record.extend(struct.pack('>III', len(arrays[off]), ptr, 0))
            if data and builder.read(ptr, len(data)) != data:
                raise ValueError('Audibility payload readback failed')
        assert len(record) == 100
        records.extend(record)
        reports.append(dict(rooms=rooms, cluster_room_bounds=bounds,
            cluster_room_indices=[x[0] for x in rebuilt],
            room_distance_bytes=len(arrays[52]), child_inherits_parent_room=True,
            encoded_room_payloads_preserved=True, runtime_verified=False))
    pointer = builder.alloc(records) if records else 0
    builder.put(scenario + 0x48, 'III', len(reports), pointer, 0)
    if records and builder.read(pointer, len(records)) != records:
        raise ValueError('Audibility root readback failed')
    return dict(zones=reports, records_read_back=True, runtime_verified=False)
