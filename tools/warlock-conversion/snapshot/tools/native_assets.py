"""Relocate stock Halo 3 assets without changing native payloads or behavior."""
from pathlib import Path
import struct
import hashlib
import zlib
from collections import OrderedDict
import xml.etree.ElementTree as ET

from cache_reader import Cache
from string_ids import StringTable
from native_shaders import NativeShaderImporter


class NativeAssets:
    def __init__(self, importer, disc_maps):
        self.i = importer
        self.paths = {}
        self.schemas = {}
        self.candidates = {}
        self.eligibility = {}
        self.string_tables = {}
        self.pages = {}
        self.resources = {}
        self.decoded_pages = OrderedDict()
        # Prefer the complete multiplayer palettes before campaign/menu donors.
        paths = sorted(Path(disc_maps).glob('*.map'),
                       key=lambda p: (0 if p.stem == 'shrine' else 1 if p.stem == 'sandbox' else 2, p.name))
        for path in paths:
            if path.stem in ('shared', 'mainmenu', 'campaign'):
                continue
            c = Cache(path)
            try:
                for index, tag in c.tags.items():
                    name = c.name(index)
                    if name:
                        self.paths.setdefault((tag['group'], name), (path, index))
                        self.candidates.setdefault((tag['group'], name), []).append((path, index))
            finally:
                c.close()

    def import_named(self, key, force=False):
        # Explicitly approved stock equivalents: source wrapper names/types are
        # not proof that the object needs MCC gameplay data.
        aliases = {
            ('bloc', r'objects\levels\dlc\shared\soccer_ball\soccer_ball'):
                ('vehi', r'objects\levels\dlc\shared\soccer_ball\soccer_ball', None),
            ('vehi', r'objects\vehicles\warthog\warthog_troop'):
                ('vehi', r'objects\vehicles\warthog\warthog', 'troop'),
            ('vehi', r'objects\vehicles\warthog\warthog_wrecked_turret'):
                ('vehi', r'objects\vehicles\warthog\warthog', 'wrecked_turret'),
            ('vehi', r'objects\vehicles\wraith\wraith_anti_air'):
                ('vehi', r'objects\vehicles\wraith\wraith', 'anti_air'),
        }
        if key in aliases:
            if key in self.i.resolved:
                return self.i.resolved[key]
            group, name, variant = aliases[key]
            result = self.import_named((group, name))
            if result is None:
                raise ValueError('Required stock equivalent is absent: ' + name)
            if variant:
                i, b, r = self.i, self.i.builder, self.i.registry
                address = struct.unpack_from('>I', r.tags, (result[1] & 65535) * 8 + 4)[0]
                schema = ET.parse(i.reference / 'plugins/vehi.xml').getroot()
                payload = bytearray(b.read(address, int(schema.get('baseSize'), 0)))
                # Native model variants select native child turrets/attachments.
                # Preserve the complete stock root, seats, weapons and damage data.
                struct.pack_into('>I', payload, 0x30, i.target_strings.id_for_text(variant))
                owner, _ = r.newtag(group, payload)
                result = group, owner
            self.i.resolved[key] = result
            self.i.added.append({
                'source': key[1], 'source_group': key[0], 'group': result[0],
                'datum': hex(result[1]), 'stock_equivalent': name,
                'stock_variant': variant,
            })
            return result
        if key not in self.paths:
            return None
        if not force and key in self.i.resolved:
            return self.i.resolved[key]
        path, index = self.paths[key]
        c = Cache(path)
        try:
            return self.import_from(c, (c.tags[index]['salt'] << 16) | index, force)
        finally:
            c.close()

    def import_from(self, c, datum, force=False):
        i, b, r = self.i, self.i.builder, self.i.registry
        tag = c.tags.get(datum & 65535)
        if tag is None or tag['salt'] != datum >> 16:
            raise ValueError(f'Invalid native dependency {datum:#x}')
        group, name = tag['group'], c.name(datum & 65535)
        key = group, name
        if not force and key in i.resolved:
            return i.resolved[key]
        if group == 'snd!':
            result = i.sounds.native.import_sound(name)
            if result is None:
                source_tag = next(((n, t) for n, t in i.source.tags.items()
                                   if t['group'] == 'snd!' and i.source.name(n) == name), None)
                if source_tag is None:
                    raise ValueError('Native sound data absent from every disc donor: ' + str(name))
                n, t = source_tag
                result = i.sounds.import_sound(t['salt'] << 16 | n)
            i.resolved[key] = result
            return result
        schema_path = i.reference / 'plugins' / (group.strip() + '.xml')
        if not schema_path.is_file():
            raise ValueError(f'Native asset schema missing: {group}:{name}')
        if group not in self.schemas:
            self.schemas[group] = ET.parse(schema_path).getroot()
        schema = self.schemas[group]
        validity_key = str(c.file.name), datum
        if validity_key not in self.eligibility:
            zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
            resources = c.block(zone + 88, 64)
            def valid_resources(at, node):
                for field in node:
                    if 'offset' not in field.attrib:
                        continue
                    pos = at + int(field.get('offset'), 0)
                    if field.tag.lower() == 'tagblock':
                        if any(not valid_resources(row, field) for row in c.block(pos, int(field.get('elementSize'), 0))):
                            return False
                    elif field.tag.lower() == 'datum' and '[zone]' in field.get('name', ''):
                        value = c.u(pos)
                        if value != 0xffffffff and ((value & 65535) >= len(resources)
                            or c.unpack('H', resources[value & 65535] + 16)[0] != value >> 16
                            or c.u(resources[value & 65535] + 24) == 0):
                            return False
                return True
            self.eligibility[validity_key] = valid_resources(tag['offset'], schema)
        if not self.eligibility[validity_key]:
            for path, index in self.candidates.get(key, []):
                donor = Cache(path)
                try:
                    other = donor.tags[index]['salt'] << 16 | index
                    other_key = str(donor.file.name), other
                    if other_key == validity_key or self.eligibility.get(other_key) is False:
                        continue
                    return self.import_from(donor, other, force)
                finally:
                    donor.close()
            raise ValueError(f'No intact native resource donor for {group}:{name}')
        size = int(schema.get('baseSize'), 0)
        owner, address = r.newtag(group, bytes(size))
        i.resolved[key] = group, owner
        if str(c.file.name) not in self.string_tables:
            self.string_tables[str(c.file.name)] = StringTable(c)
        strings = self.string_tables[str(c.file.name)]
        shaders = None

        def record(at, node, length, label, depth=0):
            if depth > 32 or at < 0 or at + length > len(c.data):
                raise ValueError(f'Invalid native metadata bounds: {label}')
            # Preserve every scalar, unknown and padding byte. Only serialized
            # addresses, handles and string IDs need relocation.
            nonlocal shaders
            out = bytearray(c.data[at:at + length])
            for field in node:
                if 'offset' not in field.attrib:
                    continue
                offset = int(field.get('offset'), 0)
                kind = field.tag.lower()
                pos = at + offset
                field_name = field.get('name', '')
                if kind == 'tagblock':
                    stride = int(field.get('elementSize'), 0)
                    rows = c.block(pos, stride)
                    data = [record(row, field, stride, label + '/' + field_name, depth + 1)
                            for row in rows]
                    # Animation lookup tables are keyed by translated IDs.
                    # Other blocks retain their index-addressed native order.
                    if group == 'jmad' and field.get('sort') == 'true':
                        data.sort(key=lambda row: struct.unpack_from('>I', row)[0])
                    payload = b''.join(data)
                    struct.pack_into('>III', out, offset, len(rows), b.alloc(payload) if payload else 0, 0)
                elif kind == 'tagref':
                    handle_offset = 0 if field.get('withGroup') == 'false' else 12
                    ref = c.u(pos + handle_offset)
                    if ref != 0xffffffff:
                        target_group, target = self.import_from(c, ref)
                        if handle_offset:
                            out[offset:offset + 4] = target_group.encode('ascii')
                            out[offset + 4:offset + 12] = bytes(8)
                        struct.pack_into('>I', out, offset + handle_offset, target)
                elif kind == 'stringid':
                    struct.pack_into('>I', out, offset, strings.translate(c.u(pos), i.target_strings))
                elif kind == 'datum' and c.u(pos) != 0xffffffff:
                    if '[zone]' not in field_name:
                        raise ValueError(f'Unclassified native datum: {label}/{field_name}')
                    struct.pack_into('>I', out, offset, self.resource(c, c.u(pos), owner, strings))
                elif kind == 'dataref':
                    count = c.u(pos)
                    if count:
                        start = c.pointer(c.u(pos + 12))
                        if start + count > len(c.data):
                            raise ValueError('Native data reference exceeds cache')
                        struct.pack_into('>I', out, offset + 12, b.alloc(c.data[start:start + count]))
                elif kind == 'shader':
                    if shaders is None:
                        shaders = NativeShaderImporter(c, i)
                    struct.pack_into('>I', out, offset,
                                     shaders.shader_pointer(c.u(pos), field.get('type')))
            return bytes(out)

        payload = record(tag['offset'], schema, size, group + ':' + str(name))
        b.meta[address - b.base:address - b.base + size] = payload
        i.added.append({'source': name, 'group': group, 'datum': hex(owner),
                        'native_asset_donor': Path(c.file.name).name})
        return group, owner

    def resource(self, c, datum, owner, strings):
        r, b = self.i.registry, self.i.builder
        key = str(c.file.name), datum, owner
        if key in self.resources:
            return self.resources[key]
        zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
        play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
        at = c.block(zone + 88, 64)[datum & 65535]
        row = bytearray(c.data[at:at + 64])
        if c.unpack('H', at + 16)[0] != datum >> 16 or not c.u(at + 24):
            raise ValueError(f'Stripped/invalid native resource: {c.file.name} {datum:#x}')
        types = c.block(zone + 4, 28)
        type_name = strings.text(c.u(types[row[18]] + 24))
        control_field = zone + r.control_field - r.zone
        start = c.pointer(c.u(control_field + 12)) + c.u(at + 20)
        control = bytearray(c.data[start:start + c.u(at + 24)])
        fixups = [c.unpack('II', x) for x in c.block(at + 40, 8)]
        if type_name == 'model_animation_tag_resource':
            root = c.u(at + 36) & 0x1fffffff
            count = struct.unpack_from('>I', control, root)[0]
            table = dict(fixups)[root + 4] & 0x1fffffff if count else 0
            for n in range(count):
                pos = table + n * 48
                value = struct.unpack_from('>I', control, pos)[0]
                struct.pack_into('>I', control, pos, strings.translate(value, self.i.target_strings))
        struct.pack_into('>I', row, 20, len(r.control))
        r.control.extend(control)
        li = c.unpack('h', at + 34)[0]
        if li < 0:
            raise ValueError('Native resource lacks a location')
        location_at = c.block(play + 48, 16)[li]
        location = bytearray(c.data[location_at:location_at + 16])
        source_streaming = c.block(play + 36, 16)
        for slot, index in enumerate(struct.unpack_from('>hh', location, 12)):
            if index >= 0:
                sa = source_streaming[index]
                rows = c.block(sa + 4, 8)
                payload = b''.join(c.data[x:x + 8] for x in rows)
                struct.pack_into('>h', location, 12 + slot * 2, len(r.streaming) // 16)
                r.streaming.extend(struct.pack('>IIII', c.u(sa), len(rows),
                                                b.alloc(payload) if payload else 0, 0))
        source_pages = c.block(play + 24, 88)
        source_files = c.block(play + 12, 264)
        target_names = [r.cache.data[x:x + 256].split(b'\0')[0]
                        for x in r.cache.block(r.play + 12, 264)]
        ends = [0, 0]
        for pointer, target in fixups:
            segment = {0x40000000: 0, 0x60000000: 1}.get(target & 0xe0000000)
            if segment is not None:
                if pointer < 12 or pointer > len(control) - 4:
                    raise ValueError('Native resource dataref outside control')
                size = struct.unpack_from('>I', control, pointer - 12)[0]
                ends[segment] = max(ends[segment], (target & 0x1fffffff) + size)
        for slot, index in enumerate(struct.unpack_from('>hh', location)):
            if index < 0:
                continue
            page = bytearray(c.data[source_pages[index]:source_pages[index] + 88])
            shared = struct.unpack_from('>h', page, 4)[0]
            if shared >= 0:
                name = c.data[source_files[shared]:source_files[shared] + 256].split(b'\0')[0]
                if name not in target_names:
                    raise ValueError(f'Native shared cache not available: {name}')
                struct.pack_into('>h', page, 4, target_names.index(name))
                page_key = ('shared', bytes(page))
            else:
                size = ends[slot]
                if not size:
                    struct.pack_into('>h', location, slot * 2, -1)
                    continue
                decode_key = str(c.file.name), index
                if decode_key not in self.decoded_pages:
                    block, length, expected = struct.unpack_from('>III', page, 8)
                    start = ((c.u(0x484) + c.u(0x470)) & 0xffffffff) + block
                    encoded = c.data[start:start + length]
                    decoded = zlib.decompress(encoded, -15) if page[3] == 0 else encoded
                    if len(decoded) != expected:
                        raise ValueError('Native page decompressed size mismatch')
                    self.decoded_pages[decode_key] = decoded
                    while len(self.decoded_pages) > 4:
                        self.decoded_pages.popitem(last=False)
                decoded = self.decoded_pages[decode_key]
                offset = struct.unpack_from('>I', location, 4 + slot * 4)[0]
                segment = decoded[offset:offset + size]
                if len(segment) != size:
                    raise ValueError('Native segment exceeds donor page')
                page_key = ('local', hashlib.sha256(segment).digest())
                struct.pack_into('>I', location, 4 + slot * 4, 0)
            if page_key not in self.pages:
                existing = next((n for n in range(len(r.pages) // 88)
                                 if r.pages[n * 88:(n + 1) * 88] == page), None) if shared >= 0 else None
                if existing is None:
                    if shared < 0:
                        encoded = zlib.compress(segment)[2:-4]
                        page = bytearray(88)
                        struct.pack_into('>hBBhhIIII', page, 0, 0, 1, 0, -1, 0,
                                         b.append_raw(encoded), len(encoded), len(segment),
                                         zlib.crc32(segment) ^ 0xffffffff)
                        page[24:84] = b''.join(hashlib.sha1(r.salt + part).digest()
                                               for part in (segment, segment[:1024], segment[-1024:]))
                        struct.pack_into('>hh', page, 84, 1, -1)
                    existing = len(r.pages) // 88
                    r.pages.extend(page)
                self.pages[page_key] = existing
            struct.pack_into('>h', location, slot * 2, self.pages[page_key])
        rid = len(r.resources) // 64
        struct.pack_into('>I', row, 12, owner)
        struct.pack_into('>H', row, 16, 0x9100)
        row[18] = r.types[type_name]
        struct.pack_into('>h', row, 34, len(r.locations) // 16)
        for field in (40, 52):
            pairs = c.block(at + field, 8)
            payload = b''.join(c.data[x:x + 8] for x in pairs)
            struct.pack_into('>III', row, field, len(pairs), b.alloc(payload) if payload else 0, 0)
        r.locations.extend(location)
        r.resources.extend(row)
        self.resources[key] = 0x91000000 | rid
        return self.resources[key]
