"""POC water binding through original retail shader programs and wave arrays."""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from cache_reader import Cache
from native_shaders import NativeShaderImporter
from string_ids import StringTable
from tag_metadata import MetadataConverter
from tag_functions import convert_function

VARIANTS = {
    '_0_1_1_1_1_0_1_3': ('riverworld.map', '_0_1_1_1_1_0_1_3'),
    '_0_0_1_1_1_0_2_1': ('zanzibar.map', '_0_0_1_1_2_0_2_3'),
    '_0_1_1_1_2_0_1_2': ('docks.map', '_0_1_1_1_2_0_1_3'),
}


class WaterImporter:
    def __init__(self, importer, disc_maps):
        self.i, self.disc_maps = importer, Path(disc_maps)
        self.resolved, self.done = {}, {}

    def shader(self, datum):
        if datum in self.done:
            return self.done[datum]
        i, s, b = self.i, self.i.source, self.i.builder
        native_assets = getattr(i, 'native_assets', None)
        if native_assets is not None:
            native = native_assets.import_named((s.tags[datum & 65535]['group'], s.name(datum & 65535)))
            if native is not None:
                return native
        tag = s.tags[datum & 65535]
        if tag['group'] != 'rmw ' or tag['salt'] != datum >> 16:
            raise ValueError('Invalid water shader datum')
        root = tag['offset']
        posts = s.block(root + 40, 140)
        if len(posts) != 1 or s.u(root + 28):
            raise ValueError('Water requires one postprocess and no editor parameters')
        post = posts[0]
        source_template = s.tags[s.u(post + 12) & 65535]['offset']
        variant = s.name(s.u(post + 12) & 65535).rsplit('\\', 1)[-1]
        variants = dict(VARIANTS)
        if getattr(i, 'stock_forge_palette', False):
            variants.update({
                '_0_1_1_1_2_0_2_2': ('deadlock.map', '_0_1_1_1_2_0_2_3'),
                '_0_0_1_1_2_0_1_0': ('zanzibar.map', '_0_0_1_1_2_0_2_3'),
                '_0_0_1_1_1_0_1_0': ('zanzibar.map', '_0_0_1_1_2_0_2_3'),
            })
        if variant not in variants:
            raise ValueError('Water variant has no documented retail mapping')
        if [s.unpack('h', row)[0] for row in s.block(root + 16, 2)] != [int(value) for value in variant.split('_')[1:]]:
            raise ValueError('Water root options differ from its compiled template')
        filename, target_variant = variants[variant]
        donor = Cache(str(self.disc_maps / filename))
        try:
            native = NativeShaderImporter(donor, i, self.resolved,
                {'maps\\shared.map': self.disc_maps / 'shared.map'})
            lookup = {(t['group'], donor.name(k)): t['salt'] << 16 | k for k, t in donor.tags.items()}
            name = 'shaders\\water_templates\\' + target_variant
            td = lookup['rmt2', name]
            target_template = donor.tags[td & 65535]['offset']
            strings = StringTable(donor)
            def names(cache, table, at, offset):
                return [table.text(cache.u(row)) for row in cache.block(at + offset, 4)]
            source_textures = names(s, i.source_strings, source_template, 108)
            target_textures = names(donor, strings, target_template, 108)
            source_constants = names(s, i.source_strings, source_template, 72)
            target_constants = names(donor, strings, target_template, 72)
            if (s.u(source_template + 84) or donor.u(target_template + 84)
                    or names(s, i.source_strings, source_template, 96) != names(donor, strings, target_template, 96)):
                raise ValueError('Water integer/boolean template layout mismatch')
            # Find an actual donor material for its reflection cubemap.
            donor_post = next(p for t in donor.tags.values() if t['group'] == 'rmw '
                for p in donor.block(t['offset'] + 40, 132) if donor.u(p + 12) == td)
            donor_textures = donor.block(donor_post + 16, 24)
            textures = s.block(post + 16, 28)
            constants = s.block(post + 28, 16)
            if len(textures) != len(source_textures) or len(constants) != len(source_constants):
                raise ValueError('Water parameter counts differ from its template')
            overlays = s.block(post + 92, 36)
            for row in overlays:
                kind, input_name, range_name, period = s.unpack('IIIf', row)
                size, start = s.u(row + 16), s.pointer(s.u(row + 28))
                function = bytes(s.data[start:start + size])
                limit = 120 if getattr(i, 'stock_forge_palette', False) else 60
                opcodes = (0,3) if getattr(i, 'stock_forge_palette', False) else (0,)
                if kind not in (0, 5, 6) or input_name or range_name or not 0 < period <= limit or not function or function[0] not in opcodes:
                    raise ValueError('Water animation exceeds documented static POC mapping')
                convert_function(function)
            definition = native.import_tag(lookup['rmdf', r'shaders\water'])
            _, template = native.import_tag(td)
            output = bytearray(132)
            output[:16] = b'rmt2' + bytes(8) + struct.pack('>I', template)
            records, substitutions = bytearray(), []
            for parameter in target_textures:
                if parameter in source_textures:
                    row = textures[source_textures.index(parameter)]
                    bitmap = s.u(row + 12)
                    index, address, filtering, comparison, external, transform, pad, routing, pad2 = s.unpack('h4BbBhH', row + 16)
                    if index or comparison or pad or pad2 or transform < -1 or (routing and not overlays):
                        raise ValueError('Unsupported water sampler routing')
                    if transform >= 0:
                        transform_name = source_constants[transform]
                        transform = target_constants.index(transform_name)
                    if parameter in ('wave_displacement_array', 'wave_slope_array'):
                        key = ('bitm', s.name(bitmap & 65535))
                        wave = lookup.get(key)
                        if wave is None and getattr(i, 'stock_forge_palette', False):
                            wave = donor.u(donor_textures[target_textures.index(parameter)] + 12)
                            substitutions.append({'parameter': parameter, 'native_bitmap': donor.name(wave & 65535)})
                        if wave is None:raise ValueError('Native water wave array absent: '+key[1])
                        _, bitmap = native.import_tag(wave)
                    elif parameter == 'environment_map':
                        donor_bitmap = donor.u(donor_textures[target_textures.index(parameter)] + 12)
                        _, bitmap = native.import_tag(donor_bitmap)
                        substitutions.append({'parameter': parameter, 'native_bitmap': donor.name(donor_bitmap & 65535)})
                    elif bitmap != 0xffffffff:
                        bitmap = i.materials.bitmap(bitmap)
                else:
                    defaults = {'global_shape_texture': 'color_black', 'watercolor_texture': 'color_white'}
                    if parameter not in defaults:
                        raise ValueError(f'Water texture has no explicit default: {parameter}')
                    bitmap = i.materials.target_names['bitm', 'shaders\\default_bitmaps\\bitmaps\\' + defaults[parameter]]
                    index, address, filtering, external, transform = 0, 0x11, 0, 0, -1
                    substitutions.append({'parameter': parameter, 'native_default': defaults[parameter]})
                records.extend((b'bitm' if bitmap != 0xffffffff else b'\xff'*4) + bytes(8)
                               + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, 0))
            values = bytearray()
            for parameter in target_constants:
                if parameter in source_constants:
                    values.extend(struct.pack('>4I', *s.unpack('4I', constants[source_constants.index(parameter)])))
                elif parameter in ('foam_height', 'foam_pow'):
                    value = 1000000. if parameter == 'foam_height' else 1.
                    values.extend(struct.pack('>4f', value, value, value, value))
                elif getattr(i, 'stock_forge_palette', False):
                    native_constants = donor.block(donor_post + 28, 16)
                    values.extend(donor.data[native_constants[target_constants.index(parameter)]:
                                             native_constants[target_constants.index(parameter)]+16])
                    substitutions.append({'parameter': parameter, 'constant': 'Native donor material default'})
                else:
                    raise ValueError(f'Water constant has no explicit default: {parameter}')
            struct.pack_into('>III', output, 16, len(target_textures), b.alloc(records), 0)
            struct.pack_into('>III', output, 28, len(target_constants), b.alloc(values), 0)
            struct.pack_into('>I', output, 52, s.u(post + 52))
            struct.pack_into('>III8h', output, 104, *s.unpack('III8h', post + 104))
            # Queryable constants are indices; update those shifted by remapping.
            for offset in range(116, 132, 2):
                index = struct.unpack_from('>h', output, offset)[0]
                if index >= 0:
                    if index >= len(source_constants) or source_constants[index] not in target_constants:
                        raise ValueError('Water queryable property cannot be remapped')
                    struct.pack_into('>h', output, offset, target_constants.index(source_constants[index]))
            ss = ET.parse(i.reference / 'mcc/rmw.xml').getroot()
            ds = ET.parse(i.reference / 'plugins/rmw.xml').getroot()
            def reference(value):
                if value != s.u(root + 12):
                    raise ValueError('Unexpected water root dependency')
                return definition
            converter = MetadataConverter(s, b, i.source_strings, i.target_strings, reference,
                special_block=lambda at, sf, df, path: bytes(output) if sf.get('name') == 'Postprocess' else None)
            payload = bytearray(converter.convert(root, ss, ds, 'rmw :' + s.name(datum & 65535)))
            options = [int(value) for value in target_variant.split('_')[1:]]
            struct.pack_into('>III', payload, 16, len(options), b.alloc(struct.pack('>8h', *options)), 0)
            owner, _ = i.registry.newtag('rmw ', payload)
            self.done[datum] = 'rmw ', owner
            i.materials.report.append({'source': s.name(datum & 65535), 'retail_template': name,
                'native_donor': filename, 'approximation': True, 'texture_substitutions': substitutions,
                'difference': 'Static authored wave/UV values; original-disc reflection cubemap; pure water uses uniform bank opacity; unused extra foam contribution disabled.',
                'omitted_constants': sorted(set(source_constants)-set(target_constants)),
                'frozen_overlays': len(overlays)})
            return self.done[datum]
        except Exception:
            i.failed = True
            raise
        finally:
            donor.close()
