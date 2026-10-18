"""Import a dependency graph into a scratch retail cache registry.

Any failure invalidates the importer; discard its builder. Resource and opaque
data handlers remain explicit so unsupported content cannot become a partial map.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
from string_ids import StringTable, WritableStringTable
from tag_metadata import MetadataConverter
from resource_reader import Resource
from render_resource import convert_render_resource
from material_importer import MaterialImporter
import struct


class TagImporter:
    def __init__(self, source, registry, bindings=None):
        self.source, self.registry = source, registry
        self.builder = registry.builder
        self.reference = Path(__file__).resolve().parents[1] / 'reference'
        self.source_strings = StringTable(source)
        self.target_strings = WritableStringTable(self.builder)
        self.resolved = {(t['group'], registry.cache.name(i)): (t['group'], (t['salt'] << 16) | i)
                         for i, t in registry.cache.tags.items()}
        self.resolved.update(bindings or {})
        self.added = []
        self.materials = MaterialImporter(source, registry)
        self.failed = False

    def import_tag(self, datum):
        if self.failed:
            raise ValueError('Importer failed previously; discard this scratch build')
        try:
            return self._import(datum)
        except Exception:
            self.failed = True
            raise

    def _import(self, datum):
        source = self.source
        tag = source.tags[datum & 65535]
        if tag['salt'] != datum >> 16:
            raise ValueError(f'Source tag salt mismatch: {datum:#x}')
        key = tag['group'], source.name(datum & 65535)
        if key in self.resolved:
            return self.resolved[key]
        group, name = key
        if group in ('rmsh', 'rmfl'):
            result = self.materials.shader(datum)
            self.resolved[key] = result
            return result
        if group == 'bitm':
            result = ('bitm', self.materials.bitmap(datum))
            self.resolved[key] = result
            return result
        ss = ET.parse(self.reference / 'mcc' / f'{group}.xml').getroot()
        ds = ET.parse(self.reference / 'plugins' / f'{group}.xml').getroot()
        size = int(ds.get('baseSize'), 0)
        owner, address = self.registry.newtag(group, bytes(size))
        # Reserve before recursion so legitimate cyclic references resolve.
        self.resolved[key] = (group, owner)

        def resource(path, resource_datum):
            if group != 'mode' or not path.endswith('/[zone] Asset Datum'):
                raise ValueError(f'{path}: resource type requires a dedicated importer')
            payload = convert_render_resource(Resource(source, resource_datum))
            return self.registry.add_resource(owner, 'render_geometry_api_resource_definition', payload)

        def data(path, cache, at):
            # The observed model PRT-info descriptor is five 32-bit words.
            # Gate the exact header/layout; other user payloads remain unsupported.
            if group == 'mode' and '/User Data[' in path and path.endswith('/User Data'):
                kind, count, stride = cache.unpack('BBH', at - 4)
                size = cache.u(at)
                if (kind, count, stride, size) == (0, 1, 20, 20):
                    payload = cache.pointer(cache.u(at + 12))
                    return struct.pack('>5I', *cache.unpack('5I', payload))
            raise ValueError(f'{path}: opaque data format not implemented')

        converter = MetadataConverter(source, self.builder, self.source_strings,
                                      self.target_strings, self.import_tag,
                                      data_reference=data,
                                      resource_reference=resource)
        payload = converter.convert(tag['offset'], ss, ds, f'{group}:{name}')
        if len(payload) != size:
            raise ValueError('Converted tag root size mismatch')
        offset = address - self.builder.base
        self.builder.meta[offset:offset + size] = payload
        self.added.append({'source': name, 'group': group, 'datum': hex(owner)})
        return group, owner

    def finalize(self, bsp_index=0):
        if self.failed:
            raise ValueError('Cannot finalize an incomplete dependency graph')
        self.target_strings.stage()
        self.registry.finalize(bsp_index)
