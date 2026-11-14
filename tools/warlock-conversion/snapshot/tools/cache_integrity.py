"""Native cache graph finalization, before body XOR and salted digest generation.

Page reference counts reserve native backlink array slices. They count each
required/optional serialized slot of a valid resource, including disabled optional
sound slots, not all historical location rows. Never rewrite the slot flags.
"""
import hashlib
import struct


def _metadata_layout(data):
    if (len(data) < 0x3000 or len(data) % 4 or data[:4] != b'head'
            or data[0x2ffc:0x3000] != b'foot'):
        raise ValueError('Expected complete native version-11 cache')
    u = lambda at: struct.unpack_from('>I', data, at)[0]
    if u(4) != 11 or u(8) != len(data):
        raise ValueError('Expected complete native version-11 cache')
    start = (u(0x48c) + u(0x474)) & 0xffffffff
    size = u(0x490)
    sizes = [sum(u(at) for at in (0x2f4, 0x2fc, 0x304)),
             sum(u(at) for at in (0x30c, 0x314, 0x31c))]
    if (sum(sizes) != u(0x18) or sum(sizes) != size
            or start > len(data) or start + size > len(data)
            or (size and start < 0x3000)):
        raise ValueError('Invalid metadata digest partition spans')
    return start, start + size, sizes


def page_reference_counts(resources, locations, pages):
    if len(resources) % 64 or len(locations) % 16 or len(pages) % 88:
        raise ValueError('Misaligned resource/location/page table')
    counts = [0] * (len(pages) // 88)
    enabled = [0] * len(counts)
    for at in range(0, len(resources), 64):
        salt, kind = struct.unpack_from('>HB', resources, at + 16)
        flags, location = struct.unpack_from('>Hh', resources, at + 32)
        if salt == 0xffff or kind == 0xff:
            if location != -1:
                raise ValueError('Retired resource retains a location')
            continue
        if location == -1:
            continue
        if not 0 <= location < len(locations) // 16:
            raise ValueError('Resource location outside final table')
        for slot, page in enumerate(struct.unpack_from('>hh', locations, location * 16)):
            if page == -1:
                continue
            if not 0 <= page < len(counts):
                raise ValueError('Resource page outside final table')
            counts[page] += 1
            if flags & (1 << slot):
                enabled[page] += 1
                if struct.unpack_from('>I', pages, page * 88 + 16)[0] == 0:
                    raise ValueError('Enabled native resource slot references empty page')
    if any(n > 0xffff for n in counts):
        raise ValueError('Page backlink count exceeds native 16-bit field')
    total = sum(n for i, n in enumerate(counts)
                if struct.unpack_from('>I', pages, i * 88 + 16)[0])
    if total > 0xffff:
        raise ValueError('Cumulative backlink allocation exceeds native 16-bit range')
    return counts, enabled, total


def rebuild_page_reference_counts(resources, locations, pages):
    counts, enabled, total = page_reference_counts(resources, locations, pages)
    changes = []
    for i, count in enumerate(counts):
        at = i * 88 + 84
        old = struct.unpack_from('>H', pages, at)[0]
        if old != count:
            changes.append(dict(page=i, before=old, after=count))
            struct.pack_into('>H', pages, at, count)
    return dict(changes=changes, page_records=len(counts),
                serialized_slots=sum(counts), native_enabled_slots=sum(enabled),
                nonempty_reserved_slots=total)


def refresh_cache_page_reference_counts(data):
    """Read the final serialized graph, including staged/relocated tables."""
    start, end, _ = _metadata_layout(data)
    u = lambda at: struct.unpack_from('>I', data, at)[0]
    base = u(0x2e8)
    def pointer(address, size):
        at = address - base + start
        if size < 0 or not start <= at <= end - size or end > len(data):
            raise ValueError('Final metadata pointer outside cache')
        return at
    index = pointer(u(0x10), 16)
    ng, groups, nt, tags = struct.unpack_from('>IIII', data, index)
    groups, tags = pointer(groups, ng * 16), pointer(tags, nt * 8)
    roots = {}
    for i in range(nt):
        group, _, address = struct.unpack_from('>HHI', data, tags + i * 8)
        if group == 0xffff or address in (0, 0xffffffff):
            continue
        if group >= ng:
            raise ValueError('Final tag group outside table')
        name = bytes(data[groups + group * 16:groups + group * 16 + 4])
        if name in (b'zone', b'play'):
            if name in roots:
                raise ValueError('Duplicate resource metadata root')
            roots[name] = pointer(address, 100 if name == b'zone' else 60)
    if set(roots) != {b'zone', b'play'}:
        raise ValueError('Missing final resource metadata roots')
    def table(at, stride):
        n, address = struct.unpack_from('>II', data, at)
        at = pointer(address, n * stride) if n else start
        return at, bytearray(data[at:at + n * stride])
    _, resources = table(roots[b'zone'] + 88, 64)
    _, locations = table(roots[b'play'] + 48, 16)
    at, pages = table(roots[b'play'] + 24, 88)
    result = rebuild_page_reference_counts(resources, locations, pages)
    for change in result['changes']:
        change['file_offset'] = at + change['page'] * 88 + 84
    data[at:at + len(pages)] = pages
    return result


def normalized_header(header):
    if len(header) != 0x3000:
        raise ValueError('Expected complete 12 KiB cache header')
    header = bytearray(header)
    for at, size in ((0x320, 4), (0x328, 8), (0x330, 0x13c), (0x1c, 0x100),
                     (0x144, 8), (0x16c, 0x20), (0x49c, 0x10)):
        header[at:at + size] = bytes(size)
    return header


def refresh_cache_hashes(data, salt):
    """Refresh body XOR then ALL three salted digests, never claim RSA signing."""
    import numpy as np
    if len(salt) != 34:
        raise ValueError('Invalid native resource hash salt')
    start, _, sizes = _metadata_layout(data)
    checksum = int(np.bitwise_xor.reduce(
        np.frombuffer(data, dtype='>u4', offset=0x3000), initial=0))
    struct.pack_into('>I', data, 0x2c4, checksum)
    hashes = [hashlib.sha1(salt + normalized_header(data[:0x3000])).digest()]
    resources_only = struct.unpack_from('>h', data, 0x13c)[0] == 3 and sizes == [0, 0]
    for size in sizes:
        digest = hashlib.sha1(salt)
        digest.update(memoryview(data)[start:start + size])
        hashes.append(bytes(20) if resources_only else digest.digest())
        start += size
    data[0x330:0x36c] = b''.join(hashes)
    return dict(body_xor=f'{checksum:08x}', salted_hashes=[h.hex() for h in hashes],
                recomputed_triplet_digest=hashlib.sha1(salt + b''.join(hashes)).hexdigest(),
                metadata_partition_bytes=sizes, rsa_signature='unchanged; NOT re-signed')


def finalize_cache(data, salt):
    """Finalize a scenario cache only after ALL metadata/header edits are done.

    Recount the serialized resource graph first: those count edits belong in
    the body checksum and metadata digests too. RSA signature bytes are retained,
    not regenerated; this does not make a custom cache retail-authenticated.
    """
    if len(salt) != 34:
        raise ValueError('Invalid native resource hash salt')
    counts = refresh_cache_page_reference_counts(data)
    integrity = refresh_cache_hashes(data, salt)
    return dict(reference_counts=counts, integrity=integrity)
