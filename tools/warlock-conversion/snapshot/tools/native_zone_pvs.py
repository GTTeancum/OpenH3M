"""Original H3 zone PVS writer. Input must already use native semantics.

Layouts: stock disc scenario records (44-byte zone, 84-byte BSP), checked
against TagTool Scenario.ZoneSetPvsBlock. Version is the full native word 8.
Reach's three lists of two-byte cluster references must be translated by the
caller; this writer deliberately does not flatten them or discard BSP indices.
"""
import struct


def serialize_zone(zone, allocate):
    from reach_pvs_split import serialize_matrix

    if zone['version_word'] != 8:
        raise ValueError('Expected original H3 PVS version word 8')
    bsps = zone['bsps']
    if zone['mask'].bit_count() != len(bsps):
        raise ValueError('BSP mask/count mismatch')
    if len(zone['checksums']) != len(bsps):
        raise ValueError('BSP checksum/count mismatch')
    if any('seam_mappings' in b for b in bsps):
        raise ValueError('Reach cluster mappings require explicit native translation')
    counts = [len(b['open']) for b in bsps]

    def block(data, count):
        return struct.pack('>III', count, allocate(data) if data else 0, 0)

    def words(values):
        return block(b''.join(struct.pack('>I', v) for v in values), len(values))

    records = bytearray()
    for bi, b in enumerate(bsps):
        n = counts[bi]
        for key in ('open', 'closed'):
            if len(b[key]) != n:
                raise ValueError('Visibility row count mismatch')
            for row in b[key]:
                if len(row) != len(bsps):
                    raise ValueError('Visibility BSP vector count mismatch')
                if any(len(v) != (count + 31) // 32 for v, count in zip(row, counts)):
                    raise ValueError('Visibility target vector width mismatch')
            records.extend(block(serialize_matrix(b[key], allocate), n))
        for key in ('attached_skies', 'visible_skies'):
            if len(b[key]) != n:
                raise ValueError('Sky row count mismatch')
            records.extend(block(struct.pack('>' + str(n) + 'b', *b[key]), n))
        for key in ('multiple_skies', 'audio'):
            values = b[key]
            if len(values) not in (0, (n + 31) // 32):
                raise ValueError('Cluster bitvector width mismatch')
            records.extend(words(values))
        mappings = b['native_cluster_mappings']
        if len(mappings) != n:
            raise ValueError('Native cluster mapping row count mismatch')
        # Native sub_82165140 returns this list; both callers use lbzx and
        # retain the observer BSP byte (sub_82164B70/sub_822C5A50). These
        # are unsigned local cluster indices, not cross-BSP seam references.
        # Native scnr schema names this Cluster Audio Cluster Neighbors;
        # Reach root/attached/connected lists are not interchangeable.
        if n>255 or any(not 0<=v<n for row in mappings for v in row):
            raise ValueError('Native cluster mapping outside local BSP cluster range')
        refs = b''.join(block(struct.pack('>' + str(len(row)) + 'B', *row), len(row))
                        for row in mappings)
        records.extend(block(refs, len(mappings)))
    # Reflection has no device portals. Nonempty associations need their own
    # conversion, rather than treating Reach's 36-byte row as a native 24-byte row.
    portals = zone['portal_device_counts']
    if any(row != [0, 0] for row in portals):
        raise ValueError('Device portal conversion not implemented')
    return (struct.pack('>II', zone['mask'], 8) + words(zone['checksums'])
            + block(records, len(bsps)) + block(bytes(24 * len(portals)), len(portals)))
