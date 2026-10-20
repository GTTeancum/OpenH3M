"""Remove unreachable basis tags and repack their remaining local pages.

Header globals, opaque original tags, and imported metadata are reachability roots.
Tag/resource/page indices remain stable; original files are never edited.
"""
import struct
import hashlib
import zlib
import xml.etree.ElementTree as ET
import numpy as np


def compact_basis(importer):
    r, b = importer.registry, importer.builder
    c = r.cache
    schemas = {}
    ordered = sorted(t['offset'] for t in c.tags.values())
    ends = dict(zip(ordered, ordered[1:] + [c.start + c.u(0x490)]))
    originals = {(t['salt'] << 16) | i: i for i, t in c.tags.items()}
    def refs(index, live):
        tag = c.tags[index]
        # Registry owner/manifests are residency bookkeeping, not tag dependencies.
        if tag['group'] in ('zone', 'play'):
            return set()
        path = importer.reference / 'plugins' / (tag['group'].strip() + '.xml')
        if not path.exists():
            # Original tag allocations are contiguous. Scan opaque tag data for
            # exact salted handles, retaining incidental matches conservatively.
            start, end = tag['offset'], ends[tag['offset']]
            raw = c.data[start:end]
            return {originals[v[0]] for v in struct.iter_unpack('>I', raw[:len(raw) // 4 * 4]) if v[0] in originals}
        if tag['group'] not in schemas:
            schemas[tag['group']] = ET.parse(path).getroot()
        data = b.meta if live else c.data
        base = b.base if live else c.base - c.start
        address = tag['offset'] - c.start + c.base
        found, visited = set(), set()
        def word(at):
            if not 0 <= at <= len(data) - 4:
                raise ValueError('Dependency pointer outside metadata')
            return struct.unpack_from('>I', data, at)[0]
        def record(at, schema):
            key = at, id(schema)
            if key in visited:
                return
            visited.add(key)
            for field in schema:
                if 'offset' not in field.attrib:
                    continue
                pos = at + int(field.get('offset'), 0)
                kind = field.tag.lower()
                if field.get('name') == 'Simulation Definition Table':
                    continue
                if kind == 'tagblock':
                    count, pointer = word(pos), word(pos + 4)
                    stride = int(field.get('elementSize'), 0)
                    start = pointer - base
                    if count and (count > 1000000 or start < 0 or start + count * stride > len(data)):
                        raise ValueError('Dependency block outside metadata')
                    for j in range(count):
                        record(start + j * stride, field)
                elif kind in ('tagref', 'datum'):
                    value = word(pos + (12 if kind == 'tagref' and field.get('withGroup', 'true') != 'false' else 0))
                    if value in originals:
                        found.add(originals[value])
        record(address - base, schemas[tag['group']])
        return found
    # Native cache roots come from the header globals, not every historical
    # tag slot. Keep unsupported layouts as additional roots conservatively.
    candidates = set(c.tags)
    live_graph = {i: refs(i, True) for i in c.tags}
    keep = {i for i, t in c.tags.items() if not
            (importer.reference / 'plugins' / (t['group'].strip() + '.xml')).exists()}
    globals_at = c.pointer(c.u(r.index + 20))
    keep.update(c.u(globals_at + j * 8 + 4) & 65535 for j in range(c.u(r.index + 16)))
    # Newly allocated dependencies need not be contiguous with their tag roots.
    words = np.frombuffer(b.meta, dtype='>u4', count=b.used // 4)
    keep.update(originals[int(v)] for v in np.unique(words) if int(v) in originals)
    pending = list(keep)
    while pending:
        i = pending.pop()
        for j in live_graph[i] - keep:
            keep.add(j)
            pending.append(j)
    retired = candidates - keep
    dead_resources = set()
    for i in retired:
        struct.pack_into('>HHI', r.tags, i * 8, 65535, 65535, 0)
    for i in range(r.first_resource):
        owner = struct.unpack_from('>I', r.resources, i * 64 + 12)[0] & 65535
        if owner in retired or owner in getattr(r, 'superseded_resource_owners', set()):
            dead_resources.add(i)
            struct.pack_into('>h', r.resources, i * 64 + 34, -1)
    # The basis packs hundreds of textures/meshes/animations into one page.
    # Keeping the whole page for one live resource retains dead data. Repack
    # only the explicitly sized raw datarefs of these understood resource types.
    from string_ids import StringTable
    strings = StringTable(c)
    types = c.block(r.zone + 4, 28)
    type_names = [strings.text(c.u(x + 24)) for x in types]
    original_pages = c.block(r.play + 24, 88)
    raw_base = (c.u(0x484) + c.u(0x470)) & 0xffffffff
    decoded, copied = {}, {}
    fragment_count = 0
    for ri in range(r.first_resource):
        if ri in dead_resources:
            continue
        at = ri * 64
        if r.resources[at + 18] >= len(type_names):
            continue
        if type_names[r.resources[at + 18]] not in (
                'bitmap_texture_interop_resource', 'render_geometry_api_resource_definition',
                'model_animation_tag_resource'):
            continue
        li = struct.unpack_from('>h', r.resources, at + 34)[0]
        if li < 0:
            continue
        control_at, control_size = struct.unpack_from('>II', r.resources, at + 20)
        control = r.control[control_at:control_at + control_size]
        row = c.block(r.zone + 88, 64)[ri]
        ends = [0, 0]
        for fix in c.block(row + 40, 8):
            pointer, target = c.unpack('II', fix)
            segment = {0x40000000: 0, 0x60000000: 1}.get(target & 0xe0000000)
            if segment is None:
                continue
            if pointer < 12 or pointer > len(control) - 4:
                raise ValueError('Resource dataref outside control')
            size = struct.unpack_from('>I', control, pointer - 12)[0]
            ends[segment] = max(ends[segment], (target & 0x1fffffff) + size)
        for slot, size in enumerate(ends):
            pi = struct.unpack_from('>h', r.locations, li * 16 + slot * 2)[0]
            if pi < 0 or pi >= len(original_pages) or c.unpack('h', original_pages[pi] + 4)[0] != -1:
                continue
            if not size:
                struct.pack_into('>h', r.locations, li * 16 + slot * 2, -1)
                continue
            pa = original_pages[pi]
            if pi not in decoded:
                offset, compressed, expected = c.unpack('III', pa + 8)
                data = c.data[raw_base + offset:raw_base + offset + compressed]
                data = zlib.decompress(data, -15) if c.data[pa + 3] == 0 else data
                if len(data) != expected:
                    raise ValueError('Original page size mismatch')
                decoded[pi] = data
            offset = struct.unpack_from('>I', r.locations, li * 16 + 4 + slot * 4)[0]
            data = decoded[pi][offset:offset + size]
            if len(data) != size:
                raise ValueError('Live resource dataref exceeds original page')
            key = hashlib.sha256(data).digest()
            if key not in copied:
                compressed = zlib.compress(data)[2:-4]
                page = bytearray(88)
                struct.pack_into('>hBBhhIIII', page, 0, 0, 1, 0, -1, 0,
                    b.append_raw(compressed), len(compressed), len(data), zlib.crc32(data) ^ 0xffffffff)
                page[24:84] = b''.join(hashlib.sha1(r.salt + x).digest() for x in (data, data[:1024], data[-1024:]))
                struct.pack_into('>hh', page, 84, 1, -1)
                copied[key] = len(r.pages) // 88
                r.pages.extend(page)
            struct.pack_into('>h', r.locations, li * 16 + slot * 2, copied[key])
            struct.pack_into('>I', r.locations, li * 16 + 4 + slot * 4, 0)
            fragment_count += 1
    decoded.clear()
    used_pages = set()
    for i in range(len(r.resources) // 64):
        li = struct.unpack_from('>h', r.resources, i * 64 + 34)[0]
        if li >= 0:
            used_pages.update(p for p in struct.unpack_from('>hh', r.locations, li * 16) if p >= 0)
    raw_start = (c.u(0x484) + c.u(0x470)) & 0xffffffff
    original_raw = c.data[raw_start:raw_start + c.u(0x488)]
    old_raw = original_raw + b.raw
    packed = bytearray()
    dead_pages, moved = [], {}
    for i in range(len(r.pages) // 88):
        at = i * 88
        if struct.unpack_from('>h', r.pages, at + 4)[0] != -1:
            continue
        offset, size = struct.unpack_from('>II', r.pages, at + 8)
        if i not in used_pages:
            dead_pages.append(i)
            # Unreferenced slots remain inert; no stale bounds into the new file.
            struct.pack_into('>III', r.pages, at + 8, 0, 0, 0)
            continue
        key = offset, size
        if key not in moved:
            if offset + size > len(old_raw):
                raise ValueError('Live page outside source resource section')
            packed.extend(bytes((-len(packed)) % 4096))
            moved[key] = len(packed)
            packed.extend(old_raw[offset:offset + size])
        struct.pack_into('>I', r.pages, at + 8, moved[key])
    packed.extend(bytes((-len(packed)) % 4096))
    b.compacted_raw = packed
    # Remove retired residency bits from every original zone manifest.
    schema = ET.parse(importer.reference / 'plugins/zone.xml').getroot()
    for field in schema:
        if field.tag.lower() != 'tagblock' or 'Manifest' not in field.get('name', ''):
            continue
        for at in c.block(r.zone + int(field.get('offset'), 0), 120):
            for block in field:
                name = block.get('name', '')
                if block.tag.lower() != 'tagblock' or 'Bits' not in name:
                    continue
                off = int(block.get('offset'), 0)
                rows = c.block(at + off, 4)
                ids = dead_resources if 'Resource' in name else retired if 'Owner' in name else set()
                for index in ids:
                    if index // 32 < len(rows):
                        ptr = rows[index // 32] - c.start + c.base
                        value = struct.unpack('>I', b.read(ptr, 4))[0] & ~(1 << (index % 32))
                        b.put(ptr, 'I', value)
    r.retired_resources = dead_resources
    r.retired_tags = retired
    return {'retired_tags': len(retired), 'retired_resources': len(dead_resources),
            'retired_pages': len(dead_pages), 'repacked_resource_segments': fragment_count, 'bytes_saved': len(old_raw) - len(packed),
            'retired_names': [c.name(i) for i in sorted(retired)]}
