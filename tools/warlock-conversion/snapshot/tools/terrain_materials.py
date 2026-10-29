"""Bind MCC terrain and hologram parameters to original-disc shader templates."""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable
from tag_metadata import MetadataConverter
from native_shaders import NativeShaderImporter
from assemble_scenario import field

DONORS = {'_0_1_1_0_0_0': 'sandbox.map', '_0_2_1_1_1_2': 'docks.map',
          '_0_2_1_1_2_0': 'chill.map', '_0_1_1_1_1_2': 'sidewinder.map'}
HOLOGRAM_DONORS = {'_0_8_1_0_0_0_0': 'construct.map', '_2_3_1_0_0_0_1': 'sandbox.map', '_2_1_1_0_0_0_1': 'lockout.map', '_2_8_0_0_0_1_0': 'sandbox.map', '_0_3_1_0_0_0_1': 'lockout.map'}


class DiscMaterialImporter:
    def __init__(self, importer, disc_maps):
        self.importer, self.disc_maps = importer, Path(disc_maps)
        self.resolved, self.done = {}, {}
        self.hologram_donors = dict(HOLOGRAM_DONORS)

    def shader(self, datum):
        if datum in self.done:
            return self.done[datum]
        i, s, b = self.importer, self.importer.source, self.importer.builder
        native_assets = getattr(i, 'native_assets', None)
        if native_assets is not None:
            native = native_assets.import_named((s.tags[datum & 65535]['group'], s.name(datum & 65535)))
            if native is not None:
                return native
        tag = s.tags[datum & 65535]
        group = tag['group']
        if group not in ('rmtr', 'rmhg') or tag['salt'] != datum >> 16:
            raise ValueError('Invalid specialized material datum')
        root = tag['offset']
        posts = s.block(root + 40, 140)
        if len(posts) != 1 or s.u(root + 28):
            raise ValueError('Terrain requires one compiled postprocess and no editor parameters')
        post = posts[0]
        template_name = s.name(s.u(post + 12) & 65535)
        variant = template_name.rsplit('\\', 1)[-1]
        source_options = [int(value) for value in variant.split('_')[1:]]
        source_variant = variant
        fallback = None
        prt_two_layer = (getattr(i, 'stock_forge_palette', False) and group == 'rmtr'
                         and s.name(datum & 65535) == r'levels\multi\forge_halo\shaders\forge_halo_rocks')
        if getattr(i, 'stock_forge_palette', False) and group == 'rmtr':
            # This disc template retains all four authored terrain layers.
            # Several identically named retail variants only support three.
            sr = s.tags[s.u(post + 12) & 65535]['offset']
            names = [i.source_strings.text(s.u(row)) for row in s.block(sr + 108, 4)]
            fallback = '_0_0_1_1_1_2' if 'base_map_m_3' in names and variant != '_0_0_1_1_1_2' else None
            if fallback:
                variant = fallback
                template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        if prt_two_layer:
            if source_variant != '_0_0_1_1_2_0':
                raise ValueError('Forge rock PRT mapping needs review for changed source options')
            # Guardian's exact variant has no ambient PRT pass. Cold Storage
            # supports it with an extra material. Zero its otherwise ignored
            # blue weight, retaining the source two-layer normalization.
            fallback = variant = '_0_0_1_1_1_0'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        donors = DONORS if group == 'rmtr' else self.hologram_donors
        if group == 'rmhg':
            if len(source_options) != 9 or any(source_options[7:]):
                raise ValueError('Nondefault MCC-only hologram options require separate conversion')
            variant = '_' + '_'.join(str(value) for value in source_options[:7])
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        reach_grid = (group == 'rmhg' and s.name(datum & 65535) ==
                      r'objects\levels\forge\ff_grid_object\shaders\ff_grid_object_depth')
        if reach_grid:
            if variant != '_2_10_1_0_0_2_0':
                raise ValueError('Reach grid template changed; re-audit required')
            # Original source rmdf: option 10 is multilayer four-change-color.
            # Cold Storage option 8 retains the layers, depth and overlay maps,
            # with an explicit color constant instead of the MCC color binding.
            fallback = variant = '_2_8_1_0_0_2_0'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        if variant not in donors:
            # Exact native shader variants are safe to discover by name; the
            # parameter/layout checks below still validate the actual binding.
            for candidate in sorted(self.disc_maps.glob('*.map')):
                if candidate.name in ('shared.map', 'campaign.map'):
                    continue
                cache = Cache(str(candidate))
                try:
                    found = any(t['group'] == 'rmt2' and cache.name(k) == template_name
                                for k, t in cache.tags.items())
                finally:
                    cache.close()
                if found:
                    donors[variant] = candidate.name
                    break
        if variant not in donors:
            raise ValueError(f'No verified native terrain donor: {template_name}')
        donor = Cache(str(self.disc_maps / donors[variant]))
        try:
            native = NativeShaderImporter(donor, i, self.resolved)
            native.donor_scoped = getattr(i, 'stock_forge_palette', False)
            lookup = {(t['group'], donor.name(k)): (t['salt'] << 16) | k
                      for k, t in donor.tags.items()}
            target_template = lookup['rmt2', template_name]
            native_strings = StringTable(donor)
            source_template = s.tags[s.u(post + 12) & 65535]['offset']
            target_root = donor.tags[target_template & 65535]['offset']
            if prt_two_layer and not donor.u(target_root + 32) & (1 << 6):
                raise ValueError('Forge rock donor lacks ambient PRT')
            promote_layer_count = False
            omitted_constants = []
            float_indices = None
            texture_indices = None
            float_defaults = {}
            for offset in (72, 84, 96, 108):
                source_names = [i.source_strings.text(s.u(r)) for r in s.block(source_template + offset, 4)]
                target_names = [native_strings.text(donor.u(r)) for r in donor.block(target_root + offset, 4)]
                if prt_two_layer and offset in (72, 108):
                    mapped_names = [n.replace('_m_2', '_m_0') for n in target_names]
                    if any(n not in source_names for n in mapped_names):
                        raise ValueError('Unknown parameter in Forge rock PRT mapping')
                    indices = [source_names.index(n) for n in mapped_names]
                    if offset == 72:
                        float_indices = indices
                        omitted_constants = sorted(set(source_names) - set(mapped_names))
                        if any(not n.startswith('environment_specular_contribution_m_') for n in omitted_constants):
                            raise ValueError('Forge rock PRT mapping drops an active parameter')
                    else:
                        texture_indices = indices
                        blend_row = s.block(post + 16, 28)[source_names.index('blend_map')]
                        blend_name = s.name(s.u(blend_row + 12) & 65535)
                        if ('bitm', blend_name) in i.materials.done:
                            raise ValueError('Forge rock blend bitmap was already imported without channel mask')
                        i.materials.zero_blue_blend_maps = getattr(i.materials, 'zero_blue_blend_maps', set()) | {blend_name}
                elif group == 'rmhg' and offset == 84 and not source_names and target_names == ['layers_of_4']:
                    promote_layer_count = True
                elif source_names != target_names:
                    omitted = set(source_names) - set(target_names)
                    if reach_grid and offset == 72 and [n for n in target_names if n != 'self_illum_color'] == source_names:
                        float_indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                        float_defaults = {j: 1.0 for j,n in enumerate(target_names) if n == 'self_illum_color'}
                    elif fallback and offset == 72:
                        missing = set(target_names) - set(source_names)
                        allowed = ('diffuse_coefficient_m_', 'specular_coefficient_m_', 'specular_power_m_',
                                   'specular_tint_m_', 'fresnel_curve_steepness_m_', 'area_specular_contribution_m_',
                                   'analytical_specular_contribution_m_', 'albedo_specular_tint_blend_m_')
                        if any(not n.startswith(allowed) for n in missing):
                            raise ValueError('Terrain fallback missing non-material constants: '+str(missing))
                        float_indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                        float_defaults = {j:(1.0 if n.startswith(('diffuse_coefficient_', 'specular_power_')) else 0.0)
                                          for j,n in enumerate(target_names) if n in missing}
                        omitted_constants = sorted(omitted)
                    elif fallback and offset == 108 and set(target_names).issubset(source_names):
                        indices = [source_names.index(n) for n in target_names]
                        if offset == 72:
                            float_indices = indices
                            omitted_constants = sorted(omitted)
                        else:
                            texture_indices = indices
                    elif (group == 'rmtr' and offset == 72
                            and (variant.endswith('_0') or getattr(i, 'stock_forge_palette', False))
                            and omitted and all(n.startswith('environment_specular_contribution_m_') for n in omitted)
                            and [n for n in source_names if n not in omitted] == target_names):
                        float_indices = [source_names.index(n) for n in target_names]
                        omitted_constants = sorted(omitted)
                    else:
                        raise ValueError(f'Terrain parameter order differs: {template_name} field {offset}: {source_names} vs {target_names}')
            options = [s.unpack('h', r)[0] for r in s.block(root + 16, 2)]
            if options != source_options:
                raise ValueError('Terrain root options differ from template variant')
            definition = native.import_tag(lookup['rmdf', 'shaders\\' + ('terrain' if group == 'rmtr' else 'halogram')])
            _, template = native.import_tag(target_template)
            output = bytearray(132)
            output[:16] = b'rmt2' + bytes(8) + struct.pack('>I', template)
            overlays = s.block(post + 92, 36)
            # The three observed overlays scroll a water-ripple normal over 300s.
            # POC retains its authored static normal; reject any other animation.
            for row in overlays:
                size = s.u(row + 16)
                start = s.pointer(s.u(row + 28))
                expected = bytes.fromhex('0034000000000000000080bf0000000000000000000000000000000000000000')
                function = bytes(s.data[start:start + size])
                if group == 'rmtr':
                    if getattr(i, 'stock_forge_palette', False):
                        from tag_functions import convert_function
                        kind, input_id, range_id, period = s.unpack('IIIf', row)
                        if kind not in (5,6) or input_id or range_id or period not in (10.,40.):
                            raise ValueError('Unsupported Forge World terrain animation')
                        convert_function(function)
                    elif s.unpack('IIIf', row) != (6, 0, 0, 300.) or function != expected:
                        raise ValueError('Terrain animation outside the documented static-ripple approximation')
                else:
                    from tag_functions import convert_function
                    kind, input_id, range_id, period = s.unpack('IIIf', row)
                    glow = (s.name(datum & 65535) == r'objects\gear\covenant\military\shaders\cov_storage_glow'
                            and i.source_strings.text(input_id) == 'e_glow'
                            and kind in (0, 1) and len(function) == 32 and function[0] == 0)
                    seat_power = (s.name(datum & 65535).startswith('objects\\vehicles\\')
                                  and i.source_strings.text(input_id) in ('driver_seat_power', 'gunner_seat_power')
                                  and kind == 0 and len(function) == 32 and function[0] == 0)
                    # These functions affect the static parameters retained by
                    # this POC. Validate their full encoding below; opcode and
                    # allocation size alone do not determine support.
                    supported = kind in (0, 1, 5, 6)
                    if (input_id and not (glow or seat_power)) or range_id or not 0 < period < float('inf') or not supported:
                        raise ValueError(f'{s.name(datum & 65535)}: unsupported hologram animation {kind}, function size {len(function)}')
                    convert_function(function)  # Validate the complete function structure.
            textures = bytearray()
            rows = s.block(post + 16, 28)
            if len(rows) != s.u(source_template + 108):
                raise ValueError('Terrain texture count differs from template')
            if texture_indices is not None:
                rows = [rows[index] for index in texture_indices]
            for row in rows:
                bitmap = s.u(row + 12)
                index, address, filtering, comparison, external, transform, pad, animation, pad2 = s.unpack('h4BbBhH', row + 16)
                if comparison or pad or pad2 or (animation and not overlays):
                    raise ValueError('Unsupported terrain sampler routing')
                if index != 0:
                    raise ValueError('Terrain texture array/sub-image is unsupported')
                if float_indices is not None and transform >= 0:
                    if transform not in float_indices:
                        raise ValueError('Terrain sampler uses omitted transform')
                    transform = float_indices.index(transform)
                bitmap = i.materials.bitmap(bitmap) if bitmap != 0xffffffff else bitmap
                textures.extend((b'bitm' if bitmap != 0xffffffff else b'\xff' * 4) + bytes(8)
                                + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, 0))
            struct.pack_into('>III', output, 16, len(rows), b.alloc(textures), 0)
            for offset, stride, fmt, parameter_offset in ((28, 16, '4I', 72), (40, 4, 'I', 84)):
                rows = s.block(post + offset, stride)
                if len(rows) != s.u(source_template + parameter_offset):
                    raise ValueError('Terrain constant count differs from template')
                if offset == 28 and float_indices is not None:
                    payload = b''.join(struct.pack('>4f', *([float_defaults[j]] * 4)) if index < 0
                                       else struct.pack('>4I', *s.unpack('4I', rows[index]))
                                       for j,index in enumerate(float_indices))
                    rows = float_indices
                else:
                    payload = b''.join(struct.pack('>' + fmt, *s.unpack(fmt, row)) for row in rows)
                struct.pack_into('>III', output, offset, len(rows), b.alloc(payload) if rows else 0, 0)
            suppressed_specular = []
            if group == 'rmtr' and s.name(datum & 65535).startswith('levels\\multi\\warlock\\'):
                names = [i.source_strings.text(s.u(row)) for row in s.block(source_template + 72, 4)]
                pointer = struct.unpack_from('>I', output, 32)[0]
                # The converted terrain specular pass produces white subpixel
                # spikes. Keep layer blending, normals and diffuse lighting;
                # use a matte terrain approximation in this POC.
                for index, name in enumerate(names):
                    if any(term in name for term in ('specular_coefficient',
                            'specular_contribution', 'specular_tint', 'env_tint',
                            'fresnel_color', 'reflection_coefficient')):
                        b.put(pointer + index * 16, '4f', 0., 0., 0., 0.)
                        suppressed_specular.append(name)
            if promote_layer_count:
                names = [i.source_strings.text(s.u(row)) for row in s.block(source_template + 72, 4)]
                values = s.unpack('4f', s.block(post + 28, 16)[names.index('layers_of_4')])
                value = values[0]
                if not (1 <= value <= 255) or value != int(value) or any(component != value for component in values):
                    raise ValueError('Hologram layer count cannot be represented by the native integer constant')
                struct.pack_into('>III', output, 40, 1, b.alloc(struct.pack('>I', int(value))), 0)
            struct.pack_into('>I', output, 52, s.u(post + 52))
            struct.pack_into('>III8h', output, 104, *s.unpack('III8h', post + 104))
            if float_indices is not None:
                for offset in range(116, 132, 2):
                    index = struct.unpack_from('>h', output, offset)[0]
                    if index >= 0:
                        if index not in float_indices:
                            raise ValueError('Terrain query references an omitted parameter')
                        struct.pack_into('>h', output, offset, float_indices.index(index))
            ss = ET.parse(i.reference / 'mcc' / f'{group}.xml').getroot()
            ds = ET.parse(i.reference / 'plugins' / f'{group}.xml').getroot()

            def reference(value):
                if value != s.u(root + 12):
                    raise ValueError('Unexpected terrain root dependency')
                return definition

            converter = MetadataConverter(s, b, i.source_strings, i.target_strings, reference,
                special_block=lambda at, sf, df, path: bytes(output) if sf.get('name') == 'Postprocess' else None)
            payload = bytearray(converter.convert(root, ss, ds, group + ':' + s.name(datum & 65535)))
            if fallback:
                count, pointer = struct.unpack_from('>II', payload, 16)
                target_options = [int(v) for v in variant.split('_')[1:]]
                if count != len(target_options) and not (reach_grid and count == 9 and len(target_options) == 7):raise ValueError('Terrain fallback option count')
                for n,value in enumerate(target_options):b.put(pointer+n*2,'h',value)
            if group == 'rmhg':
                struct.pack_into('>I', payload, 16, 7)  # Two default MCC-only categories have no retail counterpart.
            c = i.registry.cache
            matg = next(t['offset'] for t in c.tags.values() if t['group'] == 'matg')
            materials = field(ET.parse(i.reference / 'plugins/matg.xml').getroot(), 'Materials')
            target_strings = StringTable(c)
            names = {native_name: index for index, native_name in enumerate(
                target_strings.text(c.u(row)) for row in c.block(matg + int(materials.get('offset'), 0),
                                                               int(materials.get('elementSize'), 0)))}
            for index in range(4 if group == 'rmtr' else 0):
                material = i.source_strings.text(s.u(root + 64 + index * 4))
                if not material:
                    struct.pack_into('>h', payload, 80 + index * 2, -1)
                    continue
                if material not in names:
                    raise ValueError(f'Terrain physics material missing in retail globals: {material}')
                struct.pack_into('>h', payload, 80 + index * 2, names[material])
            owner, _ = i.registry.newtag(group, payload)
            self.done[datum] = (group, owner)
            i.materials.report.append({'source': s.name(datum & 65535), 'retail_template': template_name,
                'native_donor': donors[variant], 'source_template_variant': source_variant, 'fallback_template_variant': fallback,
                'approximation': bool(fallback or overlays or suppressed_specular or omitted_constants),
                'ambient_prt_two_layer_mapping': prt_two_layer,
                'inactive_third_layer_blue_zeroed': prt_two_layer,
                'difference': ('Terrain UV animation frozen at authored initial transform' if group == 'rmtr'
                               else 'Hologram color/brightness/UV functions frozen at authored constant values') if overlays else None,
                'frozen_inputs': sorted({i.source_strings.text(s.u(row + 4)) for row in overlays if s.u(row + 4)}),
                'textures_imported': len(textures) // 24, 'all_layer_parameters_preserved': not suppressed_specular,
                'terrain_specular_suppressed': suppressed_specular,
                'unused_mcc_environment_constants_omitted': omitted_constants, 'native_constant_defaults': float_defaults})
            return self.done[datum]
        except Exception:
            i.failed = True
            raise
        finally:
            donor.close()
