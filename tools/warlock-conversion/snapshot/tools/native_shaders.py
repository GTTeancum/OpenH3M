"""Relocate native retail shader metadata and bytecode from original disc maps.

No shader recompilation or runtime patches. Native bitmap dependencies retain
their original GPU format/mips; unsupported resource layouts reject.
"""
import xml.etree.ElementTree as ET
import struct
from pathlib import Path
from string_ids import StringTable
from tag_metadata import MetadataConverter


class NativeShaderImporter:
    GROUPS = {'rmtr', 'rmt2', 'rmdf', 'rmop', 'pixl', 'vtsh', 'glps', 'glvs', 'bitm'}

    def __init__(self, source, importer, resolved=None, shared_paths=None):
        if source.mcc:
            raise ValueError('Native shader donor must be a retail cache')
        self.source, self.importer = source, importer
        self.strings = StringTable(source)
        self.resolved = resolved if resolved is not None else {}
        target = importer.registry.cache
        self.existing = {(tag['group'], target.name(index)): (tag['group'], tag['salt'] << 16 | index)
                         for index, tag in target.tags.items() if target.name(index) is not None}
        self.failed = False
        self.shader_pointers = {}
        self.shared_paths = shared_paths

    def shader_pointer(self, pointer, shader_type):
        if not pointer:
            return 0
        key = pointer, shader_type
        if key in self.shader_pointers:
            return self.shader_pointers[key]
        # Assembly's H3 layouts and ThirdGenShaderStreamer injection strategy:
        # zero runtime info, relocate its data pointer, copy relative debug data.
        sizes = {'pixel': 0x28, 'vertex': 0x368}
        if shader_type not in sizes:
            raise ValueError('Unknown native shader type')
        s, b = self.source, self.importer.builder
        at, size = s.pointer(pointer), sizes[shader_type]
        debug = at + size
        if at < 0 or debug + 28 > len(s.data):
            raise ValueError('Native shader header outside donor')
        magic, debug_size, data_size = s.unpack('III', debug)
        data_at = s.pointer(s.u(at + 16))
        if (magic >> 16 != 0x102a or debug_size < 28 or debug + debug_size > len(s.data)
                or data_size == 0 or data_at < 0 or data_at + data_size > len(s.data)):
            raise ValueError('Invalid native shader debug/data bounds')
        info = bytearray(size)
        struct.pack_into('>I', info, 16, b.alloc(bytes(s.data[data_at:data_at + data_size])))
        info.extend(s.data[debug:debug + debug_size])
        result = b.alloc(info)
        self.shader_pointers[key] = result
        return result

    def import_tag(self, datum):
        if self.failed:
            raise ValueError('Native shader importer has an incomplete dependency graph')
        try:
            return self._import(datum)
        except Exception:
            self.failed = self.importer.failed = True
            raise

    def _import(self, datum):
        s, i = self.source, self.importer
        tag = s.tags.get(datum & 65535)
        if tag is None or tag['salt'] != datum >> 16:
            raise ValueError('Invalid native shader dependency datum')
        group, name = tag['group'], s.name(datum & 65535)
        key = (group, name) if name is not None else (str(Path(s.file.name).resolve()), datum)
        if key in self.resolved:
            return self.resolved[key]
        if key in self.existing:
            return self.existing[key]
        if group not in self.GROUPS:
            raise ValueError(f'Native shader dependency needs dedicated import: {group}:{name}')
        schema = ET.parse(i.reference / 'plugins' / f'{group}.xml').getroot()
        owner, address = i.registry.newtag(group, bytes(int(schema.get('baseSize'), 0)))
        self.resolved[key] = group, owner

        def data(path, cache, at):
            if group not in {'pixl', 'vtsh', 'glps', 'glvs'} or not path.endswith('Compiled Shader'):
                raise ValueError(f'Unrecognized native shader data: {path}')
            count = cache.u(at)
            start = cache.pointer(cache.u(at + 12))
            if start < 0 or start + count > len(cache.data):
                raise ValueError('Native shader bytecode is outside donor cache')
            return bytes(cache.data[start:start + count])

        def resource(path, resource_datum):
            if group != 'bitm' or '/Hardware Textures[' not in path:
                raise ValueError(f'Unsupported native shader resource: {path}')
            from native_bitmap_resource import copy_bitmap_resource
            payload = copy_bitmap_resource(s, resource_datum, self.shared_paths)
            return i.registry.add_resource(owner, 'bitmap_texture_interop_resource', payload)

        converter = MetadataConverter(s, i.builder, self.strings, i.target_strings,
                                      self.import_tag, data_reference=data,
                                      shader_reference=self.shader_pointer, resource_reference=resource)
        payload = converter.convert(tag['offset'], schema, schema, f'{group}:{name}')
        at = address - i.builder.base
        i.builder.meta[at:at + len(payload)] = payload
        i.added.append({'source': name, 'group': group, 'datum': hex(owner),
                        'native_shader_donor': True})
        return group, owner
