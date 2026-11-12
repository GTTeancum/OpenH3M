"""Relocate missing effect shader routing from an explicit original-disc donor."""
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache
from native_shaders import NativeShaderImporter
from string_ids import StringTable
from tag_metadata import MetadataConverter


class NativeEffectPost:
    def __init__(self, importer, disc_maps):
        self.importer, self.disc_maps = importer, Path(disc_maps)
        self.resolved = {}
        self.parameter_switches = {}

    def cubemap(self, name):
        if name != r'levels\multi\snowbound\bitmaps\cube_icecave_a_cubemap':
            raise ValueError(f'No verified native cubemap donor: {name}')
        donor = Cache(str(self.disc_maps / 'snowbound.map'))
        try:
            matches = [(tag['salt'] << 16) | index for index, tag in donor.tags.items()
                       if tag['group'] == 'bitm' and donor.name(index) == name]
            if len(matches) != 1:
                raise ValueError(f'Snowbound is missing expected cubemap: {name}')
            native = NativeShaderImporter(donor, self.importer, self.resolved,
                {'maps\\shared.map': self.disc_maps / 'shared.map'})
            return native.import_tag(matches[0])[1]
        finally:
            donor.close()

    def __call__(self, group, template_name, *, replace_material_textures=False,
                 preferred_material=None, preferred_map=None):
        def matches(cache):
            result = []
            for index, tag in cache.tags.items():
                if preferred_material is not None and cache.name(index) != preferred_material:
                    continue
                actual = tag['group']
                # Embedded decal-system and standalone decal materials share
                # the same native Postprocess layout and shader family.
                if actual != group and not ({group, actual} == {'rmd ', 'decs'}):
                    continue
                if actual == 'cntl':
                    containers = [row + 0x158 for row in cache.block(tag['offset'], 0x26c)]
                elif actual == 'beam':
                    containers = [row + 0x2c for row in cache.block(tag['offset'], 0x208)]
                elif actual == 'decs':
                    containers = [row + 48 for row in cache.block(tag['offset'] + 20, 116)]
                else:
                    containers = [tag['offset'] + (40 if actual in ('rmd ', 'rmsh', 'rmtr', 'rmhg') else 100)]
                for container in containers:
                    for post in cache.block(container, 132):
                        if cache.name(cache.u(post + 12) & 65535) == template_name:
                            result.append(post)
            return result

        filename = 'armory.map'
        if group in ('rmd ', 'prt3', 'cntl', 'beam', 'rmsh', 'rmtr', 'rmhg', 'decs'):
            filename = None
            for candidate in sorted(self.disc_maps.glob('*.map')):
                if preferred_map is not None and candidate.name != preferred_map:
                    continue
                if candidate.name in ('shared.map', 'campaign.map'):
                    continue
                cache = Cache(str(candidate))
                try:
                    found = bool(matches(cache))
                finally:
                    cache.close()
                if found:
                    filename = candidate.name
                    break
        elif (group, template_name) not in {
                ('cntl', r'shaders\contrail_templates\_0_3_0_0'),
                ('prt3', r'shaders\particle_templates\_1_3_0_0_1_0_0_0_0_0')}:
            raise ValueError(f'No verified native effect donor: {group}:{template_name}')
        if filename is None:
            raise ValueError(f'No exact native effect donor: {group}:{template_name}')
        i = self.importer
        donor = Cache(str(self.disc_maps / filename))
        try:
            candidates = matches(donor)
            if not candidates:
                raise ValueError(f'{filename} is missing expected effect template: {template_name}')
            post = candidates[0]
            strings = StringTable(donor)
            names = i.materials.parameters(donor, strings, post)
            template = donor.tags[donor.u(post + 12) & 65535]['offset']
            self.parameter_switches[template_name] = {
                'integer': [strings.text(donor.u(x)) for x in donor.block(template + 84, 4)],
                'boolean': [strings.text(donor.u(x)) for x in donor.block(template + 96, 4)]}
            native = NativeShaderImporter(donor, i, self.resolved,
                {'maps\\shared.map': self.disc_maps / 'shared.map'})
            schema = ET.parse(i.reference / 'plugins' / f'{group.strip()}.xml').getroot()
            schema = next(node for node in schema.iter('tagblock') if node.get('name') == 'Postprocess')
            if replace_material_textures:
                if group not in ('rmsh', 'rmtr', 'rmhg', 'decs'):
                    raise ValueError('Texture replacement is limited to standard materials and decals')
                import copy
                schema = copy.deepcopy(schema)
                texture_block = next(node for node in schema if node.tag == 'tagblock' and int(node.get('offset', '-1'), 0) == 16)
                schema.remove(texture_block)
                for offset in (16, 20, 24):
                    ET.SubElement(schema, 'uint32', name=f'Replaced texture field {offset}', offset=hex(offset))
            def data(path, cache, at):
                if group not in ('rmsh','rmtr','rmhg') or not path.endswith('/Animation Function'):
                    raise ValueError(f'Unsupported native shader data: {path}')
                size = cache.u(at)
                start = cache.pointer(cache.u(at + 12))
                if start + size > len(cache.data):
                    raise ValueError('Native shader function outside donor')
                return bytes(cache.data[start:start + size])
            converter = MetadataConverter(donor, i.builder, strings, i.target_strings, native.import_tag,
                                          data_reference=data,
                special_block=lambda at, ss, ds, path: bytes(12)
                    if group == 'decs' and replace_material_textures
                    and ss.get('name') in ('Entry Points', 'Passes', 'Routing Info', 'Overlays') else None)
            output = converter.convert(post, schema, schema, f'native-{group}/Postprocess')
            if replace_material_textures:
                import struct
                textures = bytearray()
                for row in donor.block(post + 16, 24):
                    texture = bytearray(donor.data[row:row + 24])
                    # The caller must bind every slot. Keep native sampler and
                    # transform metadata, never copy donor cache identifiers.
                    texture[:16] = b'bitm' + bytes(8) + b'\xff' * 4
                    textures.extend(texture)
                output = bytearray(output)
                struct.pack_into('>III', output, 16, len(textures)//24, i.builder.alloc(textures), 0)
            return output, names, filename
        finally:
            donor.close()
