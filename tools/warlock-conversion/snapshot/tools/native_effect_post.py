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

    def __call__(self, group, template_name):
        def matches(cache):
            result = []
            for tag in cache.tags.values():
                actual = tag['group']
                if actual != group and not (group == 'rmd ' and actual == 'decs'):
                    continue
                if actual == 'cntl':
                    containers = [row + 0x158 for row in cache.block(tag['offset'], 0x26c)]
                elif actual == 'decs':
                    containers = [row + 48 for row in cache.block(tag['offset'] + 20, 116)]
                else:
                    containers = [tag['offset'] + (40 if actual == 'rmd ' else 100)]
                for container in containers:
                    for post in cache.block(container, 132):
                        if cache.name(cache.u(post + 12) & 65535) == template_name:
                            result.append(post)
            return result

        filename = 'armory.map'
        if group in ('rmd ', 'prt3', 'cntl'):
            filename = None
            for candidate in sorted(self.disc_maps.glob('*.map')):
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
            native = NativeShaderImporter(donor, i, self.resolved,
                {'maps\\shared.map': self.disc_maps / 'shared.map'})
            schema = ET.parse(i.reference / 'plugins' / f'{group.strip()}.xml').getroot()
            schema = next(node for node in schema.iter('tagblock') if node.get('name') == 'Postprocess')
            converter = MetadataConverter(donor, i.builder, strings, i.target_strings, native.import_tag)
            output = converter.convert(post, schema, schema, f'native-{group}/Postprocess')
            return output, names, filename
        finally:
            donor.close()
