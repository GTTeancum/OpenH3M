"""Reuse retail sound tables and bitmap resources, preserving native XMA packets."""
import struct
import hashlib
import zlib
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable
from tag_metadata import MetadataConverter


class NativeSounds:
    def __init__(self, sounds, disc_maps):
        self.sounds = sounds
        self.paths = {}
        self.item_ui = {}
        self.bitmaps = {}
        self.bitmap_resolved = {}
        self.page_cache = {}
        self.trimmed = {}
        for path in sorted(Path(disc_maps).glob('*.map')):
            if path.name in ('shared.map', 'campaign.map'):
                continue
            c = Cache(path)
            try:
                zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
                resources = c.block(zone + 88, 64)
                for i, t in c.tags.items():
                    if t['group'] in ('weap', 'eqip'):
                        self.item_ui.setdefault((t['group'], c.name(i)),
                                                (c.unpack('2h', t['offset'] + 0xfc), path.name))
                    if t['group'] == 'bitm':
                        ids = [c.u(x) for x in c.block(t['offset'] + 0x8c, 8)]
                        if ids and all(v != 0xffffffff and (v & 65535) < len(resources) and c.unpack('H', resources[v & 65535] + 16)[0] == v >> 16 for v in ids):
                            self.bitmaps.setdefault(c.name(i), (path, i))
                    if t['group'] == 'snd!':
                        resource = c.u(t['offset'] + 24)
                        # Some maps retain sound tags whose resource rows
                        # were stripped. Continue searching other disc maps.
                        if (resource != 0xffffffff and (resource & 65535) < len(resources)
                                and c.unpack('H', resources[resource & 65535] + 16)[0] == resource >> 16):
                            self.paths.setdefault(c.name(i), (path, i))
            finally:
                c.close()

    def bitmap(self, name):
        if name not in self.bitmaps:
            return None
        from native_shaders import NativeShaderImporter
        path, index = self.bitmaps[name]
        c = Cache(path)
        try:
            native = NativeShaderImporter(c, self.sounds.importer, self.bitmap_resolved)
            native.resource_copier = lambda datum, owner: self.resource(c, datum, owner, trim_bitmap=True)
            result = native.import_tag((c.tags[index]['salt'] << 16) | index)[1]
            if result in self.trimmed:
                b = self.sounds.builder
                address = struct.unpack_from('>I', self.sounds.registry.tags, (result & 65535) * 8 + 4)[0]
                count, pointer = struct.unpack('>II', b.read(address + 96, 8))
                if count != 1:
                    raise ValueError('Native mip trim requires one bitmap image')
                width, height, levels, size = self.trimmed[result]
                b.put(pointer + 4, 'HH', width, height)
                b.meta[pointer - b.base + 9] &= ~0x20
                b.meta[pointer - b.base + 20] = levels - 1
                b.put(pointer + 28, 'III', size, 0, 0)
            self.sounds.importer.materials.report.append({'source': name,
                'native_bitmap_donor': path.name, 'retained_native_mips': True, 'dropped_highest_mip': result in self.trimmed})
            return result
        finally:
            c.close()

    def resource(self, c, datum, owner, trim_bitmap=False):
        r = self.sounds.registry
        zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
        play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
        at = c.block(zone + 88, 64)[datum & 65535]
        row = bytearray(c.data[at:at + 64])
        if c.unpack('H', at + 16)[0] != datum >> 16:
            raise ValueError(f'Native resource salt mismatch {c.file.name} {datum:#x} row={c.unpack(chr(72), at + 16)[0]:#x}')
        types = c.block(zone + 4, 28)
        type_name = StringTable(c).text(c.u(types[row[18]] + 24))
        if type_name not in ('sound_resource_definition', 'bitmap_texture_interop_resource'):
            raise ValueError('Expected a native sound or bitmap resource')
        control_size = c.u(at + 24)
        control = b''
        trimmed = False
        if control_size:
            control_field = zone + (r.control_field - r.zone)
            control_start = c.pointer(c.u(control_field + 12)) + c.u(at + 20)
            control = bytearray(c.data[control_start:control_start + control_size])
            if trim_bitmap and type_name == 'bitmap_texture_interop_resource' and len(control) == 64:
                width, height, depth, levels, kind, high = struct.unpack_from('>HHBBBB', control, 40)
                if kind == 0 and depth == 1 and max(width, height) > 512 and high == 1 and struct.unpack_from('>I', control, 20)[0]:
                    width, height, levels = max(1, width // 2), max(1, height // 2), levels - 1
                    struct.pack_into('>HHBBBB', control, 40, width, height, depth, levels, kind, 0)
                    control[20:40] = bytes(20)
                    self.trimmed[owner] = (width, height, levels, struct.unpack_from('>I', control)[0])
                    trimmed = True
            struct.pack_into('>I', row, 20, len(r.control))
            r.control.extend(control)
        li = c.unpack('h', at + 34)[0]
        location = bytearray(c.data[c.block(play + 48, 16)[li]:][:16])
        if trimmed:
            struct.pack_into('>h', location, 2, -1)
            struct.pack_into('>I', location, 8, 0)
            struct.pack_into('>h', location, 14, -1)
        source_files = c.block(play + 12, 264)
        target_files = r.cache.block(r.play + 12, 264)
        names = [r.cache.data[x:x + 256].split(b'\0')[0] for x in target_files]
        pages = c.block(play + 24, 88)
        streaming = c.block(play + 36, 16)
        lengths = []
        for slot, si in enumerate(struct.unpack_from('>hh', location, 12)):
            if si < 0:
                if type_name == 'sound_resource_definition':
                    raise ValueError('Native sound missing streaming sublocations')
                lengths.append(struct.unpack_from('>I', control, slot * 20)[0])
                continue
            sa = streaming[si]
            rows = c.block(sa + 4, 8)
            payload = b''.join(c.data[x:x + 8] for x in rows)
            lengths.append(sum(c.u(x + 4) for x in rows))
            target_si = len(r.streaming) // 16
            r.streaming.extend(struct.pack('>IIII', c.u(sa), len(rows),
                r.builder.alloc(payload) if payload else 0, 0))
            struct.pack_into('>h', location, 12 + slot * 2, target_si)
        for slot, pi in enumerate(struct.unpack_from('>hh', location)):
            if pi < 0:
                continue
            page = bytearray(c.data[pages[pi]:pages[pi] + 88])
            shared = struct.unpack_from('>h', page, 4)[0]
            if shared >= 0:
                name = c.data[source_files[shared]:source_files[shared] + 256].split(b'\0')[0]
                if name not in names:
                    raise ValueError('Native shared resource file absent from target')
                struct.pack_into('>h', page, 4, names.index(name))
                # The stock maps share the same authenticated page descriptors.
                key = ('shared', bytes(page))
            else:
                key = (str(c.file.name), pi, struct.unpack_from('>I', location, 4 + slot * 4)[0], lengths[slot])
            if key not in self.page_cache:
                existing = next((j for j in range(len(r.pages) // 88)
                                 if r.pages[j * 88:(j + 1) * 88] == page), None) if shared >= 0 else None
                if existing is None:
                    if shared == -1:
                        block, size = struct.unpack_from('>II', page, 8)
                        start = ((c.u(0x484) + c.u(0x470)) & 0xffffffff) + block
                        payload = c.data[start:start + size]
                        if len(payload) != size:
                            raise ValueError('Truncated native resource page')
                        raw = zlib.decompress(payload, -15) if page[3] == 0 else payload
                        offset = struct.unpack_from('>I', location, 4 + slot * 4)[0]
                        raw = raw[offset:offset + lengths[slot]]
                        if len(raw) != lengths[slot]:
                            raise ValueError('Native sound segment exceeds page')
                        # Retail XMA streaming reads packet pages directly. Keep
                        # the original uncompressed page codec for native audio.
                        codec = 255 if type_name == 'sound_resource_definition' else 0
                        compressed = raw if codec == 255 else zlib.compress(raw)[2:-4]
                        page = bytearray(88)
                        struct.pack_into('>hBBhhIIII', page, 0, 0, 1, codec, -1, 0,
                            r.builder.append_raw(compressed), len(compressed), len(raw), zlib.crc32(raw) ^ 0xffffffff)
                        page[24:84] = b''.join(hashlib.sha1(r.salt + x).digest() for x in (raw, raw[:1024], raw[-1024:]))
                        struct.pack_into('>hh', page, 84, 1, -1)
                    existing = len(r.pages) // 88
                    r.pages.extend(page)
                self.page_cache[key] = existing
            struct.pack_into('>h', location, slot * 2, self.page_cache[key])
            if shared == -1:
                struct.pack_into('>I', location, 4 + slot * 4, 0)
        rid = len(r.resources) // 64
        struct.pack_into('>I', row, 12, owner)
        struct.pack_into('>H', row, 16, 0x9100)
        row[18] = r.types[type_name]
        struct.pack_into('>h', row, 34, len(r.locations) // 16)
        for field in (40, 52):
            pairs = c.block(at + field, 8)
            if trimmed and field == 40:
                pairs = [x for x in pairs if c.u(x) != 32]
            data = b''.join(c.data[x:x + 8] for x in pairs)
            struct.pack_into('>III', row, field, len(pairs), r.builder.alloc(data) if data else 0, 0)
        r.added_bytes += sum(lengths)
        r.locations.extend(location)
        r.resources.extend(row)
        return 0x91000000 | rid

    def import_sound(self, name):
        if name not in self.paths:
            return None
        path, index = self.paths[name]
        c = Cache(path)
        try:
            return self.convert(c, index, name, path.name)
        finally:
            c.close()

    def convert(self, c, index, name, filename):
        s = self.sounds
        at = c.tags[index]['offset']
        flags, category, count, codec, first, language, priority, playback, scale, promotion, custom, extra, duration, resource, padding = c.unpack('HBB6hbbhIII', at)
        root = next(t['offset'] for t in c.tags.values() if t['group'] == 'ugh!')
        def row(table, index):
            field = s.field(s.ds, table)
            return c.block(root + int(field.get('offset'), 0), int(field.get('elementSize'), 0))[index]
        if language != -1 or custom != -1 or (extra != -1 and c.u(row('Extra Info', extra))):
            raise ValueError('Unsupported native sound auxiliary table: ' + name)
        conv = MetadataConverter(c, s.builder, StringTable(c), s.importer.target_strings,
                                 lambda datum: (_ for _ in ()).throw(ValueError('Unexpected native sound tag dependency')))
        def copy(table, index):
            if index == -1:
                return -1
            field = s.field(s.ds, table)
            data = conv.convert(row(table, index), field, field, 'ugh!/' + table)
            try:
                return s.tables[table].index(data)
            except ValueError:
                return s.append(table, data)
        if promotion != -1:
            for rule in c.block(row('Promotions', promotion), 16):
                if not 0 <= c.unpack('h', rule)[0] < count:
                    raise ValueError('Native promotion uses a nonlocal pitch index')
        owner, address = s.registry.newtag('snd!', bytes(32))
        target_first = len(s.tables['Pitch Ranges'])
        for pitch in range(first, first + count):
            pn, parameters, encoded, runtime, packed = c.unpack('4hI', row('Pitch Ranges', pitch))
            pc, pf = (packed >> 20) & 63, packed & 65535
            fixed = encoded == 0 and runtime == -1 and pc == 1
            if not pc or (encoded != -1 and not fixed):
                raise ValueError('Unsupported native pitch encoding')
            target_perm = len(s.tables['Permutations'])
            bit = -1 if fixed else len(s.tables['Runtime Permutation Flags']) * 8
            if bit > 32767 or target_perm + pc > 65535:
                raise ValueError('Native sound table index exhausted')
            for _ in range(0 if fixed else (pc + 7) // 8):
                s.append('Runtime Permutation Flags', b'\0')
            for perm in range(pf, pf + pc):
                imp, skip, frames, chunk, chunks, gain, info = c.unpack('hhIIhbb', row('Permutations', perm))
                target_chunk = len(s.tables['Chunks'])
                for ci in range(chunk, chunk + chunks):
                    ca = row('Chunks', ci)
                    s.append('Chunks', bytes(c.data[ca:ca + 20]))
                s.append('Permutations', struct.pack('>hhIIhbb', copy('Import Names', imp), skip,
                    frames, target_chunk, chunks, gain, info))
            s.append('Pitch Ranges', struct.pack('>4h2H', copy('Import Names', pn),
                copy('Pitch Range Parameters', parameters), encoded, bit, packed >> 16, target_perm))
        res = self.resource(c, resource, owner)
        data = struct.pack('>HBB6hbbhIII', flags, category, count, copy('Codecs', codec), target_first,
            -1, priority, copy('Playbacks', playback), copy('Scales', scale), copy('Promotions', promotion), -1, copy('Extra Info', extra), duration, res, padding)
        off = address - s.builder.base
        s.builder.meta[off:off + 32] = data
        s.report.append({'source': name, 'datum': hex(owner), 'encoding': 'native retail', 'donor': filename})
        return 'snd!', owner

