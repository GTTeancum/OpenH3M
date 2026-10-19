"""Stage new retail tag/resource tables and explicit BSP residency manifests."""
import hashlib
import struct
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from string_ids import StringTable


class CacheRegistry:
    def __init__(self, builder, salt):
        if len(salt) != 34:
            raise ValueError('Expected the retail 34-byte resource hash salt')
        self.builder, self.cache, self.salt = builder, builder.cache, salt
        c = self.cache
        self.zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
        self.play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
        self.index = c.pointer(c.u(16))
        self.first_tag = c.u(self.index + 8)
        at = c.pointer(c.u(self.index + 12))
        self.tags = bytearray(c.data[at:at + self.first_tag * 8])
        self.resources = self.table(self.zone + 0x58, 64)
        self.first_resource = len(self.resources) // 64
        self.pages = self.table(self.play + 0x18, 88)
        self.locations = self.table(self.play + 0x30, 16)
        self.streaming = self.table(self.play + 0x24, 16)
        schema = ET.parse(Path(__file__).resolve().parents[1] / 'reference/plugins/zone.xml').getroot()
        self.control_field = self.zone + int(next(f for f in schema if f.get('name') == 'Native Resource Control Data').get('offset'), 0)
        at = c.pointer(c.u(self.control_field + 12))
        self.control = bytearray(c.data[at:at + c.u(self.control_field)])
        strings = StringTable(c)
        self.types = {strings.text(c.u(row + 24)): i for i, row in enumerate(c.block(self.zone + 4, 28))}
        self.manifest_field = self.zone + int(next(f for f in schema if f.get('name') == 'Static BSP Zone Manifests').get('offset'), 0)
        self.added_bytes = 0
        self.closed = False

    def table(self, offset, stride):
        return bytearray(b''.join(self.builder.read(self.address(x), stride) for x in self.cache.block(offset, stride)))

    def address(self, offset):
        return offset - self.cache.start + self.cache.base

    def newtag(self, group, payload):
        if self.closed:
            raise ValueError('Registry already finalized')
        index = len(self.tags) // 8
        if index >= 65535:
            raise ValueError('Retail tag index exhausted')
        address = self.builder.alloc(payload)
        salt = 0x9000
        self.tags.extend(struct.pack('>HHI', self.cache.groups.index(group), salt, address))
        return (salt << 16) | index, address

    def add_resource(self, owner, type_name, resource):
        if self.closed:
            raise ValueError('Registry already finalized')
        index = owner & 65535
        if index >= len(self.tags) // 8:
            raise ValueError('Resource owner tag does not exist')
        group, tag_salt = struct.unpack_from('>HH', self.tags, index * 8)
        if tag_salt != owner >> 16:
            raise ValueError('Resource owner salt mismatch')
        rid, page, location = len(self.resources) // 64, len(self.pages) // 88, len(self.locations) // 16
        if rid >= 65535 or page >= 32767 or location >= 32767:
            raise ValueError('Retail resource index exhausted')
        control, raw = resource['control'], resource['raw']
        sound = type_name == 'sound_resource_definition'
        if sound and (control or resource['root'] != 0 or resource['interops']
                      or resource['fixups'] != [(12, 0x40000000)]):
            raise ValueError('Unexpected sound resource layout')
        # Native sound resources serialize no control bytes. Their single fixup
        # addresses the data pointer in the runtime-created 20-byte dataref.
        control_size = 20 if sound else len(control)
        if not 0 <= resource['root'] < control_size:
            raise ValueError('Resource root outside control payload')
        for at, target in resource['fixups']:
            segment, offset = target & 0xe0000000, target & 0x1fffffff
            bound = len(control) if segment == 0x20000000 else len(raw) if segment == 0x40000000 else -1
            if not 0 <= at <= control_size - 4 or not 0 <= offset < bound:
                raise ValueError('Invalid new resource fixup')
        compressed = zlib.compress(raw)[2:-4]
        offset = self.builder.append_raw(compressed)
        entry = bytearray(88)
        struct.pack_into('>hBBhhIIII', entry, 0, 0, 1, 0, -1, 0, offset, len(compressed), len(raw), zlib.crc32(raw) ^ 0xffffffff)
        entry[24:84] = b''.join(hashlib.sha1(self.salt + x).digest() for x in (raw, raw[:1024], raw[-1024:]))
        struct.pack_into('>hh', entry, 84, 1, -1)
        self.pages.extend(entry)
        self.locations.extend(struct.pack('>hhIIhh', page, -1, 0, 0, -1, -1))
        row = bytearray(64)
        row[:4] = self.cache.groups[group].encode('ascii')
        struct.pack_into('>I', row, 12, owner)
        resource_salt = 0x9100
        struct.pack_into('>HBBIIIHhI', row, 16, resource_salt, self.types[type_name], 2,
                         0 if sound else len(self.control), len(control), 0 if sound else 0xffffffff,
                         1, location, 0x20000000 | resource['root'])
        for field, pairs in ((40, resource['fixups']), (52, resource['interops'])):
            data = b''.join(struct.pack('>II', *pair) for pair in pairs)
            struct.pack_into('>III', row, field, len(pairs), self.builder.alloc(data) if data else 0, 0)
        self.control.extend(control)
        self.resources.extend(row)
        self.added_bytes += len(raw)
        return (resource_salt << 16) | rid

    def finalize(self, bsp_index=0):
        if self.closed:
            raise ValueError('Registry already finalized')
        manifests = self.cache.block(self.manifest_field, 120)
        if not 0 <= bsp_index < len(manifests):
            raise ValueError('Selected BSP has no static residency manifest')
        b = self.builder
        self.stage_simulation_definitions()
        for at, stride, payload in ((self.zone + 0x58, 64, self.resources),
                                   (self.play + 0x18, 88, self.pages),
                                   (self.play + 0x24, 16, self.streaming),
                                   (self.play + 0x30, 16, self.locations)):
            b.put(self.address(at), 'III', len(payload) // stride, b.alloc(payload), 0)
        b.put(self.address(self.control_field), 'I', len(self.control))
        b.put(self.address(self.control_field + 12), 'I', b.alloc(self.control))
        b.put(self.address(self.index + 8), 'II', len(self.tags) // 8, b.alloc(self.tags))
        manifest = manifests[bsp_index]
        for field, indices in ((0, range(self.first_resource, len(self.resources) // 64)),
                               (0x54, range(self.first_tag, len(self.tags) // 8)),
                               (0x60, range(self.first_tag, len(self.tags) // 8))):
            if not indices:
                continue
            bits = self.table(manifest + field, 4)
            required = (indices[-1] // 32 + 1) * 4
            bits.extend(bytes(max(0, required - len(bits))))
            for index in indices:
                at = (index // 32) * 4
                value = struct.unpack_from('>I', bits, at)[0] | (1 << (index % 32))
                struct.pack_into('>I', bits, at, value)
            b.put(self.address(manifest + field), 'III', len(bits) // 4, b.alloc(bits), 0)
        b.put(self.address(manifest + 0x30), 'I', self.cache.u(manifest + 0x30) + self.added_bytes)
        self.closed = True

    def stage_simulation_definitions(self):
        """Keep live native definitions in order, then append converted definitions."""
        schema = ET.parse(Path(__file__).resolve().parents[1] / 'reference/plugins/scnr.xml').getroot()
        field = next(x for x in schema if x.get('name') == 'Simulation Definition Table')
        scenario = next(t['offset'] for t in self.cache.tags.values() if t['group'] == 'scnr')
        at = scenario + int(field.get('offset'), 0)
        original = self.table(at, 4)
        payload = bytearray(b''.join(original[j:j + 4] for j in range(0, len(original), 4)
            if struct.unpack_from('>H', self.tags, (struct.unpack_from('>I', original, j)[0] & 65535) * 8)[0] != 65535))
        groups = {'bipd', 'vehi', 'weap', 'eqip', 'garb', 'proj', 'scen', 'mach',
                  'ctrl', 'lifi', 'ssce', 'bloc', 'crea', 'term', 'efsc', 'effe', 'jpt!'}
        self.simulation_added = []
        for index in range(self.first_tag, len(self.tags) // 8):
            group, salt = struct.unpack_from('>HH', self.tags, index * 8)
            if self.cache.groups[group] in groups:
                datum = (salt << 16) | index
                payload.extend(struct.pack('>I', datum))
                self.simulation_added.append(datum)
        if self.simulation_added:
            self.builder.put(self.address(at), 'III', len(payload) // 4, self.builder.alloc(payload), 0)
