"""Import textures and named material parameters through native retail shaders.

Compiled MCC shaders are never copied. Unavailable variants use the existing
proof's retail templates and report every unrepresented parameter explicitly.
"""
import hashlib
import struct
from mcc_bitmap_source import BitmapSource
from encode_bitmap import encode_bitmap_base
from string_ids import StringTable
from powerhouse_materials import NATIVE_VARIANTS as POWERHOUSE_NATIVE_VARIANTS
from powerhouse_materials import NATIVE_OBJECT_VARIANTS as POWERHOUSE_NATIVE_OBJECT_VARIANTS

# Explicit, reported proof-of-concept substitutions for absent disc variants.
PARTICLE_ALIASES = {
    '_5_10_0_2_0_1_0_1_0_0': ('_5_10_0_2_0_1_1_1_0_0', 'neutral_black_point', 'Native lit soft smoke with verified constant-zero black point'),
    '_1_8_0_0_1_1_0_0_0_0': ('_1_8_0_0_1_1_1_0_0_0', 'neutral_black_point', 'Native soft-smoke LDR/depth-fade shader with verified constant-zero black point'),
    '_3_8_0_0_1_1_0_0_0_0': ('_3_8_0_0_1_1_1_0_0_0', 'neutral_black_point', 'Native snow shader with verified constant-zero black point; authored LDR rendering and depth fade retained'),
    '_1_3_0_0_0_0_0_1_0_0': ('_1_3_0_0_0_0_1_1_0_0', 'neutral_black_point', 'Native black-point support with verified constant-zero emitter values; authored alpha/fog retained'),
    '_0_10_0_0_1_0_1_1_0_0': ('_0_10_0_0_0_0_1_1_0_0', 'render_targets', 'LDR-only becomes LDR and HDR'),
    '_1_10_0_0_0_1_1_1_0_0': ('_1_3_0_0_0_1_1_1_0_0', 'blend_mode', 'Premultiplied alpha becomes alpha blend'),
}
DECAL_ALIASES = {
    '_3_3_0_0_1_1': ('_0_3_0_0_1_1', 'combined_alpha', 'Separate alpha combined with native bump and unmodulated tint retained'),
    '_6_3_0_0_1_1': ('_0_3_0_0_1_1', 'combined_alpha', 'Unit-tiled mask combined with native bump and unmodulated tint retained'),
    '_6_3_0_1_0_2': ('_0_3_0_1_0_1', 'combined_alpha', 'Verified zero modulation uses native unmodulated tint; unit-tiled alpha combined and specular behavior retained'),
    '_3_3_0_0_0_1': ('_0_3_0_0_0_3', 'combined_alpha', 'Static unmodulated tint baked in linear color; native unit tint preserves authored intensity'),
    '_6_3_0_0_0_1': ('_0_3_0_0_0_3', 'combined_alpha', 'Static unit-tiled mask and unmodulated tint baked in linear color; native unit tint preserves intensity'),
    '_3_3_0_0_0_2': ('_0_3_0_0_0_3', 'combined_alpha', 'Guarded endpoint modulation maps to native fully modulated tint; grayscale unmodulated tint folds into intensity'),
    '_3_3_0_0_0_3': ('_0_3_0_0_0_3', 'combined_alpha', 'Diffuse and alpha combined with native fully modulated tint retained; identical bindings reuse the source bitmap'),
    '_3_3_0_0_1_0': ('_0_3_0_0_1_0', 'combined_alpha', 'Authored BC color/alpha blocks joined without recompression at common mip levels; RGB shares alpha clamp addressing at decal edges'),
    '_3_3_0_1_1_0': ('_6_3_0_1_1_0', 'untiled_alpha', 'Unit tiling and nonsprite alpha make native untiled-mask sampling equivalent; separate textures and bump retained'),
    '_3_2_0_1_1_0': ('_0_2_0_1_1_0', 'identical_alpha', 'Separate diffuse/alpha samples use identical bitmap and sampler; native diffuse RGBA retains multiply, specular and bump behavior'),
    '_6_3_0_0_1_0': ('_0_3_0_0_1_0', 'albedo', 'Untiled alpha mask is combined with the diffuse using the validated decal-mask adapter; no tint or bump change'),
    '_0_0_0_0_0_0': ('_0_3_0_0_0_0', 'opaque_alpha', 'Opaque diffuse uses native alpha blend with a private fully opaque texture; pre-lighting and untouched specular/bump retained'),
    '_0_3_0_1_1_3': ('_0_3_0_1_1_1', 'tinting', 'Fully modulated tint becomes unmodulated tint'),
    '_0_3_2_1_1_0': ('_0_3_0_1_1_0', 'render_pass', 'MCC transparent pass becomes retail pre-lighting pass'),
    '_6_3_0_1_1_1': ('_0_3_0_1_1_1', 'albedo', 'Identical untiled alpha mask uses base-map alpha'),
    '_6_3_0_1_1_3': ('_0_3_0_1_1_1', 'albedo', 'Identical untiled alpha mask uses base-map alpha; fully modulated tint becomes unmodulated'),
    '_6_3_2_1_1_3': ('_0_3_0_1_1_1', 'albedo', 'Identical untiled alpha mask uses base-map alpha; tint becomes unmodulated and pass becomes pre-lighting'),
}


class MaterialImporter:
    def __init__(self, source, registry):
        self.source, self.registry = source, registry
        self.target, self.builder = registry.cache, registry.builder
        self.bitmaps = BitmapSource(source)
        self.source_strings, self.target_strings = StringTable(source), StringTable(self.target)
        self.done = {}
        self.report = []
        self.bitmap_preservation = []
        self._bitmap_encodings = {}
        self.particle_aliases = {}
        self.native_effect_post = None
        self.native_bitmaps = None
        self.target_names = {(t['group'], self.target.name(i)): (t['salt'] << 16) | i
                             for i, t in self.target.tags.items()}

    def encode_bitmap(self, source, tag, index=0, **options):
        """Keep the authored base and every mip; old size caps cannot select data.

        Material-specific channel/format transformations remain explicit. A
        derived source is identified as such rather than called an original
        pixel copy. Native file/residency limits are checked on the final cache.
        """
        info = source.info(tag)[index]
        # These legacy switches selected/resized levels. The preservation path
        # supersedes them, not the explicit zero-blue/opaque-alpha adapters.
        options.pop('max_dimension', None)
        options.pop('resize_blend', None)
        options['preserve_authored_mips'] = True
        options['max_dimension'] = max(info['width'], info['height'])
        encoded = encode_bitmap_base(source, tag, index=index, **options)
        self.remember_bitmap_encoding(source, tag, index, encoded,
            transforms=[name for name in ('zero_blue', 'opaque_alpha') if options.get(name)])
        return encoded

    def remember_bitmap_encoding(self, source, tag, index, encoded, transforms=()):
        record, control, raw = encoded
        info = source.info(tag)[index]
        width, height = struct.unpack_from('>HH', record, 4)
        if (width, height, record[20]+1) != (info['width'], info['height'], info['mips']):
            raise ValueError('Encoded bitmap lost authored base dimensions or mip levels')
        kind, fmt = struct.unpack_from('>HH', record, 10)
        from encode_bitmap import texture_gpu_format
        if (struct.unpack_from('>HH', control, 40) != (width, height)
                or control[45:47] != bytes((info['mips'], kind))
                or struct.unpack_from('>I', control, 48)[0] != texture_gpu_format(fmt, record[21])
                or struct.unpack_from('>I', control, 0)[0] != len(raw)
                or struct.unpack_from('>I', record, 28)[0] != len(raw)):
            raise ValueError('Encoded bitmap control disagrees with image metadata/payload')
        transforms = list(transforms)
        if info['format'] == 29:
            transforms.append('V16U16 signed components quantized to native V8U8 per authored mip')
        elif info['format'] == 33:
            transforms.append('MCC signed DXN endpoints biased to native unsigned storage; selectors retained')
        elif info['format'] in (0, 1, 3, 10):
            transforms.append('Source channels expanded to native ARGB32 per authored mip')
        cache = getattr(source, 'c', None)
        name = cache.name(tag) if cache is not None and tag in cache.tags else None
        note = dict(source=name, source_tag=tag, source_image=index,
            derived_input=source is not self.bitmaps,
            input={k: info[k] for k in ('width', 'height', 'format', 'mips')},
            output=dict(width=width, height=height, format=struct.unpack_from('>H', record, 12)[0],
                        mips=record[20]+1, kind=struct.unpack_from('>H', record, 10)[0]),
            input_payload_sha256=hashlib.sha256(source.pixels(tag, index)).hexdigest(),
            tiled_payload_sha256=hashlib.sha256(raw).hexdigest(), tiled_bytes=len(raw),
            explicit_channel_transforms=transforms, authored_levels_retained=True,
            verification='Encoder shape/control validation; independent serialized pixel verification is separate')
        key = (record, control, note['tiled_payload_sha256'])
        self._bitmap_encodings.setdefault(key, []).append(note)

    def record_bitmap_resource(self, record, control, raw, owner, resource, index=0):
        key = (record, control, hashlib.sha256(raw).hexdigest())
        pending = getattr(self, '_bitmap_encodings', {}).get(key, [])
        if pending:
            note = pending.pop(0)
            note.update(owner_datum=owner, resource_datum=resource, output_image=index)
            self.bitmap_preservation.append(note)

    def bitmap_preservation_report(self, resource_compaction=None):
        mapping = (resource_compaction or {}).get('old_to_new')
        result = []
        for note in self.bitmap_preservation:
            row = dict(note)
            staged = row['resource_datum']
            row['staged_resource_datum'] = staged
            if mapping is not None:
                index = mapping.get(str(staged & 65535))
                row['resource_datum'] = None if index is None else (staged & 0xffff0000) | index
            row['retained'] = row['resource_datum'] is not None
            result.append(row)
        return result

    def remember_composite_bitmap(self, tags, encoded, mode):
        """Report derived material textures separately from direct mip copies."""
        record, control, raw = encoded
        inputs = [self.bitmaps.info(tag)[0] for tag in tags]
        note = dict(source=[self.source.name(tag) for tag in tags], source_tags=list(tags),
            source_image=0, derived_input=True, composition=mode,
            input=[{k: info[k] for k in ('width', 'height', 'format', 'mips')} for info in inputs],
            output=dict(width=struct.unpack_from('>H', record, 4)[0],
                        height=struct.unpack_from('>H', record, 6)[0],
                        format=struct.unpack_from('>H', record, 12)[0],
                        mips=record[20]+1, kind=struct.unpack_from('>H', record, 10)[0]),
            input_payload_sha256=[hashlib.sha256(self.bitmaps.pixels(tag)).hexdigest() for tag in tags],
            tiled_payload_sha256=hashlib.sha256(raw).hexdigest(), tiled_bytes=len(raw),
            difference='Derived material composition, not an unchanged copy of either source bitmap; no generic size cap or mip-tail removal.')
        key = (record, control, note['tiled_payload_sha256'])
        self._bitmap_encodings.setdefault(key, []).append(note)

    def bitmap(self, datum):
        s, c, b = self.source, self.target, self.builder
        tag = datum & 65535
        key = ('bitm', s.name(tag))
        if key in self.done:
            return self.done[key]
        from native_linear_gray import recover as recover_linear_gray
        recovered = recover_linear_gray(self, key)
        if recovered is not None:
            return recovered
        native_assets = getattr(self, 'native_assets', None)
        if native_assets is not None:
            native = native_assets.import_named(key)
            if native is not None:
                return native[1]
        if key in self.target_names:
            return self.target_names[key]
        if self.native_bitmaps is not None:
            native = self.native_bitmaps.bitmap(key[1])
            if native is not None:
                self.done[key] = native
                return native
        rows = s.block(s.tags[tag]['offset'] + 0x60, 0x38)
        from sky_bridge_screen_mips import import_bitmap as import_sky_screen_bitmap
        screen_bitmap = import_sky_screen_bitmap(self, tag)
        if screen_bitmap is not None:
            return screen_bitmap
        if rows and all(s.unpack('H', row + 10)[0] == 2 for row in rows) and key[1] != r'levels\multi\snowbound\bitmaps\cube_icecave_a_cubemap':
            from encode_bitmap import encode_cubemap_base
            root = bytearray(0xa4)
            struct.pack_into('>H', root, 4, 0x50)
            owner, address = self.registry.newtag('bitm', root)
            records, resources = bytearray(), bytearray()
            for index in range(len(rows)):
                info = self.bitmaps.info(tag)[index]
                record, control, raw = encode_cubemap_base(self.bitmaps, tag, index,
                    max_dimension=max(info['width'], info['height']), preserve_authored_mips=True)
                self.remember_bitmap_encoding(self.bitmaps, tag, index, (record, control, raw))
                resource = self.registry.add_resource(owner, 'bitmap_texture_interop_resource',
                    {'control': control, 'raw': raw, 'root': 52,
                     'fixups': [(12, 0x40000000), (52, 0x20000000)], 'interops': [(0x20000034, 2)]})
                self.record_bitmap_resource(record, control, raw, owner, resource, index)
                records.extend(record); resources.extend(struct.pack('>II', resource, 0))
            b.put(address + 96, 'III', len(rows), b.alloc(records), 0)
            b.put(address + 140, 'III', len(rows), b.alloc(resources), 0)
            self.done[key] = owner
            self.report.append({'source': key[1], 'approximation': False, 'cubemap_images': len(rows),
                                'difference': 'All six authored reflection faces, original base resolution and every authored mip retained.'})
            return owner
        if len(rows) == 1 and s.unpack('H', rows[0] + 10)[0] == 2 and self.native_effect_post is not None:
            owner = self.native_effect_post.cubemap(key[1])
            self.done[key] = owner
            self.report.append({'source': key[1], 'native_bitmap_donor': 'snowbound.map',
                                'approximation': True,
                                'difference': 'Original-disc cubemap replaces same-named MCC cubemap.'})
            return owner
        from missing_color_mips import NAMES as missing_color_mip_names
        if key[1] in missing_color_mip_names:
            from missing_color_mips import encode
            owner = self.bitmap_resource(*encode(self.bitmaps, tag))
            self.done[key] = owner
            self.report.append({'source':key[1], 'approximation':True,
                'difference':'Missing diffuse mip chain generated by linear-color filtering to 512px BC1.'})
            return owner
        max_dimension = getattr(self, 'bitmap_size_overrides', {}).get(key[1], 512)
        from dune_sky_bitmap import resolution as dune_sky_resolution
        dune_resolution = dune_sky_resolution(s, key[1], self.bitmaps, tag)
        if dune_resolution is not None:
            max_dimension = dune_resolution
        if (str(s.file.name).replace('\\', '/').endswith('/s3d_sky_bridgenew.map')
                and key[1] == r'levels\multi\s3d_sky_bridgenew\sky\bitmaps\sky_transport_fl_01'):
            info = self.bitmaps.info(tag)
            if len(info) != 1 or (info[0]['width'], info[0]['height'], info[0]['format'], info[0]['mips']) != (4096,16,16,3):
                raise ValueError('Sky Bridge transport strip layout changed')
            max_dimension = 4096
        powerhouse_thunderhead = (
            str(s.file.name).replace('\\', '/').rsplit('/', 1)[-1] == 's3d_powerhouse.map'
            and key[1] == r'levels\multi\s3d_powerhouse\sky_settlement\bitmaps\thunderhead')
        if powerhouse_thunderhead:
            info = self.bitmaps.info(tag)
            if len(info) != 1 or (info[0]['width'], info[0]['height'], info[0]['format'], info[0]['mips']) != (1024, 512, 14, 11):
                raise ValueError('Powerhouse thunderhead texture changed; re-audit its native budget')
            # This sky layer fills much of the view. Preserve its authored BC1
            # base level instead of discarding it under the general 512px cap.
            max_dimension = 1024
        try:
            if not rows or (len(rows)>1 and s.u(s.tags[tag]['offset']+84)):
                raise ValueError('Empty or multi-image sprite bitmap needs its dedicated adapter')
            encoded_images = [self.encode_bitmap(self.bitmaps, tag, index=index, max_dimension=max_dimension,
                    resize_blend=getattr(self, 'resize_blend_maps', False) and 'blend' in key[1],
                    zero_blue=key[1] in getattr(self, 'zero_blue_blend_maps', set()),
                    preserve_normal_mips=getattr(self, 'preserve_normal_mips', True),
                    preserve_bc_mips=getattr(self, 'preserve_bc_mips', True) or key[1] in getattr(self, 'preserve_bc_mip_names', set()))
                for index in range(len(rows))]
        except ValueError as error:
            raise ValueError(f'bitm:{key[1]}: {error}') from error
        owner = self.bitmap_resources(encoded_images)
        self.done[key] = owner
        if len(rows)>1:
            self.report.append(dict(source=key[1], authored_images_retained=len(rows),
                difference='Every image and its full authored mip chain retained in original image-index order.'))
        if dune_resolution is not None:
            self.report.append({'source': key[1], 'approximation': False,
                'difference': 'Audited Dune sky retains authored 2048x2048 ARGB32 single mip; no invented mip or downsampling.',
                'authored_resolution': [2048, 2048], 'resource_bytes': sum(len(raw) for _,_,raw in encoded_images)})
        return owner

    def bitmap_resource(self, record, control, raw):
        return self.bitmap_resources([(record, control, raw)])

    def bitmap_resources(self, encoded_images):
        c, b = self.target, self.builder
        if not encoded_images:
            raise ValueError('Cannot create an empty bitmap image table')
        # Explicit runtime root: resource-backed and sampleable.
        # All editor data, sequences and runtime pointers start empty. These
        # are the same non-pointer fields as the accepted bitmap prototype.
        root = bytearray(0xa4)
        struct.pack_into('>H', root, 4, 0x50)
        owner, address = self.registry.newtag('bitm', root)
        records, hardware = bytearray(), bytearray()
        for index, (record, control, raw) in enumerate(encoded_images):
            resource = self.registry.add_resource(owner, 'bitmap_texture_interop_resource',
                {'control': control, 'raw': raw, 'root': 52,
                 'fixups': [(12, 0x40000000), (52, 0x20000000)],
                 'interops': [(0x20000034, 2)]})
            records.extend(record); hardware.extend(struct.pack('>II', resource, 0))
            self.record_bitmap_resource(record, control, raw, owner, resource, index)
        b.put(address + 0x60, 'III', len(encoded_images), b.alloc(records), 0)
        b.put(address + 0x8c, 'III', len(encoded_images), b.alloc(hardware), 0)
        b.put(address + 0x98, 'III', 0, 0, 0)
        return owner

    def parameters(self, cache, strings, post):
        template = cache.tags[cache.u(post + 12) & 65535]
        if template['group'] != 'rmt2':
            raise ValueError('Shader postprocess has no render-method template')
        offset = template['offset']
        return ([strings.text(cache.u(x)) for x in cache.block(offset + 0x6c, 4)],
                [strings.text(cache.u(x)) for x in cache.block(offset + 0x48, 4)])

    def disc_shader_templates(self):
        """Names of every shader template on the original disc maps (cached)."""
        if getattr(self, '_disc_shader_templates', None) is None:
            from cache_reader import Cache as _Cache
            from pathlib import Path
            names = set()
            for candidate in sorted(Path(self.native_effect_post.disc_maps).glob('*.map')):
                if candidate.name in ('shared.map', 'campaign.map'):
                    continue
                cache = _Cache(str(candidate))
                try:
                    names |= {cache.name(i) for i, t in cache.tags.items() if t['group'] == 'rmt2'}
                finally:
                    cache.close()
            self._disc_shader_templates = names
        return self._disc_shader_templates

    def shader(self, datum):
        s, c, b = self.source, self.target, self.builder
        tag = s.tags[datum & 65535]
        if tag['group'] not in ('rmsh', 'rmfl'):
            raise ValueError(f"Material class requires dedicated handling: {tag['group']}")
        key = tag['group'], s.name(datum & 65535)
        if key in self.done:
            return 'rmsh', self.done[key]
        native_assets = getattr(self, 'native_assets', None)
        if native_assets is not None:
            if (getattr(self, 'battle_canyon_rebuilt', False) and
                    key == ('rmsh', r'levels\shared\shaders\multi\mp_glass')):
                # Use the shipping H3 window equivalent for kit-only glass.
                native = native_assets.import_named(('rmsh',
                    r'levels\dlc\ghosttown\shaders\glass_factory_window'))
                if native is None:
                    raise ValueError('Required original H3 glass donor is absent')
                self.report.append({'source': key[1], 'native_material_donor':
                    r'levels\dlc\ghosttown\shaders\glass_factory_window',
                    'reason': 'Stock H3 window equivalent for generic authoring-kit glass'})
                return native
            native = native_assets.import_named(key)
            if native is not None:
                return native
        source_post = s.block(tag['offset'] + 40, 140)[0]
        texture_names, constant_names = self.parameters(s, self.source_strings, source_post)
        source_textures = s.block(source_post + 16, 28)
        source_constants = s.block(source_post + 28, 16)
        if len(texture_names) != len(source_textures) or len(constant_names) != len(source_constants):
            raise ValueError('Source material parameter counts differ from its template')
        options = [s.unpack('h', x)[0] for x in s.block(tag['offset'] + 16, 2)]
        alpha = tag['group'] == 'rmfl' or (len(options) > 2 and options[2] == 1)
        template_name = (r'objects\weapons\lod\shaders\lod_plasma_grenade' if alpha
                         else getattr(self, 'opaque_prototype', r'levels\dlc\lockout\shaders\metal_wall_white_flat'))
        native = self.target_names.get(('rmsh', template_name))
        if native is None:
            raise ValueError(f'Required native material prototype absent: {template_name}')
        template_id = native & 65535
        retail = c.tags[template_id]['offset']
        post = c.block(retail + 40, 132)[0]
        target_texture_names, target_constant_names = self.parameters(c, self.target_strings, post)
        textures = bytearray(b''.join(c.data[x:x + 24] for x in c.block(post + 16, 24)))
        constants = bytearray(b''.join(c.data[x:x + 16] for x in c.block(post + 28, 16)))
        sky_template = None
        forge_sky_alias = None
        prisoner_template = False
        powerhouse_wire = False
        powerhouse_wire_report = None
        half_detail_strength = False
        fused_ridge_detail = False
        fused_small_rock_detail = False
        detail_strength_report = None
        reach_scenery_template = False
        forge_environment_template = (key[1].startswith(r'levels\multi\forge_halo\shaders\forge_halo_forerunner_')
                                      and not key[1].endswith('_glass')) or key[1] in {
            r'levels\multi\forge_halo\shaders\forge_driftwood_bark',
            *[r'levels\multi\forge_halo\shaders\water\forge_halo_waterfall_' + part
              for part in ('upper_small', 'upper_big', 'lower_small', 'lower_big')],
        }
        neutral_bump = False
        battle_static_environment = False
        static_cube_routes = 0
        forge_primary_color = False
        forge_primary_routes = []
        neutral_diffuse_specular_mask = False
        disabled_extra_environment = False
        chiron_opaque_emission = False
        boarding_sky_emission = None
        boarding_metal = None
        boarding_metal_bitmap = None
        authored_conveyor = key[1] == r'levels\multi\h2_elongation\shaders\elongation_conveyor_pro'
        from installed_materials import EMISSION_TEMPLATES
        correction_sources = {'cex_beavercreek.map', 'rodentia.map', 'lockoutfix.map',
                              'h2_elongation.map', 'sancr.map'}
        source_filename = str(s.file.name).replace('\\', '/').rsplit('/', 1)[-1]
        autoturret_emission = (source_filename in correction_sources and
                              key[1] == r'objects\equipment\shaders\autoturret')
        animation_aliases = ({'normal_specular_tint': 'specular_tint',
                              'glancing_specular_tint': 'fresnel_color'}
                             if autoturret_emission else {})
        gravlift_emission = (source_filename == 'cex_beavercreek.map' and key[1] ==
            r'objects\levels\multi\20_sword_slayer\sword_grav_lift_c\shaders\gravlift_vapor_shell_oni')
        gravlift_scale = None
        if gravlift_emission:
            animation_aliases = {'self_illum_detail_map': 'self_illum_map'}
        authored_emission_template = (EMISSION_TEMPLATES.get(key[1])
                                     if source_filename in correction_sources else None)
        elongation_unmasked_emission = (source_filename == 'h2_elongation.map' and
            key[1] in {r'levels\multi\h2_elongation\shaders' + '\\' + name
                       for name in ('panel_mech_strips_hazard_stripe',
                                    'panel_tech_rack', 'light_halogen')})
        rodentia_diffuse_emission = (source_filename == 'rodentia.map' and
            key[1] in {r'blackandfan\levels\multi\rodentia\shaders' + '\\' + name
                       for name in ('forerunner_fluorescent_bloom',
                                    'forerunner_fluorescent_bloom_cyan')})
        lockout_neutral_emission_detail = (source_filename == 'lockoutfix.map' and
            key[1] == r'levels\multi\lockoutfix\shaders\guardian_light_circle_flicker')
        lockout_composed_panel_normal = (source_filename == 'lockoutfix.map' and
            key[1] == r'levels\multi\lockoutfix\shaders\guardian_centerplatform_metalunderglass')
        lockout_stock_lighting = None
        if source_filename == 'lockoutfix.map':
            lockout_stock_lighting = {
                r'levels\multi\lockoutfix\shaders\panel_elevator_unlit':
                    ('_8_1_0_1_7_2_1_0_2_0', '_8_1_0_1_2_2_1_0_2_0',
                     'chill.map', r'levels\multi\chill\shaders\panel_elevator'),
                r'levels\multi\lockoutfix\shaders\panel_elevator':
                    ('_8_1_0_1_7_1_1_0_2_0', '_8_1_0_1_2_2_1_0_2_0',
                     'chill.map', r'levels\multi\chill\shaders\panel_elevator'),
                r'levels\multi\lockoutfix\shaders\guardian_light_circle_lift':
                    ('_0_2_0_1_7_1_1_0_1_0', '_0_2_0_1_2_1_1_0_1_0',
                     'guardian.map', r'levels\multi\guardian\shaders\guardian_light_circle_lift'),
            }.get(key[1])
        boarding_opaque_emission = (getattr(self, 'boarding_action', False) and
                                   key[1] == r'custom\levels\multiplayer\shaders\bloodgulch_light_blue')
        chiron_surface = (getattr(self, 'chiron_materials', False) and
                          (key[1].startswith(r'custom\levels\multiplayer' + '\\') or
                           key[1] == r'custom\objects\scen\mp_obj\hce_tele_flat_wide\shaders\teleporter_shield'))
        if ((getattr(self, 'prisoner_materials', False)
                and key[1].startswith(r'custom\levels\multiplayer\prisoner\shaders' + '\\')) or chiron_surface or boarding_opaque_emission or authored_conveyor or authored_emission_template or elongation_unmasked_emission or rodentia_diffuse_emission or lockout_neutral_emission_detail or lockout_composed_panel_normal or lockout_stock_lighting or autoturret_emission or gravlift_emission):
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            # Verified native H3 variants. MCC adds three default trailing
            # options; the first ten retain their original H3 meanings.
            exact = {'_0_2_0_1_1_0_0_0_0_0', '_0_0_0_0_0_0_1_3_0_0',
                     '_0_1_0_2_5_2_0_3_0_0', '_0_0_0_0_0_0_4_3_0_0'}
            if authored_conveyor:
                # Present on the original Last Resort disc cache. Preserve
                # parallax/height-map routing as well as all scrolling layers.
                exact.add('_0_1_0_1_1_2_0_0_1_0')
            if chiron_surface:
                exact.update({'_0_0_0_0_0_0_4_0_0_0',
                              '_0_0_0_0_0_0_1_0_0_0',
                              '_2_0_0_0_0_0_3_1_0_0'})
            suffix = '_' + '_'.join(str(v) for v in variants[:10])
            if gravlift_emission:
                if variants != [7,0,0,0,4,0,5,3,0,0,0,1,0]:
                    raise ValueError('Gravlift source options changed')
                for name in ('soft_fresnel_power','soft_z_range'):
                    if s.unpack('4f',source_constants[constant_names.index(name)]) != (0.,)*4:
                        raise ValueError('Gravlift soft fade is not neutral')
                from gravlift_material import uniform_emission_scale
                constant_tag = s.u(source_textures[texture_names.index('self_illum_map')]+12)&65535
                gravlift_scale = uniform_emission_scale(self.bitmaps, constant_tag)
                variants = [7,0,0,0,0,0,1,3,0,0,0,0,0]
                suffix = '_7_0_0_0_0_0_1_3_0_0'
                exact.add(suffix)
            if autoturret_emission:
                if len(variants) != 13 or any(variants[10:]) or suffix != '_3_2_0_1_2_2_1_0_0_1':
                    raise ValueError('Autoturret source material options changed')
                # Native Armory retains change-color, both normal layers and
                # animated illumination. Its Cook-Torrance highlight is an
                # explicit approximation of the source two-lobe highlight.
                variants[4] = 1
                suffix = '_3_2_0_1_1_2_1_0_0_1'
                exact.add(suffix)
            if lockout_stock_lighting:
                expected, native, donor_file, donor_material = lockout_stock_lighting
                if len(variants)!=13 or any(variants[10:]) or suffix!=expected:
                    raise ValueError('Lockout stock-lighting source options changed')
                # Reuse the original H3 surface's lighting model and its own
                # specular parameters, not arbitrary defaults from another
                # material sharing the permutation. Authored textures, colors,
                # parallax and emission animations remain name-mapped below.
                battle_static_environment = variants[5]==1 and int(native.split('_')[6])==2
                variants[:10]=[int(v) for v in native.split('_')[1:]]
                suffix=native
                exact.add(suffix)
            if lockout_composed_panel_normal:
                if len(variants)!=13 or any(variants[10:]) or suffix!='_0_2_0_1_7_2_5_0_0_0':
                    raise ValueError('Lockout center panel options changed')
                for name in ('bump_map','bump_detail_map'):
                    if s.unpack('4f',source_constants[constant_names.index(name)])!=(1.,1.,0.,0.):
                        raise ValueError('Lockout composed normals require identical unit UVs')
                    row=source_textures[texture_names.index(name)]
                    if s.unpack('h4BbBhH',row+16)[:5]!=(0,0,0,0,0):
                        raise ValueError('Lockout composed normals require default wrap sampling')
                normal_indices={constant_names.index(n) for n in ('bump_map','bump_detail_map','bump_detail_coefficient')}
                if any(s.unpack('HBB',r)[2] in normal_indices for r in s.block(source_post+80,4)):
                    raise ValueError('Cannot precompose animated normal inputs')
                variants[1]=1
                suffix='_0_1_0_1_7_2_5_0_0_0'
                exact.add(suffix)
            if lockout_neutral_emission_detail:
                if len(variants) != 13 or any(variants[10:]) or suffix != '_0_2_0_1_2_2_1_0_1_0':
                    raise ValueError('Lockout flickering light options changed')
                if s.u(source_post + 40) or s.u(source_post + 52):
                    raise ValueError('Lockout flickering light has unreviewed material switches')
                # Retail descent has the same permutation with detail emission.
                # Its illum_detail rmop explicitly defaults the added sampler to
                # default_detail. Keep the authored color animation and all
                # surface/parallax options; add only that neutral detail input.
                variants[6] = 5
                suffix = '_0_2_0_1_2_2_5_0_1_0'
                exact.add(suffix)
            if rodentia_diffuse_emission:
                if len(variants) != 13 or any(variants[10:]) or suffix != '_0_1_0_0_0_0_2_0_0_0':
                    raise ValueError('Rodentia three-channel light material changed')
                if s.u(source_post + 40) or s.u(source_post + 52):
                    raise ValueError('Rodentia diffuse light has unreviewed material switches')
                # Native armory shader retains bump, channel colors and animated
                # channel_a. Unit diffuse and zero specular below reduce its
                # two-lobe material to the source diffuse-only calculation.
                # Diffuse alpha masking then has no effect (specular is zero).
                variants[3], variants[4] = 1, 2
                suffix = '_0_1_0_1_2_0_2_0_0_0'
                exact.add(suffix)
            if elongation_unmasked_emission:
                if len(variants) != 13 or any(variants[10:]) or suffix != '_0_2_0_0_2_0_1_0_0_0':
                    raise ValueError('3longation unmasked emissive material changed')
                # Original-disc resupply_capsule shader has identical options
                # except diffuse-alpha specular masking. These opaque materials
                # do not otherwise consume base alpha; private opaque alpha
                # preserves their unmasked specular and restores self light.
                variants[3] = 1
                suffix = '_0_2_0_1_2_0_1_0_0_0'
                exact.add(suffix)
                neutral_diffuse_specular_mask = True
            if authored_emission_template:
                if (len(variants)!=13 or any(variants[10:]) or
                        source_template.rsplit('\\',1)[0]+'\\'+suffix != authored_emission_template):
                    raise ValueError('Audited installed-map emission options changed')
                exact.add(suffix)
            if (chiron_surface or boarding_opaque_emission) and suffix == '_0_0_0_0_0_0_4_0_0_0':
                # Disc inventory has diffuse-driven emission with alpha blending,
                # not the MCC opaque combination. An opaque private base alpha
                # retains the source's solid surface while using native emission.
                variants[7] = 3
                suffix = '_' + '_'.join(str(v) for v in variants[:10])
                chiron_opaque_emission = True
            if suffix == '_0_1_0_1_1_0_5_0_0_0':
                # H3 has this combination with environment mapping enabled.
                # A zero environment tint preserves the source's disabled
                # reflection while retaining its authored emission/detail.
                variants[5] = 2
                suffix = '_' + '_'.join(str(v) for v in variants[:10])
                exact.add(suffix)
                disabled_extra_environment = True
            if len(variants) == 13 and not any(variants[10:]) and suffix in exact:
                sky_template = source_template.rsplit('\\', 1)[0] + '\\' + suffix
                prisoner_template = True
        if getattr(self, 'resuscitation_sky', False) and '\\sky\\shaders\\' in key[1]:
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            if len(variants) != 13 or any(variants[10:]):
                raise ValueError('Sky has nondefault MCC-only shader options')
            if (key[1] == r'levels\multi\resuscitation\sky\shaders\terrain_desert'
                    and variants[:10] == [0, 2, 0, 0, 0, 0, 5, 0, 0, 0]):
                # The distant self-lit sky terrain has no native bump-detail
                # variant. Keep its authored emission with unbumped sky routing.
                variants[1] = 0
            sky_template = source_template.rsplit('\\', 1)[0] + '\\_' + '_'.join(str(v) for v in variants[:10])
        from foundation_sky import select_foundation_clouds, TARGET_OPTIONS
        foundation_clouds = select_foundation_clouds(s, key[1], options, texture_names, constant_names)
        if foundation_clouds:
            # diffuse_only.fx ignores the diffuse-alpha specular mask in all
            # static/PRT consumers; its analytical specular multiplier is zero.
            # Preserve blend5, alpha, RGB, UVs and authored animation routes.
            tm = s.tags[s.u(source_post + 12) & 65535]['offset']
            booleans = [self.source_strings.text(s.u(row)) for row in s.block(tm + 96, 4)]
            if s.u(source_post + 40) or s.u(source_post + 52) or s.u(tm + 84) or booleans != ['no_dynamic_lights']:
                raise ValueError('Foundation clouds switches require re-audit')
            variants = list(TARGET_OPTIONS)
            sky_template = r'shaders\shader_templates\_0_0_0_0_0_0_0_5_0_0'
            prisoner_template = True
        if getattr(self, 'forge_world_sky', False) and '\\sky_halo\\shaders\\' in key[1]:
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            if len(variants) != 13 or any(variants[10:]):
                raise ValueError('Forge sky has nondefault MCC-only shader options')
            suffix = '_' + '_'.join(str(v) for v in variants[:10])
            aliases = {
                '_7_0_0_0_4_0_4_3_0_0': '_7_0_0_0_0_0_4_3_0_0',
                '_0_0_0_0_4_0_4_3_0_0': '_0_0_0_0_0_0_4_3_0_0',
                '_2_0_0_0_4_0_1_0_0_0': '_2_0_0_0_0_0_1_0_0_0',
                '_5_4_0_0_0_0_0_0_0_0': '_5_2_0_0_0_0_0_0_0_0',
                '_5_4_0_1_0_0_5_0_0_0': '_0_0_0_1_0_0_5_0_0_0',
            }
            if suffix in aliases:
                forge_sky_alias = {'source': suffix, 'target': aliases[suffix],
                                   'note': 'Explicit native sky material/bump approximation; blend mode preserved'}
                suffix = aliases[suffix]
                variants[:10] = [int(v) for v in suffix.split('_')[1:]]
            sky_template = source_template.rsplit('\\', 1)[0] + '\\' + suffix
        if key[1].startswith('objects\\levels\\forge\\shaders\\') or forge_environment_template:
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\',1)[-1].split('_')[1:]]
            if len(variants) != 13 or any(variants[10:]):
                raise ValueError('Reach scenery has non-default MCC-only shader options')
            suffix = '_'+'_'.join(map(str,variants[:10]))
            # Original disc inventory: retain material, reflection and blend
            # options. Missing no-bump combinations use native neutral normals.
            aliases = {
                '_0_0_0_0_2_2_0_0_0_0': '_0_2_0_0_2_2_0_0_0_0',
                '_7_0_0_1_2_1_0_0_0_0': '_7_1_0_1_2_1_0_0_0_0',
                '_0_2_0_2_2_2_0_3_0_0': '_0_1_0_2_2_2_0_3_0_0',
            }
            if forge_environment_template and suffix == '_0_2_0_0_0_0_1_0_0_0':
                # Stock Cyberdyne's brute_target preserves diffuse lighting and
                # authored self illumination; only its bump detail is absent.
                aliases[suffix] = '_0_1_0_0_0_0_1_0_0_0'
            if suffix in aliases:
                neutral_bump = variants[1] == 0
                suffix = aliases[suffix]
                variants[:10] = [int(v) for v in suffix.split('_')[1:]]
            if (key[1] == r'objects\levels\forge\shaders\for_forge_gen_panel_04_dark_nocc'
                    and suffix == '_0_2_0_0_2_0_1_0_0_0'):
                # Stock resupply_capsule has the same bump/detail, lighting and
                # emission, plus diffuse-alpha specular masking. Its opaque
                # material does not otherwise consume alpha. A private white
                # alpha channel gives the source's unmasked specular exactly;
                # keep RGB and all other users of the source bitmap unchanged.
                suffix = '_0_2_0_1_2_0_1_0_0_0'
                variants[3] = 1
                neutral_diffuse_specular_mask = True
            sky_template = source_template.rsplit('\\',1)[0]+'\\'+suffix
            reach_scenery_template = not forge_environment_template
        if getattr(self, 'battle_canyon', False) and key[0] == 'rmsh' and key[1].startswith('levels\\multi\\cex_beavercreek\\'):
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            if len(variants) != 13 or any(variants[10:]):
                raise ValueError('Battle Canyon has nondefault MCC-only material options')
            suffix = '_' + '_'.join(map(str, variants[:10]))
            if key[1] in {
                    r'levels\multi\cex_beavercreek\shaders\ca_bcreek_forerunner_panel_circle_quarter',
                    r'levels\multi\cex_beavercreek\shaders\ca_bcreek_forerunner_panel_circle_quarter_red'}:
                if suffix != '_0_2_0_1_1_1_5_0_0_0':
                    raise ValueError('Battle Canyon circular-panel options changed')
                # Preserve the static reflection cube via explicit routing of
                # both native dynamic samplers, rather than discarding emission
                # or replacing Cook-Torrance with a different lighting model.
                variants[5] = 2
                suffix = '_0_2_0_1_1_2_5_0_0_0'
                battle_static_environment = True
            exact = {'_0_0_0_0_0_0_1_3_0_0', '_0_2_0_0_2_0_0_0_0_0', '_0_1_0_1_2_2_2_0_0_0', '_0_0_0_0_0_0_1_1_0_0', '_0_2_0_1_0_0_0_0_0_0', '_0_1_0_1_2_1_0_0_0_0', '_0_1_0_1_2_1_1_0_0_0', '_0_2_0_1_2_1_0_0_0_0', '_2_0_0_0_0_0_1_0_0_0', '_0_2_0_1_1_1_0_0_0_0', '_0_1_0_0_0_0_1_0_0_0', '_0_2_0_0_1_1_0_0_0_0', '_0_0_0_0_0_0_1_0_0_0', '_2_0_0_0_0_0_5_1_0_0', '_2_0_0_0_0_0_0_0_0_0', '_0_0_0_0_0_0_3_1_0_0', '_0_0_1_0_0_0_0_0_0_0', '_0_1_0_1_2_2_0_0_0_0', '_0_2_0_0_0_0_0_0_0_0', '_0_0_0_0_0_0_5_0_0_0', '_0_0_0_0_0_0_5_3_0_0', '_0_1_0_1_2_0_2_0_0_0', '_0_1_0_1_1_2_0_0_0_0', '_2_0_0_0_0_0_1_1_0_0', '_0_0_0_0_0_0_3_3_0_0', '_0_1_0_1_1_1_0_0_0_0', '_0_1_0_1_2_0_1_0_0_0', '_0_0_0_0_0_0_0_0_0_0', '_0_0_0_0_0_0_5_1_0_0', '_0_1_0_1_2_2_1_0_0_0'}
            if battle_static_environment:
                exact.add(suffix)
            aliases = {
                '_2_0_0_0_4_0_2_1_0_0': '_2_0_0_0_0_0_2_1_0_0',
                '_0_0_0_1_1_1_0_0_0_0': '_0_1_0_1_1_1_0_0_0_0',
                '_0_0_0_1_2_1_0_3_0_0': '_0_2_0_1_2_1_0_3_0_0',
                '_0_0_0_1_2_1_0_0_0_0': '_0_1_0_1_2_1_0_0_0_0',
            }
            if suffix in aliases:
                neutral_bump = variants[1] == 0 and int(aliases[suffix].split('_')[2]) != 0
                forge_sky_alias = {'source':suffix, 'target':aliases[suffix],
                                   'note':'Native material with neutral added normals or unlit emissive sky'}
                suffix = aliases[suffix]
                variants[:10] = [int(v) for v in suffix.split('_')[1:]]
                exact.add(suffix)
            if suffix in exact:
                sky_template = source_template.rsplit('\\', 1)[0] + '\\' + suffix
                prisoner_template = True
        if key[0] == 'rmsh' and key[1] in {
                'levels\\multi\\s3d_powerhouse\\shaders\\'+name for name in (
                    'sloped_rock_elements','valley_floor',
                    'strip_mine_facility','distant_mountains','strip_mine',
                    'ridge_rock','ridge_rock_v2','distant_ridge_rock',
                    'm35_small_rock_custom', *POWERHOUSE_NATIVE_VARIANTS)}:
            source_template=s.name(s.u(source_post+12)&65535)
            variants=[int(v) for v in source_template.rsplit('\\',1)[-1].split('_')[1:]]
            if len(variants)!=13 or any(variants[10:]):
                raise ValueError('Powerhouse sky terrain has nondefault MCC-only options')
            reviewed = POWERHOUSE_NATIVE_VARIANTS.get(key[1].rsplit('\\', 1)[-1])
            if reviewed is not None and reviewed != '_'+'_'.join(map(str,variants[:10])):
                raise ValueError('Powerhouse reviewed native material variant changed')
            if key[1].rsplit('\\', 1)[-1] in ('strip_mine', 'distant_ridge_rock'):
                # diffuse_only ignores specular_mask; environment mapping is
                # disabled. Native no-mask variant preserves all six textures.
                # See pinned HaloShaderGenerator diffuse_only.fx.
                if variants[:10] != [5,2,0,1,0,0,0,0,0,0]:
                    raise ValueError('Powerhouse strip-mine shader changed; re-audit required')
                variants[3] = 0
            if key[1].endswith('\\distant_ridge_rock'):
                coefficient = s.unpack('4f', source_constants[constant_names.index('bump_detail_coefficient')])
                normal_rows = [source_textures[texture_names.index(n)] for n in ('bump_map', 'bump_detail_map')]
                if coefficient != (2., 2., 2., 2.) or s.u(normal_rows[0]+12) != s.u(normal_rows[1]+12) or s.u(source_post+92):
                    raise ValueError('Powerhouse fused ridge inputs changed')
                for row in normal_rows:
                    image, address, filtering, comparison, external, transform, pad, animation, pad2 = s.unpack('h4BbBhH', row+16)
                    if image or address or filtering or comparison or external or pad or animation or pad2:
                        raise ValueError('Powerhouse fused ridge requires static default wrap sampling')
                fused_ridge_detail = True
            if key[1].rsplit('\\', 1)[-1] in ('ridge_rock', 'ridge_rock_v2'):
                if variants[:10] != [5,2,0,0,0,0,0,0,0,0]:
                    raise ValueError('Powerhouse ridge shader changed; re-audit required')
                coefficient = s.unpack('4f', source_constants[constant_names.index('bump_detail_coefficient')])
                if coefficient != (.5, .5, .5, .5):
                    raise ValueError('Powerhouse ridge needs authored half-strength detail')
                half_detail_strength = True
            if key[1].endswith('\\m35_small_rock_custom'):
                if variants[:10] != [0,2,0,1,1,0,0,0,0,0] or s.u(source_post+92):
                    raise ValueError('Small-rock native shader inputs changed')
                expected = {'bump_map': (1.,1.,0.,0.), 'bump_detail_map': (2.,1.,0.,0.),
                            'bump_detail_coefficient': (2.5,2.5,2.5,2.5)}
                for n,v in expected.items():
                    if s.unpack('4f', source_constants[constant_names.index(n)]) != v:
                        raise ValueError('Small-rock authored normal transform changed')
                for n in ('bump_map','bump_detail_map'):
                    row = source_textures[texture_names.index(n)]
                    image, address, filtering, comparison, external, transform, pad, animation, pad2 = s.unpack('h4BbBhH', row+16)
                    if image or address or filtering or comparison or external or pad or animation or pad2:
                        raise ValueError('Small-rock normal requires static wrap sampling')
                fused_small_rock_detail = True
            sky_template=source_template.rsplit('\\',1)[0]+'\\_'+'_'.join(map(str,variants[:10]))
            prisoner_template=True  # Shared strict native-material parameter path.
        if getattr(self, 'boarding_action', False):
            from boarding_action_materials import NATIVE_TEMPLATES
            if key[1] == r'custom\levels\multiplayer\shaders\metal_flat_generic':
                if not s.name(s.u(source_post+12)&65535).endswith('_0_2_0_0_10_2_0_0_0_1_0_0_0') or s.u(source_post+92):
                    raise ValueError('Boarding metal source variant or animation changed')
                from boarding_metal import prepare
                control = s.u(source_textures[texture_names.index('material_texture')]+12)&65535
                tint = s.u(source_textures[texture_names.index('spec_tint_map')]+12)&65535
                blend = s.unpack('4f',source_constants[constant_names.index('albedo_blend')])[0]
                environment = s.unpack('4f',source_constants[constant_names.index('environment_map_specular_contribution')])[0]
                baked, boarding_metal = prepare(self.bitmaps, control, tint, blend, environment)
                boarding_metal_bitmap = self.bitmap_resource(*self.encode_bitmap(baked,control,preserve_color_mips=True))
                variants = [0,2,0,1,1,2,0,0,0,1]
                sky_template = r'shaders\shader_templates\_0_2_0_1_1_2_0_0_0_1'
                prisoner_template = True
            if key[1] in (r'custom\skies\new_hce_skies\space\shaders\threshold',
                          r'custom\skies\new_hce_skies\space\shaders\basis'):
                from boarding_sky_emission import validate
                boarding_sky_emission = validate(s, self.bitmaps, source_post,
                    texture_names, source_textures, constant_names, source_constants)
                variants = [0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
                sky_template = r'shaders\shader_templates\_0_0_1_0_0_0_1_0_0_0'
                prisoner_template = True
            reviewed = NATIVE_TEMPLATES.get(key[1])
            if reviewed is not None:
                source_template = s.name(s.u(source_post + 12) & 65535)
                variants = [int(v) for v in source_template.rsplit(chr(92), 1)[-1].split('_')[1:]]
                expected = source_template.rsplit(chr(92), 1)[0] + chr(92) + '_' + '_'.join(map(str, variants[:10]))
                if len(variants) != 13 or any(variants[10:]) or expected != reviewed:
                    raise ValueError('Boarding Action reviewed native material changed')
                sky_template = reviewed
                prisoner_template = True
        if getattr(self, 'battle_canyon_rebuilt', False) and key[0] == 'rmsh':
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            if len(variants) != 13 or any(variants[10:]):
                raise ValueError('Rebuilt Battle Canyon has nondefault MCC-only material options')
            suffix = '_' + '_'.join(map(str, variants[:10]))
            # Original-disc inventory, not the generic metal prototype. Added
            # normal layers are neutral; an added reflection is zeroed below.
            aliases = {
                '_0_0_0_1_1_1_0_0_0_0': '_0_1_0_1_1_1_0_0_0_0',
                '_0_0_0_1_2_1_0_0_0_1': '_0_2_0_1_2_1_0_0_0_1',
                '_7_0_0_1_0_0_0_0_0_0': '_7_1_0_1_0_0_0_0_0_0',
                '_0_2_0_0_0_0_1_0_0_0': '_0_1_0_0_0_0_1_0_0_0',
                '_0_2_0_1_2_0_0_0_1_0': '_0_2_0_1_2_2_0_0_1_0',
            }
            if suffix in aliases:
                replacement = aliases[suffix]
                changed = list(map(int, replacement.split('_')[1:]))
                neutral_bump = variants[1] == 0 and changed[1] != 0
                disabled_extra_environment = variants[5] == 0 and changed[5] != 0
                forge_sky_alias = {'source': suffix, 'target': replacement,
                    'note': ('Base bump and emission retained; detail bump absent in shipping H3 permutation'
                             if variants[1] == 2 and changed[1] == 1 else
                             'Added normal layers are flat; added environment contribution is zero')}
                suffix = replacement
                variants[:10] = changed
            sky_template = source_template.rsplit('\\', 1)[0] + '\\' + suffix
            if source_template.startswith('shaders\\battle_canyon_forge_primary_templates\\'):
                if suffix != '_0_2_0_1_1_2_5_0_0_0':
                    raise ValueError('Unreviewed Forge primary-color shader permutation')
                sky_template = 'shaders\\shader_templates\\' + suffix
                forge_primary_color = True
            prisoner_template = True  # existing named constants/animation path
        if getattr(self, 'haven_draft', False) and key[0] == 'rmsh':
            # H3EK authors these drafts from existing stock H3 shader templates.
            # Reuse the established exact-template/parameter conversion path;
            # fail if an authored permutation has no original-disc counterpart.
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            if (not source_template.startswith('shaders\\shader_templates\\')
                    or len(variants) != 13 or any(variants[10:])):
                raise ValueError('Haven draft has unreviewed MCC-only material options')
            if variants[1] == 2 and 'bump_detail_coefficient' in constant_names:
                detail_strength = s.unpack('4f', source_constants[constant_names.index('bump_detail_coefficient')])
                if detail_strength == (0., 0., 0., 0.):
                    # This authored layer is disabled. Select shipping H3's
                    # base-normal-only permutation rather than enable detail.
                    variants[1] = 1
            sky_template = 'shaders\\shader_templates\\_' + '_'.join(map(str, variants[:10]))
            prisoner_template = True
        if (getattr(self, 'stock_materials', False) and not sky_template and key[0] == 'rmsh'
                and key[1].startswith('levels'+chr(92))):
            # Kit-authored level materials set to stock H3 option combinations:
            # reuse the exact-template/parameter path when the original disc has
            # that combination; otherwise keep the existing conversion.
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit(chr(92), 1)[-1].split('_')[1:]]
            if (source_template.startswith('shaders'+chr(92)+'shader_templates'+chr(92))
                    and len(variants) == 13 and not any(variants[10:])):
                candidate = chr(92).join(('shaders', 'shader_templates', '_' + '_'.join(map(str, variants[:10]))))
                if candidate in self.disc_shader_templates():
                    sky_template = candidate
                    prisoner_template = True
        powerhouse_lamp = (source_filename == 's3d_powerhouse.map' and key == (
            'rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_lamp_glass'))
        if powerhouse_lamp:
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_0_0_0_0_2_0_5_0_0_0_0_0_0'):
                raise ValueError('Powerhouse lamp shader changed; re-audit required')
            # Sidewinder has the same two-lobe lighting and detail emission,
            # with diffuse-alpha specular masking added. The source is opaque
            # and uses a separate emission mask: unit private base alpha makes
            # that extra specular mask neutral without changing source RGB.
            variants = [0, 0, 0, 1, 2, 0, 5, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_0_0_0_1_2_0_5_0_0_0'
            neutral_diffuse_specular_mask = True
            prisoner_template = True
        powerhouse_screen = (source_filename == 's3d_powerhouse.map' and key == (
            'rmsh', r'objects\gear\human\residential\shaders\vet_computer_screen'))
        if powerhouse_screen:
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_0_1_0_0_2_2_5_0_0_0_0_0_0'):
                raise ValueError('Powerhouse computer screen shader changed')
            specular = s.unpack('4f', source_constants[constant_names.index('specular_coefficient')])
            if specular != (0., 0., 0., 0.):
                raise ValueError('Powerhouse screen specular masking needs re-audit')
            # Stock Cold Storage monitor shader adds diffuse-alpha specular
            # masking. Zero authored specular makes that mask inert; all named
            # textures, constants and the LCD emission animation match.
            for animation_pass in s.block(source_post + 68, 6):
                routes = s.block(source_post + 80, 4)
                for usage in (1, 2):
                    packed = s.unpack('H', animation_pass + usage * 2)[0]
                    for route in routes[packed & 1023:(packed & 1023) + (packed >> 10)]:
                        constant = s.data[route + 3]
                        if constant_names[constant] == 'specular_coefficient':
                            raise ValueError('Animated screen specular needs re-audit')
            variants = [0, 1, 0, 1, 2, 2, 5, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_0_1_0_1_2_2_5_0_0_0'
            prisoner_template = True
        if (source_filename == 's3d_powerhouse.map' and key[0] == 'rmsh'
                and key[1] in POWERHOUSE_NATIVE_OBJECT_VARIANTS):
            reviewed = POWERHOUSE_NATIVE_OBJECT_VARIANTS[key[1]]
            source_template = s.name(s.u(source_post + 12) & 65535)
            variants = [int(v) for v in source_template.rsplit('\\', 1)[-1].split('_')[1:]]
            if (len(variants) != 13 or any(variants[10:])
                    or reviewed != '_' + '_'.join(map(str, variants[:10]))):
                raise ValueError('Powerhouse reviewed object material variant changed')
            sky_template = source_template.rsplit('\\', 1)[0] + '\\' + reviewed
            prisoner_template = True  # strict named parameters and animation relocation
        if (source_filename == 's3d_powerhouse.map' and key[0] == 'rmsh'
                and key[1] in {r'levels\multi\s3d_powerhouse\shaders\m30_wire_tech',
                               r'levels\multi\s3d_powerhouse\shaders\m30_wire_tech_v2'}):
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_7_2_0_1_1_2_5_0_1_0_0_0_0'):
                raise ValueError('Powerhouse wire material changed')
            variants = [0, 2, 0, 1, 1, 2, 5, 0, 1, 0]
            sky_template = r'shaders\shader_templates\_0_2_0_1_1_2_5_0_1_0'
            prisoner_template = powerhouse_wire = True
        powerhouse_interior_concrete = (source_filename == 's3d_powerhouse.map' and key == (
            'rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_concrete_interior'))
        if powerhouse_interior_concrete:
            # Source two-lobe Phong has zero specular, including environment
            # reflectance, and unit diffuse. White, non-inverted detail mask
            # with unit strength reduces exactly to native unmasked detail.
            # Reuse Armory's diffuse detail-blend program, preserving both
            # authored detail textures/transforms instead of the fallback.
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_1_3_0_2_2_2_0_0_0_0_0_0_0') or s.u(source_post + 92) or s.u(source_post + 52):
                raise ValueError('Powerhouse interior concrete options changed; re-audit required')
            for name, expected in (('specular_coefficient', (0.,) * 4),
                                   ('diffuse_coefficient', (1.,) * 4),
                                   ('bump_detail_coefficient', (1.,) * 4)):
                if s.unpack('4f', source_constants[constant_names.index(name)]) != expected:
                    raise ValueError('Powerhouse interior concrete lighting changed; re-audit required')
            mask = source_textures[texture_names.index('bump_detail_mask_map')]
            if s.name(s.u(mask + 12) & 65535) != r'shaders\default_bitmaps\bitmaps\color_white':
                raise ValueError('Powerhouse interior concrete mask changed; re-audit required')
            variants = [1, 2, 0, 0, 0, 0, 0, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_1_2_0_0_0_0_0_0_0_0'
            prisoner_template = True
        powerhouse_extra_diffuse_detail = None
        diffuse_detail_families = {
            r'levels\multi\s3d_powerhouse\shaders\m30_garage_ceiling_settlement':
                ('_1_3_0_0_0_0_0_0_0_0_0_0_0', '_1_2_0_0_0_0_0_0_0_0'),
            r'levels\multi\s3d_powerhouse\shaders\m30_metal_transformer':
                ('_7_2_0_0_2_2_0_0_0_0_0_0_0', '_7_2_0_0_0_0_0_0_0_0'),
        }
        if source_filename == 's3d_powerhouse.map' and key[0] == 'rmsh':
            powerhouse_extra_diffuse_detail = diffuse_detail_families.get(key[1])
        if powerhouse_extra_diffuse_detail:
            expected_source, native_suffix = powerhouse_extra_diffuse_detail
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith(expected_source) or s.u(source_post + 92) or s.u(source_post + 52):
                raise ValueError('Powerhouse diffuse detail options changed; re-audit required')
            required = [('bump_detail_coefficient', (1.,) * 4)]
            if key[1].endswith('m30_metal_transformer'):
                # Two-lobe specular and environment reflectance both multiply
                # zero specular strength; unit diffuse matches native diffuse.
                required.extend((('specular_coefficient', (0.,) * 4), ('diffuse_coefficient', (1.,) * 4)))
            else:
                # White, non-inverted mask with unit strength equals unmasked
                # detail. Retain both albedo detail layers and normal inputs.
                mask = source_textures[texture_names.index('bump_detail_mask_map')]
                if s.name(s.u(mask + 12) & 65535) != r'shaders\default_bitmaps\bitmaps\color_white':
                    raise ValueError('Powerhouse garage detail mask changed; re-audit required')
            for name, expected in required:
                if s.unpack('4f', source_constants[constant_names.index(name)]) != expected:
                    raise ValueError('Powerhouse diffuse detail lighting changed; re-audit required')
            variants = [int(v) for v in native_suffix.split('_')[1:]]
            sky_template = '\\'.join(('shaders', 'shader_templates', native_suffix))
            prisoner_template = True
        powerhouse_diamondplate = (source_filename == 's3d_powerhouse.map' and key == (
            'rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_diamondplate'))
        if powerhouse_diamondplate:
            # Orbital's native overlay family retains all authored albedo and
            # normal inputs. Its texture specular mask and dynamic environment
            # replace inactive source paths: zero specular/environment strength,
            # no material-texture override, and no animated controls.
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_6_1_0_1_1_1_0_0_0_0_0_0_0') or s.u(source_post + 92) or s.u(source_post + 52):
                raise ValueError('Powerhouse diamondplate options changed; re-audit required')
            for name in ('specular_coefficient', 'environment_map_specular_contribution'):
                if s.unpack('4f', source_constants[constant_names.index(name)]) != (0.,) * 4:
                    raise ValueError('Powerhouse diamondplate specular changed; re-audit required')
            variants = [6, 1, 0, 2, 1, 2, 0, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_6_1_0_2_1_2_0_0_0_0'
            prisoner_template = True
        powerhouse_metal_exterior = (source_filename == 's3d_powerhouse.map' and key == (
            'rmsh', r'levels\multi\s3d_powerhouse\shaders\m10_metal_ext_a'))
        if powerhouse_metal_exterior:
            # High Ground preserves the three authored albedo inputs and no
            # normal mapping. Its additional simple emission is explicitly
            # zeroed below; source diffuse-only ignores the specular mask.
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_7_0_0_1_0_0_0_0_0_0_0_0_0') or s.u(source_post + 92) or s.u(source_post + 52):
                raise ValueError('Powerhouse metal exterior options changed; re-audit required')
            variants = [7, 0, 0, 0, 0, 0, 1, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_7_0_0_0_0_0_1_0_0_0'
            prisoner_template = True
        powerhouse_cliffs = (source_filename == 's3d_powerhouse.map' and key == (
            'rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_river_valley_cliffs'))
        if powerhouse_cliffs:
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_5_2_0_1_0_0_0_0_0_0_0_0_0') or s.u(source_post + 92):
                raise ValueError('Powerhouse cliff source permutation/animation changed')
            strength = s.unpack('4f', source_constants[constant_names.index('bump_detail_coefficient')])
            if any(abs(v-1.2)>1e-6 for v in strength):
                raise ValueError('Powerhouse cliff detail-normal coefficient changed')
            variants = [5, 2, 0, 0, 0, 0, 0, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_5_2_0_0_0_0_0_0_0_0'
            prisoner_template = True
        import os
        compiled_concrete_directory = os.environ.get('OPENH3M_POWERHOUSE_CONCRETE_SHADER_DIR')
        powerhouse_compiled_concrete = bool(compiled_concrete_directory and source_filename == 's3d_powerhouse.map'
            and key == ('rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_concrete_ext_settlement'))
        compiled_concrete_evidence = None
        if powerhouse_compiled_concrete:
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_1_3_0_2_2_1_0_0_0_0_0_0_0') or s.u(source_post + 92) or s.u(source_post + 52):
                raise ValueError('Powerhouse exterior concrete options changed; re-audit required')
            mask = source_textures[texture_names.index('bump_detail_mask_map')]
            if (s.name(s.u(mask + 12) & 65535) != r'shaders\default_bitmaps\bitmaps\color_white'
                    or s.unpack('4f', source_constants[constant_names.index('bump_detail_coefficient')]) != (1.,) * 4):
                raise ValueError('Powerhouse exterior concrete normal mask changed')
            variants = [1, 2, 0, 2, 2, 1, 0, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_1_2_0_2_2_0_0_0_0_0'
            prisoner_template = True
        compiled_corrugated_directory = os.environ.get('OPENH3M_POWERHOUSE_CORRUGATED_SHADER_DIR')
        powerhouse_compiled_corrugated = bool(compiled_corrugated_directory and source_filename == 's3d_powerhouse.map'
            and key == ('rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_metal_corrugated_sheet'))
        compiled_corrugated_evidence = None
        if powerhouse_compiled_corrugated:
            if (not s.name(s.u(source_post + 12) & 65535).endswith('_0_1_0_3_1_1_9_0_0_0_0_0_0')
                    or s.u(source_post + 52) or s.u(source_post + 92)):
                raise ValueError('Powerhouse corrugated options changed; re-audit required')
            variants = [0, 1, 0, 3, 1, 1, 9, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_0_1_0_1_1_1_0_0_0_0'
            prisoner_template = True
        compiled_splash_directory = os.environ.get('OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR')
        compiled_window_directory = os.environ.get('OPENH3M_POWERHOUSE_WINDOW_SHADER_DIR')
        powerhouse_compiled_window = bool(compiled_window_directory and source_filename == 's3d_powerhouse.map'
            and key == ('rmsh', r'levels\multi\s3d_powerhouse\shaders\windowbox_subfloor_a'))
        compiled_window_evidence = None
        compiled_opaque_grate_directory = os.environ.get('OPENH3M_POWERHOUSE_OPAQUE_GRATE_SHADER_DIR')
        powerhouse_compiled_opaque_grate = bool(compiled_opaque_grate_directory and source_filename == 's3d_powerhouse.map'
            and key == ('rmsh', r'levels\multi\s3d_powerhouse\shaders\m30_metal_grate_circular_floor_opaque'))
        compiled_opaque_grate_evidence = None
        if powerhouse_compiled_opaque_grate:
            if (not s.name(s.u(source_post + 12) & 65535).endswith('_0_2_0_0_0_0_0_0_0_0_0_0_0')
                    or s.u(source_post + 52) or s.u(source_post + 92)):
                raise ValueError('Powerhouse opaque grate options changed; re-audit required')
            variants = [0, 2, 0, 0, 0, 0, 0, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_0_2_0_0_0_0_0_0_0_0'
            prisoner_template = True
        if powerhouse_compiled_window:
            if (not s.name(s.u(source_post + 12) & 65535).endswith('_0_2_0_0_0_0_0_0_1_0_0_0_0')
                    or s.u(source_post + 52) or s.u(source_post + 92)):
                raise ValueError('Powerhouse window-floor options changed; re-audit required')
            variants = [0, 2, 0, 0, 0, 0, 0, 0, 1, 0]
            sky_template = r'shaders\shader_templates\_0_2_0_0_0_0_0_0_0_0'
            prisoner_template = True
        compiled_grate_directory = os.environ.get('OPENH3M_POWERHOUSE_GRATE_SHADER_DIR')
        powerhouse_compiled_grate = bool(compiled_grate_directory and source_filename == 's3d_powerhouse.map'
            and key[1] in (r'levels\multi\s3d_powerhouse\shaders\m30_metal_grate_circular',
                           r'levels\multi\s3d_powerhouse\shaders\m30_metal_grate_circular_floor'))
        compiled_grate_evidence = None
        if powerhouse_compiled_grate:
            if not s.name(s.u(source_post + 12) & 65535).endswith('_0_1_1_1_1_1_0_0_1_0_0_0_0'):
                raise ValueError('Powerhouse grate options changed; re-audit required')
            variants = [0, 1, 1, 1, 1, 1, 0, 0, 1, 0]
            sky_template = r'shaders\shader_templates\_0_1_1_1_2_1_0_0_1_0'
            prisoner_template = True
        compiled_river_directory = os.environ.get('OPENH3M_POWERHOUSE_RIVER_SHADER_DIR')
        powerhouse_compiled_river = bool(compiled_river_directory and source_filename == 's3d_powerhouse.map'
            and key == ('rmsh', r'levels\multi\s3d_powerhouse\shaders\settlement_river'))
        compiled_river_evidence = None
        if powerhouse_compiled_river:
            if not s.name(s.u(source_post + 12) & 65535).endswith('_5_2_0_0_1_2_0_3_0_0_0_0_0') or s.u(source_post + 52):
                raise ValueError('Powerhouse river options changed; re-audit required')
            variants = [5, 2, 0, 0, 1, 2, 0, 3, 0, 0]
            sky_template = r'shaders\shader_templates\_0_2_0_1_1_2_0_3_0_0'
            prisoner_template = True
        powerhouse_compiled_splash = bool(compiled_splash_directory and source_filename == 's3d_powerhouse.map'
            and key == ('rmsh', r'levels\multi\s3d_powerhouse\shaders\settlement_river_valley_waterfall_splash_a'))
        compiled_splash_evidence = None
        compiled_water_directory = os.environ.get('OPENH3M_POWERHOUSE_WATER_SHADER_DIR')
        powerhouse_compiled_water = bool(compiled_water_directory and source_filename == 's3d_powerhouse.map'
            and key[1] in (r'levels\multi\s3d_powerhouse\shaders\030_water_river_bottom',
                           r'levels\multi\s3d_powerhouse\shaders\settlement_river_inlet'))
        compiled_water_evidence = None
        if powerhouse_compiled_water:
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_0_2_0_0_1_2_0_3_0_0_0_0_0'):
                raise ValueError('Powerhouse compiled water source permutation changed')
            variants = [0, 2, 0, 0, 1, 2, 0, 3, 0, 0]
            sky_template = r'shaders\shader_templates\_0_2_0_1_1_2_0_3_0_0'
            prisoner_template = True
        if powerhouse_compiled_splash:
            source_template = s.name(s.u(source_post + 12) & 65535)
            if not source_template.endswith('_6_2_0_1_2_2_0_1_0_0_0_0_0'):
                raise ValueError('Powerhouse compiled splash source permutation changed')
            variants = [6, 2, 0, 1, 2, 2, 0, 1, 0, 0]
            sky_template = r'shaders\shader_templates\_6_2_0_1_2_2_0_0_0_0'
            prisoner_template = True
        water_card_directory = os.environ.get('OPENH3M_SKY_WATER_CARD_SHADER_DIR')
        sky_water_card = bool(water_card_directory and source_filename == 's3d_sky_bridgenew.map'
            and key[0] == 'rmsh' and key[1] in (
                r'levels\multi\s3d_sky_bridgenew\fx\shaders\settlement_pipe_small_water_01',
                r'levels\multi\s3d_sky_bridgenew\fx\shaders\settlement_pipe_small_water_02'))
        sky_water_card_evidence = None
        if sky_water_card:
            if s.name(s.u(source_post+12)&65535) != r'shaders\shader_templates\_6_2_0_1_2_2_4_1_0_0_0_0_0':
                raise ValueError('Sky water-card source profile changed')
            variants = [6,2,0,1,2,2,4,1,0,0]
            sky_template = r'shaders\shader_templates\_6_2_0_1_2_2_0_0_0_0'
            prisoner_template = True
        alpha_card_root = os.environ.get('OPENH3M_SKY_ALPHA_CARD_SHADER_ROOT')
        sky_alpha_card = bool(alpha_card_root and source_filename == 's3d_sky_bridgenew.map'
            and key[0] == 'rmsh' and (datum & 65535) in (12294,12159,12412,12416,12220))
        sky_alpha_card_evidence = None
        if sky_alpha_card:
            from sky_bridge_alpha_card import PROFILES
            alpha_profile, alpha_name, alpha_template, alpha_functions = PROFILES[datum & 65535]
            if s.name(s.u(source_post+12)&65535) != 'shaders\\shader_templates\\'+alpha_template:
                raise ValueError('Sky alpha-card source profile changed')
            alpha_card_directory = os.path.join(alpha_card_root,alpha_profile+'-native-01')
            variants = [int(v) for v in alpha_template.split('_') if v][:10]
            sky_template = r'shaders\shader_templates\_0_2_0_1_1_2_0_3_0_0'
            prisoner_template = True
        decal_card_directory = os.environ.get('OPENH3M_SKY_DECAL_CARD_SHADER_DIR')
        sky_decal_card = bool(decal_card_directory and source_filename == 's3d_sky_bridgenew.map'
            and key[0] == 'rmsh' and key[1].rsplit('\\',1)[-1] in (
                'sbr_decals_05','sbr_decals_01','sbr_decals_teem','sbr_decals_04'))
        sky_decal_card_evidence = None
        if sky_decal_card:
            if s.name(s.u(source_post+12)&65535) != r'shaders\shader_templates\_0_0_1_2_1_2_0_4_0_0_0_0_0':
                raise ValueError('Sky decal-card source profile changed')
            variants = [0,0,1,2,1,2,0,4,0,0]
            sky_template = r'shaders\shader_templates\_0_0_1_1_1_2_0_0_0_0'
            prisoner_template = True
        window_directory = os.environ.get('OPENH3M_SKY_WINDOW_SHADER_DIR')
        sky_window = bool(window_directory and source_filename == 's3d_sky_bridgenew.map'
            and key == ('rmsh', r'levels\multi\s3d_sky_bridgenew\shaders\sbr_window_01'))
        sky_window_evidence = None
        if sky_window:
            if s.name(s.u(source_post+12)&65535) != r'shaders\shader_templates\_0_0_0_0_1_2_0_3_0_0_0_0_0':
                raise ValueError('Sky window source permutation changed')
            variants = [0,0,0,0,1,2,0,3,0,0]
            sky_template = r'shaders\shader_templates\_0_2_0_1_1_2_0_3_0_0'
            prisoner_template = True
        screen_directory = os.environ.get('OPENH3M_SKY_SCREEN_SHADER_DIR')
        sky_screen = bool(screen_directory and source_filename == 's3d_sky_bridgenew.map'
            and key == ('rmsh', r'levels\multi\s3d_sky_bridgenew\shaders\screen_lines'))
        screen_evidence = None
        if sky_screen:
            if s.name(s.u(source_post+12)&65535) != r'shaders\shader_templates\_0_0_0_0_0_0_7_1_0_0_0_0_0':
                raise ValueError('Sky screen source permutation changed')
            variants = [0,0,0,0,0,0,7,1,0,0]
            sky_template = r'shaders\shader_templates\_0_0_0_0_0_0_1_1_0_0'
            prisoner_template = True
        if source_filename == 's3d_sky_bridgenew.map' and key[0] == 'rmsh':
            # These source materials have an exact original-H3 diffuse-only
            # template and identical parameter lists. The generic metal donor
            # otherwise adds an unrelated factory-panel normal and specular.
            source_template = s.name(s.u(source_post + 12) & 65535)
            if source_template == r'shaders\shader_templates\_0_0_0_0_0_0_0_0_0_0_0_0_0':
                variants = [0] * 10
                sky_template = r'shaders\shader_templates\_0_0_0_0_0_0_0_0_0_0'
                prisoner_template = True
        review_exact_templates = {
            ('rodentia.map', r'blackandfan\levels\multi\rodentia\shaders\dcr_bridge'):
                [0,1,0,2,5,2,0,3,0,0],
            ('resuscitation.map', r'levels\multi\resuscitation\shaders\coag_panel_i'):
                [0,0,0,0,0,0,0,0,0,0],
        }
        review_variants = review_exact_templates.get((source_filename, key[1]))
        if review_variants is not None:
            if options != review_variants + [0,0,0]:
                raise ValueError('Final-review exact material source options changed')
            variants = review_variants
            sky_template = 'shaders\\shader_templates\\_' + '_'.join(map(str, variants))
            prisoner_template = True
        chiron_ladder = (source_filename == 'putput.map' and
            key == ('rmsh', r'custom\levels\multiplayer\shaders\beavercreek_ladder'))
        if chiron_ladder:
            if options != [0,0,0,0,0,2,0,3,0,0,0,0,0]:
                raise ValueError('Chiron ladder source options changed')
            # Shipping alpha-blended diffuse shader retains the authored RGBA
            # cutout. The old opaque metal prototype discarded its alpha.
            # No exact native permutation with this dynamic reflection exists;
            # report the omitted weak reflection explicitly for visual review.
            variants = [0,0,0,0,0,0,0,3,0,0]
            sky_template = r'shaders\shader_templates\_0_0_0_0_0_0_0_3_0_0'
            prisoner_template = True
        sanctuary_water_card = (source_filename == 'sancr.map' and key[0] == 'rmsh'
            and key[1] in (r'levels\multi\sancr\shaders\water\vahalla_waterfall',
                           r'levels\multi\sancr\shaders\water\waterfall_splash'))
        if sanctuary_water_card:
            # Both cards use shipping H3 textures and the two-layer water
            # albedo mode. The generic opaque metal fallback dropped blending,
            # detail_map2 and scrolling. Use Valhalla's native alpha-blended
            # shader, preserving every authored texture, UV and animation.
            splash = key[1].endswith('waterfall_splash')
            expected_options = [7, 0 if splash else 1, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0]
            if options != expected_options:
                raise ValueError('Sanctuary water-card source options changed')
            variants = [7, 1, 0, 0, 0, 0, 0, 3, 0, 0]
            sky_template = r'shaders\shader_templates\_7_1_0_0_0_0_0_3_0_0'
            neutral_bump = splash
            prisoner_template = True
        sanctuary_rock_templates = {
            r'levels\multi\sancr\shaders\rock\rock_rough_regular': '_1_2_0_1_7_0_0_0_0_0',
            r'levels\multi\sancr\shaders\rock\rock_rough_giant': '_1_2_0_1_7_0_0_0_0_0',
            r'levels\multi\sancr\shaders\rock\rock_rough_medium': '_1_2_0_1_7_0_0_0_0_0',
            r'levels\multi\sancr\shaders\terrain\outer_cliff': '_0_2_0_0_0_0_0_0_0_0',
        }
        sanctuary_rock_approximations = {
            r'levels\multi\sancr\shaders\rock\rock_rough_regular_wet': [1, 2, 0, 1, 1, 0, 0, 0, 0, 0],
            r'levels\multi\sancr\shaders\rock\outer_cliff_face': [1, 2, 0, 1, 7, 0, 0, 0, 2, 0],
            r'levels\multi\sancr\shaders\terrain\sanc_cliff_wall': [1, 2, 0, 1, 7, 0, 0, 0, 2, 0],
            r'levels\multi\sancr\shaders\rock\wet_cliff': [1, 2, 0, 1, 1, 0, 0, 0, 2, 0],
        }
        # User approved closest native H3 shading without parallax, 2026-11-05.
        # Preserve the two detail-color layers, detail normals and authored UVs.
        if source_filename == 'sancr.map' and key[1] in sanctuary_rock_approximations:
            if options != sanctuary_rock_approximations[key[1]] + [0, 0, 0]:
                raise ValueError('Sanctuary approximate rock source options changed')
            variants = [1, 2, 0, 1, 7, 0, 0, 0, 0, 0]
            sky_template = r'shaders\shader_templates\_1_2_0_1_7_0_0_0_0_0'
            prisoner_template = True
        if source_filename == 'sancr.map' and key[1] in sanctuary_rock_templates:
            suffix = sanctuary_rock_templates[key[1]]
            variants = [int(x) for x in suffix.split('_')[1:]]
            if options != variants + [0, 0, 0]:
                raise ValueError('Sanctuary rock source options changed')
            sky_template = 'shaders\\shader_templates\\' + suffix
            prisoner_template = True
        if sky_template:
            donor_options = ({'preferred_map': lockout_stock_lighting[2],
                              'preferred_material': lockout_stock_lighting[3]}
                             if lockout_stock_lighting else {})
            if powerhouse_compiled_splash:
                donor_options = dict(preferred_map='salvation.map',
                    preferred_material=r'levels\multi\salvation\sky\shaders\salvation_tower')
            if powerhouse_cliffs:
                donor_options = dict(preferred_map='bunkerworld.map',
                    preferred_material=r'levels\dlc\bunkerworld\sky\shaders\terrain_africa')
            if powerhouse_compiled_water or powerhouse_compiled_river:
                donor_options = dict(preferred_map='armory.map',
                    preferred_material=r'levels\dlc\armory\shaders\water_puddle')
            if powerhouse_compiled_grate:
                donor_options = dict(preferred_map='docks.map')
            if powerhouse_compiled_window or powerhouse_compiled_opaque_grate:
                donor_options = dict(preferred_map='bunkerworld.map')
            if powerhouse_compiled_corrugated:
                donor_options = dict(preferred_map='construct.map')
            if sky_alpha_card:
                donor_options = dict(preferred_map='armory.map')
            if sky_decal_card:
                donor_options = dict(preferred_map='armory.map')
            if sky_window:
                donor_options = dict(preferred_map='armory.map')
            if sky_screen:
                donor_options = dict(preferred_map='zanzibar.map')
            if sky_water_card:
                donor_options = dict(preferred_map='salvation.map')
            if sanctuary_water_card:
                donor_options = dict(preferred_map='riverworld.map',
                    preferred_material=r'levels\multi\riverworld\shaders\vahalla_waterfall')
            if foundation_clouds:
                donor_options = dict(preferred_map='docks.map',
                    preferred_material=r'levels\dlc\docks\sky\shaders\clouds_horizon_dark')
            native_sky_post, names, sky_donor = self.native_effect_post('rmsh', sky_template, **donor_options)
            if sky_alpha_card:
                from sky_bridge_alpha_card import bind_alpha_card
                native_sky_post, names, sky_alpha_card_evidence = bind_alpha_card(self, native_sky_post, names, alpha_card_directory, datum & 65535)
            if sky_decal_card:
                from sky_bridge_decal_card import bind_decal_card
                native_sky_post, names, sky_decal_card_evidence = bind_decal_card(self, native_sky_post, names, decal_card_directory, datum & 65535)
            if sky_water_card:
                from sky_bridge_water_card import bind_water_card
                native_sky_post, names, sky_water_card_evidence = bind_water_card(self, native_sky_post, names, water_card_directory, datum & 65535)
            if sky_window:
                from sky_bridge_window import bind_window
                native_sky_post, names, sky_window_evidence = bind_window(self, native_sky_post, names, window_directory)
            if sky_screen:
                from sky_bridge_screen import bind_screen
                native_sky_post, names, screen_evidence = bind_screen(self, native_sky_post, names, screen_directory)
            if powerhouse_compiled_concrete:
                from powerhouse_compiled_concrete import bind_compiled_concrete
                native_sky_post, names, compiled_concrete_evidence = bind_compiled_concrete(
                    self, native_sky_post, names, compiled_concrete_directory)
            if powerhouse_compiled_river:
                from powerhouse_compiled_concrete import bind_compiled_concrete
                native_sky_post, names, compiled_river_evidence = bind_compiled_concrete(
                    self, native_sky_post, names, compiled_river_directory, blend_mode=3, river=True)
            if powerhouse_compiled_grate:
                from powerhouse_compiled_concrete import bind_compiled_concrete
                native_sky_post, names, compiled_grate_evidence = bind_compiled_concrete(
                    self, native_sky_post, names, compiled_grate_directory, grate=True)
            if powerhouse_compiled_window:
                from powerhouse_compiled_concrete import bind_compiled_concrete
                native_sky_post, names, compiled_window_evidence = bind_compiled_concrete(
                    self, native_sky_post, names, compiled_window_directory, window=True)
            if powerhouse_compiled_opaque_grate:
                from powerhouse_compiled_concrete import bind_compiled_concrete
                native_sky_post, names, compiled_opaque_grate_evidence = bind_compiled_concrete(
                    self, native_sky_post, names, compiled_opaque_grate_directory, opaque_grate=True)
            if powerhouse_compiled_corrugated:
                from powerhouse_compiled_concrete import bind_compiled_concrete
                native_sky_post, names, compiled_corrugated_evidence = bind_compiled_concrete(
                    self, native_sky_post, names, compiled_corrugated_directory, corrugated=True)
            if powerhouse_compiled_splash:
                from powerhouse_compiled_splash import bind_compiled_splash
                native_sky_post, names, compiled_splash_evidence = bind_compiled_splash(
                    self, native_sky_post, names, compiled_splash_directory)
            if powerhouse_compiled_water:
                from powerhouse_compiled_splash import bind_compiled_splash
                native_sky_post, names, compiled_water_evidence = bind_compiled_splash(
                    self, native_sky_post, names, compiled_water_directory, blend_mode=3)
            if forge_primary_color:
                from forge_primary_color import bind_primary_color
                native_sky_post, forge_primary_routes = bind_primary_color(self, native_sky_post, names)
            if battle_static_environment:
                from static_environment_adapter import bind_static_cube
                native_sky_post, names, static_cube_routes = bind_static_cube(self, native_sky_post, names)
            target_texture_names, target_constant_names = names
            if foundation_clouds:
                from foundation_sky import TEXTURES, CONSTANTS
                switches = self.native_effect_post.parameter_switches[sky_template]
                if (names != (TEXTURES, CONSTANTS) or switches != {'integer': [], 'boolean': ['no_dynamic_lights']}
                        or struct.unpack_from('>I', native_sky_post, 52)[0]):
                    raise ValueError('Foundation cloud native parameter/switch layout changed')
            if rodentia_diffuse_emission and (
                    not {'diffuse_coefficient', 'specular_coefficient'}.issubset(target_constant_names)
                    or struct.unpack_from('>I', native_sky_post, 40)[0]
                    or struct.unpack_from('>I', native_sky_post, 52)[0]):
                raise ValueError('Rodentia native diffuse-light donor layout/switches changed')
            count, pointer = struct.unpack_from('>II', native_sky_post, 16)
            textures = bytearray(b.read(pointer, count * 24))
            count, pointer = struct.unpack_from('>II', native_sky_post, 28)
            constants = bytearray(b.read(pointer, count * 16))
        imported = []
        for index, name in enumerate(target_texture_names):
            if lockout_neutral_emission_detail and name == 'self_illum_detail_map':
                neutral = self.target_names['bitm', r'shaders\default_bitmaps\bitmaps\default_detail']
                struct.pack_into('>I', textures, index * 24 + 12, neutral)
                continue
            if (fused_ridge_detail or fused_small_rock_detail) and name == 'bump_detail_map':
                flat = self.target_names['bitm', r'shaders\default_bitmaps\bitmaps\default_vector']
                struct.pack_into('>I', textures, index*24+12, flat)
                imported.append(name)
                continue
            if neutral_bump and name in ('bump_map','bump_detail_map'):
                flat = self.target_names['bitm', r'shaders\default_bitmaps\bitmaps\default_vector']
                struct.pack_into('>I',textures,index*24+12,flat)
                continue
            source_name = 'base_map' if name == 'alpha_test_map' and name not in texture_names else name
            if gravlift_emission and name == 'self_illum_map':
                source_name = 'self_illum_detail_map'
            if boarding_sky_emission is not None and name == 'self_illum_map':
                source_name = 'base_map'
            if source_name not in texture_names:
                continue
            row = source_textures[texture_names.index(source_name)]
            bitmap_datum = s.u(row + 12)
            if bitmap_datum == 0xffffffff:
                continue
            if powerhouse_wire and name == 'detail_map':
                from powerhouse_wire import bake
                import hashlib
                baked, powerhouse_wire_report = bake(self, source_post)
                composed_key = ('powerhouse_wire_detail', hashlib.sha256(baked.pixels(0)).digest())
                if composed_key not in self.done:
                    self.done[composed_key] = self.bitmap_resource(*self.encode_bitmap(baked, 0, preserve_color_mips=True))
                bitmap = self.done[composed_key]
            elif gravlift_emission and name == 'base_map':
                from gravlift_material import black_rgb_mask
                bitmap = self.bitmap_resource(*self.encode_bitmap(
                    black_rgb_mask(self.bitmaps,bitmap_datum&65535),bitmap_datum&65535,
                    preserve_color_mips=True))
            elif boarding_metal is not None and name == 'material_texture':
                bitmap = boarding_metal_bitmap
            elif boarding_metal is not None and name in ('base_map','detail_map'):
                bitmap = self.bitmap_resource(*self.encode_bitmap(self.bitmaps,bitmap_datum&65535,
                    opaque_alpha=True,preserve_color_mips=True))
            elif fused_small_rock_detail and name == 'bump_map':
                from fused_small_rock_normal import bake
                detail_datum = s.u(source_textures[texture_names.index('bump_detail_map')]+12)
                baked = bake(self.bitmaps, bitmap_datum & 65535, detail_datum & 65535)
                bitmap = self.bitmap_resource(*self.encode_bitmap(
                    baked, bitmap_datum & 65535, max_dimension=1024, preserve_normal_mips=True))
            elif fused_ridge_detail and name == 'bump_map':
                from fused_ridge_normal import bake
                transforms = [s.unpack('4f', source_constants[constant_names.index(n)]) for n in ('bump_map', 'bump_detail_map')]
                baked = bake(self.bitmaps, bitmap_datum & 65535, *transforms)
                bitmap = self.bitmap_resource(*self.encode_bitmap(
                    baked, bitmap_datum & 65535, max_dimension=1024, preserve_normal_mips=True))
            elif powerhouse_cliffs and name == 'bump_detail_map':
                from normal_strength import scaled_strength
                baked, detail_strength_report = scaled_strength(self.bitmaps, bitmap_datum & 65535, strength[0], uncompressed=True)
                bitmap = self.bitmap_resource(*self.encode_bitmap(
                    baked, bitmap_datum & 65535, preserve_normal_mips=True))
            elif half_detail_strength and name == 'bump_detail_map':
                from normal_strength import half_strength
                strength_key = ('half_strength_detail', s.name(bitmap_datum & 65535))
                if strength_key not in self.done:
                    baked, detail_strength_report = half_strength(self.bitmaps, bitmap_datum & 65535)
                    self.done[strength_key] = self.bitmap_resource(*self.encode_bitmap(
                        baked, bitmap_datum & 65535, preserve_normal_mips=True))
                bitmap = self.done[strength_key]
            elif lockout_composed_panel_normal and name == 'bump_map':
                from lockout_panel_normal import bake
                detail=s.u(source_textures[texture_names.index('bump_detail_map')]+12)&65535
                baked=bake(self.bitmaps,bitmap_datum&65535,detail)
                bitmap=self.bitmap_resource(*self.encode_bitmap(baked,bitmap_datum&65535,
                    max_dimension=1024,preserve_normal_mips=True))
            elif (neutral_diffuse_specular_mask or chiron_opaque_emission) and name == 'base_map':
                opaque_key = ('opaque_specular_base', s.name(bitmap_datum & 65535))
                if opaque_key not in self.done:
                    self.done[opaque_key] = self.bitmap_resource(*self.encode_bitmap(
                        self.bitmaps, bitmap_datum & 65535, opaque_alpha=True,
                        preserve_color_mips=elongation_unmasked_emission or powerhouse_lamp))
                bitmap = self.done[opaque_key]
            else:
                bitmap = self.bitmap(bitmap_datum)
            struct.pack_into('>I', textures, index * 24 + 12, bitmap)
            if prisoner_template and (getattr(self, 'boarding_action', False) or
                    source_filename == 's3d_powerhouse.map' or sky_screen or sky_window or sky_water_card or sky_decal_card or sky_alpha_card):
                # Exact shader programs do not imply identical material sampling.
                # Preserve authored image/address/filter/external selection while
                # retaining the donor's name-matched constant transform index.
                image, address, filtering, comparison, external, transform, pad, animation, pad2 = s.unpack('h4BbBhH', row + 16)
                if comparison or pad or pad2 or (animation and
                        (not animation >> 10 or (animation & 1023)+(animation >> 10) > s.u(source_post+92))):
                    raise ValueError('Exact native material needs unsupported sampler routing')
                struct.pack_into('>hBBB', textures, index * 24 + 16,
                                 image, address, filtering, external)
                # Animation conversion retains source overlay order while
                # remapping shader register routes and constant indices.
                struct.pack_into('>H', textures, index*24+22, animation)
            imported.append(source_name)
        for index, name in enumerate(target_constant_names):
            if powerhouse_wire and name == 'albedo_color':
                struct.pack_into('>4f', constants, index*16, 1., 1., 1., 1.)
                continue
            if lockout_neutral_emission_detail and name == 'self_illum_detail_map':
                struct.pack_into('>4f', constants, index * 16, 1., 1., 0., 0.)
                continue
            source_name = 'base_map' if name == 'alpha_test_map' and name not in constant_names else name
            if gravlift_emission and name == 'self_illum_map':
                source_name = 'self_illum_detail_map'
            if autoturret_emission:
                source_name = {v: k for k, v in animation_aliases.items()}.get(name, source_name)
            if boarding_sky_emission is not None and name == 'self_illum_map':
                source_name = 'base_map'
            if fused_ridge_detail and name == 'bump_map':
                source_name = 'bump_detail_map'
            if source_name in constant_names:
                values = s.unpack('4f', source_constants[constant_names.index(source_name)])
                if boarding_metal is not None:
                    if name == 'specular_tint':
                        values = tuple(boarding_metal['specular_tint']) + (values[3],)
                    elif name == 'env_tint_color':
                        values = tuple(v*boarding_metal['environment_scale'] for v in values[:3]) + (values[3],)
                if boarding_sky_emission is not None:
                    if name == 'albedo_color':
                        values = (0., 0., 0., values[3])
                    elif name == 'self_illum_color':
                        values = tuple(values[j] * boarding_sky_emission[j] for j in range(3)) + (values[3],)
                struct.pack_into('>4f', constants, index * 16, *values)
                if gravlift_emission and name == 'self_illum_color':
                    struct.pack_into('>4f', constants, index*16,
                                     *(v*gravlift_scale for v in values[:3]),values[3])
            elif disabled_extra_environment and name.startswith('env_tint'):
                struct.pack_into('>4f', constants, index * 16, 0., 0., 0., 0.)
            if powerhouse_metal_exterior and name in ('self_illum_color', 'self_illum_intensity'):
                struct.pack_into('>4f', constants, index * 16, 0., 0., 0., 0.)
            if rodentia_diffuse_emission:
                if name == 'diffuse_coefficient':
                    struct.pack_into('>4f', constants, index * 16, 1., 1., 1., 1.)
                elif name in ('specular_coefficient', 'analytical_specular_contribution',
                              'area_specular_contribution', 'environment_map_specular_contribution'):
                    struct.pack_into('>4f', constants, index * 16, 0., 0., 0., 0.)
            if autoturret_emission:
                if name == 'roughness':
                    power = s.unpack('4f', source_constants[constant_names.index('normal_specular_power')])[0]
                    if power < 0:
                        raise ValueError('Autoturret specular exponent must be nonnegative')
                    roughness = min(1., (2. / (power + 2.)) ** .5)
                    struct.pack_into('>4f', constants, index * 16, *(roughness,) * 4)
                elif name == 'use_material_texture':
                    struct.pack_into('>4f', constants, index * 16, 0., 0., 0., 0.)
            if battle_static_environment:
                if name == 'env_tint_color':
                    values = s.unpack('4f', source_constants[constant_names.index(name)])
                    struct.pack_into('>4f', constants, index * 16, *(v / 256. for v in values[:3]), values[3])
                elif name == 'env_roughness_scale':
                    struct.pack_into('>4f', constants, index * 16, 0., 0., 0., 0.)
        suppressed_specular = []
        implicit_defaults = []
        if powerhouse_wire:
            imported.append('detail_map2')
            implicit_defaults.append('detail_map2')
        if lockout_composed_panel_normal:
            imported.append('bump_detail_map')
            implicit_defaults.append('bump_detail_map') # unit UV folded into the generated texture
        detail_adjustment = None
        if boarding_metal is not None:
            imported.append('spec_tint_map') # verified constant folded into specular_tint
        if (prisoner_template or reach_scenery_template or forge_environment_template) and 'bump_detail_coefficient' in constant_names and 'bump_detail_coefficient' not in target_constant_names and not ((reach_scenery_template or forge_environment_template) and variants[1] == 1):
            value = s.unpack('4f', source_constants[constant_names.index('bump_detail_coefficient')])
            lockout_strengths = {
                r'levels\multi\lockoutfix\shaders\panel_poop_ramp_tech': 2.,
                r'levels\multi\lockoutfix\shaders\panel_poop_rampb': 5.,
                r'levels\multi\lockoutfix\shaders\chill_mainpillar_blue': 1.5,
                r'levels\multi\lockoutfix\shaders\chill_mainpillar_red': 1.5,
            }
            expected = lockout_strengths.get(key[1]) if authored_emission_template else None
            if getattr(self, 'haven_draft', False) and variants[1] == 1 and value == (0., 0., 0., 0.):
                detail_adjustment = {'source_strength': 0.0, 'native_detail_layer': False,
                                     'reason': 'Authored detail layer disabled; use native base-normal-only shader'}
            elif expected is not None and value == (expected,) * 4:
                # Deliberate map-specific appearance correction: retain the
                # texture and emission, use native unit detail instead of the
                # MCC-only amplified normals that exaggerate surface grain.
                detail_adjustment = {'source_strength': expected, 'native_strength': 1.0,
                                     'reason': 'Reduce amplified detail normals on Lockout surfaces'}
            elif value != (1., 1., 1., 1.) and not powerhouse_cliffs and not (half_detail_strength and value == (.5, .5, .5, .5)) and not (fused_ridge_detail and value == (2., 2., 2., 2.)) and not (fused_small_rock_detail and value == (2.5, 2.5, 2.5, 2.5)):
                raise ValueError('Non-unit MCC bump-detail strength requires explicit conversion')
            implicit_defaults.append('bump_detail_coefficient')
        if key[1].startswith('levels\\multi\\warlock\\shaders\\') or (getattr(self, 'resuscitation_sky', False) and key[1].startswith('levels\\multi\\resuscitation\\shaders\\')):
            # The approximate retail fallback produces unstable world highlights.
            # Preserve diffuse and bump lighting; use matte world materials.
            for index, name in enumerate(target_constant_names):
                if any(term in name for term in ('specular_coefficient',
                        'specular_contribution', 'specular_tint', 'env_tint',
                        'fresnel_color', 'reflection_coefficient')):
                    struct.pack_into('>4f', constants, index * 16, 0., 0., 0., 0.)
                    suppressed_specular.append(name)
        root = bytearray(c.data[retail:retail + 68])
        root[28:40] = bytes(12)
        owner, address = self.registry.newtag('rmsh', root)
        if sky_template:
            struct.pack_into('>III', root, 16, 10, b.alloc(struct.pack('>10h', *variants[:10])), 0)
            struct.pack_into('>H', root, 52, s.unpack('H', tag['offset'] + 52)[0])
            root[54] = s.data[tag['offset'] + 54]
            struct.pack_into('>i', root, 56, s.unpack('i', tag['offset'] + 56)[0])
            b.meta[address - b.base:address - b.base + 68] = root
        output_post = bytearray(native_sky_post if sky_template else c.data[post:post + 132])
        if sky_template and (getattr(self, 'boarding_action', False) or getattr(self, 'battle_canyon_rebuilt', False) or getattr(self, 'haven_draft', False) or (getattr(self, 'stock_materials', False) and prisoner_template) or battle_static_environment or autoturret_emission or gravlift_emission or source_filename == 's3d_powerhouse.map'):
            # Shader routing is reusable, but a donor's material switches are not.
            tm = s.tags[s.u(source_post + 12) & 65535]['offset']
            source_booleans = [self.source_strings.text(s.u(x)) for x in s.block(tm + 96, 4)]
            switches = self.native_effect_post.parameter_switches[sky_template]
            if s.u(source_post + 40) or switches['integer']:
                raise ValueError('Boarding Action integer material constants need named conversion')
            enabled = {n for j, n in enumerate(source_booleans) if s.u(source_post + 52) & (1 << j)}
            real_switches = set(source_booleans) & set(target_constant_names) & {'use_material_texture'}
            for name in real_switches:
                value = float(name in enabled)
                struct.pack_into('>4f', constants, target_constant_names.index(name)*16,
                                 value, value, value, value)
            if enabled - set(switches['boolean']) - real_switches:
                raise ValueError('Boarding Action enabled material switch has no native equivalent')
            flags = sum(1 << j for j, n in enumerate(switches['boolean']) if n in enabled)
            struct.pack_into('>I', output_post, 52, flags)
        converted_animations = 0
        authored_forge_sky = (getattr(self, 'forge_world_sky', False)
                              and '\\sky_halo\\shaders\\' in key[1])
        if prisoner_template or authored_forge_sky or reach_scenery_template or forge_environment_template or authored_conveyor:
            # Donor programs are reusable; donor material animations are not.
            output_post[56:104] = bytes(48)
            if s.u(source_post + 92):
                from material_animation import convert_material_animation
                converted_animations = convert_material_animation(self, source_post, output_post,
                    aliases=animation_aliases,
                    uniform_uv_exclusions=('self_illum_map',) if gravlift_emission else ())
        struct.pack_into('>III', output_post, 16, len(target_texture_names), b.alloc(textures), 0)
        struct.pack_into('>III', output_post, 28, len(target_constant_names), b.alloc(constants), 0)
        b.put(address + 40, 'III', 1, b.alloc(output_post), 0)
        self.done[key] = owner
        self.report.append({'source': key[1], 'retail_template': struct.unpack_from('>I', output_post, 12)[0] & 65535,
            'chiron_ladder_alpha': ({'native_blend': 'alpha blend', 'difference': 'Weak dynamic reflection omitted; authored color/alpha/detail retained'} if chiron_ladder else None),
            'native_diffuse_only_emission': rodentia_diffuse_emission,
            'gravlift_uniform_emission_fold': gravlift_scale,
            'autoturret_emission_adapter': ({'animation_aliases': animation_aliases,
                'difference': 'Native Cook-Torrance replaces two-lobe specular; roughness derives from normal exponent, glancing exponent and Fresnel steepness are not equivalent'}
                if autoturret_emission else None),
            'native_neutral_emission_detail': lockout_neutral_emission_detail,
            'powerhouse_screen_inert_specular_mask': powerhouse_screen,
            'foundation_clouds_inert_specular_mask': foundation_clouds,
            'sky_bridge_compiled_alpha_card': sky_alpha_card_evidence,
            'sky_bridge_compiled_decal_card': sky_decal_card_evidence,
            'sky_bridge_compiled_water_card': sky_water_card_evidence,
            'sky_bridge_compiled_window': sky_window_evidence,
            'sky_bridge_compiled_screen': screen_evidence,
            'powerhouse_compiled_concrete': compiled_concrete_evidence,
            'powerhouse_compiled_river': compiled_river_evidence,
            'powerhouse_compiled_grate': compiled_grate_evidence,
            'powerhouse_compiled_corrugated': compiled_corrugated_evidence,
            'powerhouse_compiled_window': compiled_window_evidence,
            'powerhouse_compiled_opaque_grate': compiled_opaque_grate_evidence,
            'powerhouse_compiled_splash': compiled_splash_evidence,
            'powerhouse_compiled_water': compiled_water_evidence,
            'powerhouse_native_metal_exterior': powerhouse_metal_exterior,
            'powerhouse_native_diamondplate_overlay': powerhouse_diamondplate,
            'powerhouse_extra_native_diffuse_detail': powerhouse_extra_diffuse_detail,
            'powerhouse_interior_concrete_native_detail_blend': powerhouse_interior_concrete,
            'powerhouse_cliffs_native_diffuse_blend': powerhouse_cliffs,
            'powerhouse_wire_detail_composition': powerhouse_wire_report,
            'static_environment_cube_routes': static_cube_routes,
            'lockout_composed_panel_normal': lockout_composed_panel_normal,
            'stock_lighting_donor': ({'map':lockout_stock_lighting[2], 'material':lockout_stock_lighting[3],
                'difference':'Original H3 two-lobe specular replaces source single-lobe roughness; authored emission/parallax retained'}
                if lockout_stock_lighting else None),
            'detail_strength_adjustment': detail_adjustment,
            'approximation': (powerhouse_wire or boarding_metal is not None or fused_ridge_detail or fused_small_rock_detail or lockout_composed_panel_normal or not (prisoner_template or reach_scenery_template or forge_environment_template) or bool(set(texture_names) - set(imported))
                              or bool(set(constant_names) - set(target_constant_names) - set(implicit_defaults))),
            'textures_imported': imported,
            'forge_primary_color_routes': forge_primary_routes,
            'reach_scenery_native_template': sky_template if reach_scenery_template else None,
            'forge_environment_native_template': sky_template if forge_environment_template else None,
            'neutral_bump': neutral_bump,
            'neutral_diffuse_specular_mask': neutral_diffuse_specular_mask,
            'opaque_emission_alpha_baked': chiron_opaque_emission,
            'boarding_sky_emission_scale': boarding_sky_emission,
            'boarding_metal_control_conversion': boarding_metal,
            'converted_source_animations': converted_animations,
            'disabled_extra_environment': disabled_extra_environment,
            'implicit_native_defaults': implicit_defaults,
            'half_strength_detail_baked': half_detail_strength,
            'fused_ridge_detail': fused_ridge_detail,
            'fused_small_rock_detail': fused_small_rock_detail,
            'detail_strength_report': detail_strength_report,
            'forge_sky_alias': forge_sky_alias,
            'native_sky_template': sky_template if not prisoner_template else None,
            'native_sky_donor': sky_donor if sky_template and not prisoner_template else None,
            'native_material_template': sky_template if prisoner_template or reach_scenery_template or forge_environment_template else None,
            'native_material_donor': sky_donor if prisoner_template or reach_scenery_template or forge_environment_template else None,
            'fallback_specular_suppressed': suppressed_specular,
            'unrepresented_textures': sorted(set(texture_names) - set(imported)),
            'unrepresented_constants': sorted(set(constant_names) - set(target_constant_names) - set(implicit_defaults))})
        return 'rmsh', owner

    def particle_post(self, source_post, group='prt3'):
        """Use native particle/decal routing with source named parameters."""
        s, c, b = self.source, self.target, self.builder
        template_name = s.name(s.u(source_post + 12) & 65535)
        aliases = DECAL_ALIASES if group == 'decs' else PARTICLE_ALIASES if group == 'prt3' else {}
        alias = aliases.get(template_name.rsplit('\\', 1)[-1])
        from dune_decal import matches as dune_decal_matches, NOTE as DUNE_DECAL_NOTE
        dune_decal = dune_decal_matches(s, source_post, group, template_name)
        if dune_decal:
            alias = ('_0_3_0_1_0_0', 'combined_alpha', DUNE_DECAL_NOTE)
        from dune_projectile import matches as dune_projectile_matches, NOTE as DUNE_PROJECTILE_NOTE
        if dune_projectile_matches(s, source_post, group, template_name):
            alias = ('_0_8_1_0', 'blend_mode', DUNE_PROJECTILE_NOTE)
        target_template = template_name.rsplit('\\', 1)[0] + '\\' + alias[0] if alias else template_name
        sky_bridge_ldr = (group=='prt3' and template_name==r'shaders\particle_templates\_0_8_0_0_1_0_0_0_0_0'
                          and str(s.file.name).replace('\\','/').endswith('/s3d_sky_bridgenew.map'))
        if sky_bridge_ldr:
            target_template=r'shaders\particle_templates\_0_8_0_0_0_0_0_0_0_0'
        sky_bridge_smoke = (group=='prt3' and template_name==r'shaders\particle_templates\_5_10_0_0_0_1_0_1_0_0'
                            and str(s.file.name).replace('\\','/').endswith('/s3d_sky_bridgenew.map'))
        if sky_bridge_smoke:
            target_template=r'shaders\particle_templates\_5_10_0_1_0_1_1_1_0_0'
        post = None
        for tag in c.tags.values():
            tag_group = tag['group']
            if tag_group != group and not (group == 'rmd ' and tag_group == 'decs'):
                continue
            if tag_group == 'rmd ':
                containers = [tag['offset'] + 40]
            elif tag_group == 'decs':
                containers = [row + 48 for row in c.block(tag['offset'] + 20, 116)]
            elif tag_group == 'cntl':
                containers = [row + 0x158 for row in c.block(tag['offset'], 0x26c)]
            elif tag_group == 'beam':
                containers = [row + 0x2c for row in c.block(tag['offset'], 0x208)]
            elif tag_group == 'ltvl':
                containers = [row + 0x2c for row in c.block(tag['offset'], 0x17c)]
            else:
                containers = [tag['offset'] + 100]
            for candidate in (post for container in containers for post in c.block(container, 132)):
                datum = c.u(candidate + 12)
                if datum != 0xffffffff and c.name(datum & 65535) == template_name:
                    post, alias, target_template = candidate, None, template_name
                    break
                if datum != 0xffffffff and c.name(datum & 65535) == target_template:
                    post = candidate
            if post is not None and alias is None:
                break
        if alias and alias[1] == 'neutral_black_point':
            self.verify_zero_particle_black_point(source_post)
        native_output = None
        native_donor = None
        if post is None and self.native_effect_post is not None:
            native_output, target_names, native_donor = self.native_effect_post(
                group, target_template, replace_material_textures=(group == 'decs'))
        elif post is None:
            raise ValueError(f'No supported retail {group} template: {template_name}')
        else:
            target_names = self.parameters(c, self.target_strings, post)
        source_names = self.parameters(s, self.source_strings, source_post)
        textures = s.block(source_post + 16, 28)
        constants = s.block(source_post + 28, 16)
        if len(textures) != len(source_names[0]) or len(constants) != len(source_names[1]):
            raise ValueError('Particle template parameter count mismatch')
        baked_bitmap = None
        baked_tiles = None
        opaque_bitmap = None
        combined_alpha_mode = None
        constant_overrides = {}
        color_scale = (1.,1.,1.)
        if group == 'decs' and alias and template_name.endswith('\\_6_3_0_1_0_2'):
            index=source_names[1].index('modulation_factor')
            if s.unpack('4f',constants[index])!=(0.,)*4:
                raise ValueError('Native unmodulated decal requires constant zero modulation')
            constants=[row for j,row in enumerate(constants) if j!=index]
            source_names=(source_names[0],[name for j,name in enumerate(source_names[1]) if j!=index])
        if group == 'decs' and alias and template_name.rsplit('\\',1)[-1] in ('_3_3_0_0_0_1','_6_3_0_0_0_1'):
            values=dict(zip(source_names[1],[s.unpack('4f',row) for row in constants]))
            color_scale=values['tint_color'][:3]
            constant_overrides={'tint_color':(1.,)*4}
        if group == 'decs' and template_name.endswith('\\_3_3_0_0_0_2') and alias:
            values=dict(zip(source_names[1],[s.unpack('4f',row) for row in constants]))
            factor=values['modulation_factor']
            if factor == (0.,)*4:
                tint=values['tint_color'];intensity=values['intensity']
                if tint[0]!=tint[1] or tint[0]!=tint[2]:
                    raise ValueError('Unmodulated decal requires grayscale tint for native endpoint mapping')
                constant_overrides={'tint_color':(1.,)*4,'intensity':tuple(v*tint[0] for v in intensity)}
            elif factor != (1.,)*4:
                raise ValueError('Intermediate decal tint modulation has no native endpoint mapping')
            constants=[row for name,row in zip(source_names[1],constants) if name!='modulation_factor']
            source_names=(source_names[0],[n for n in source_names[1] if n!='modulation_factor'])
        if (group == 'decs' and alias and alias[1] == 'albedo'
                and template_name.endswith('\\_6_3_0_0_1_0') and textures
                and (s.name(s.u(textures[0]+12)&65535) or '').startswith('levels\\multi\\s3d_powerhouse\\')):
            alias = (alias[0], 'combined_alpha',
                     'Unit-tiled Powerhouse diffuse/mask combined at common authored mip levels without recompression; RGB shares alpha clamp addressing')
        if group == 'decs' and alias and alias[1] == 'combined_alpha':
            if source_names[0] not in (['base_map', 'alpha_map', 'bump_map'], ['base_map', 'alpha_map']) or s.u(source_post + 92):
                raise ValueError('Combined decal requires static diffuse/alpha bindings with optional bump')
            if any(s.unpack('4f',constants[source_names[1].index(n)]) != (1.,)*4 for n in ('u_tiles','v_tiles')):
                raise ValueError('Combined decal requires unit tiling')
            base, mask = textures[:2]
            for row in (base,mask):
                datum=s.u(row+12)
                if datum==0xffffffff or s.u(s.tags[datum&65535]['offset']+84):
                    raise ValueError('Combined decal requires nonsprite images')
                if s.unpack('h4BbBhH',row+16)[3:] != (0,0,-1,0,0,0):
                    raise ValueError('Combined decal has unexpected texture routing')
            if s.data[base+18] not in (0,17) or s.data[mask+18]!=17 or s.data[base+19]!=s.data[mask+19]:
                raise ValueError('Combined decal requires common filtering and clamped alpha')
            from decal_bitmap import combine_bc_alpha, combine_resampled_alpha
            key=('combined_decal_alpha',s.u(base+12),s.u(mask+12),color_scale)
            bi,mi=(self.bitmaps.info(d&65535)[0] for d in key[1:3])
            exact=(color_scale==(1.,1.,1.) and bi['format'] in (14,16) and mi['format']==16
                   and (bi['width'],bi['height'])==(mi['width'],mi['height'])
                   and bi['mips']==mi['mips'])
            identical=color_scale==(1.,1.,1.) and s.data[base+12:base+28]==s.data[mask+12:mask+28]
            combined_alpha_mode=('original_bitmap' if identical else 'authored_bc_blocks_common_mips' if exact
                                 else 'derived_linear_resample_argb8_authored_dimensions_levels')
            if key not in self.done:
                if dune_decal:
                    from dune_decal import encode as encode_dune_decal
                    encoded = encode_dune_decal(self.bitmaps, key[1]&65535, key[2]&65535)
                    combined_alpha_mode = 'exact_authored_bc_rgb_alpha_all_mips'
                    self.remember_composite_bitmap([d&65535 for d in key[1:3]], encoded, combined_alpha_mode)
                    self.done[key] = self.bitmap_resource(*encoded)
                elif identical:
                    self.done[key] = self.bitmap(key[1])
                else:
                    encoded = (combine_bc_alpha(self.bitmaps,key[1]&65535,key[2]&65535) if exact
                        else combine_resampled_alpha(self.bitmaps,key[1]&65535,key[2]&65535,color_scale))
                    self.remember_composite_bitmap([d&65535 for d in key[1:3]], encoded, combined_alpha_mode)
                    self.done[key] = self.bitmap_resource(*encoded)
            baked_bitmap=self.done[key]
            textures=[mask,*textures[2:]]
            source_names=([name for name in source_names[0] if name!='alpha_map'],source_names[1])
        if group == 'decs' and alias and alias[1] == 'untiled_alpha':
            if source_names[0] != ['base_map', 'alpha_map', 'bump_map'] or s.u(source_post + 92):
                raise ValueError('Untiled-alpha decal requires static diffuse/alpha/bump bindings')
            for name in ('u_tiles', 'v_tiles'):
                if s.unpack('4f', constants[source_names[1].index(name)]) != (1.,)*4:
                    raise ValueError('Separate alpha cannot use untiled native sampling with nonunit tiling')
            for row in textures[:2]:
                datum = s.u(row + 12)
                if datum == 0xffffffff or s.u(s.tags[datum & 65535]['offset'] + 0x54):
                    raise ValueError('Untiled-alpha decal requires nonsprite images')
                if s.unpack('h4BbBhH', row + 16)[3:] != (0, 0, -1, 0, 0, 0):
                    raise ValueError('Untiled-alpha decal has unexpected texture transforms')
        if group == 'decs' and alias and alias[1] == 'identical_alpha':
            # decal.fx diffuse_plus_alpha samples both maps at the same UVs.
            # Identical bindings therefore reduce exactly to diffuse_only.
            if source_names[0] != ['base_map', 'alpha_map', 'bump_map'] or s.u(source_post + 92):
                raise ValueError('Identical-alpha decal requires static diffuse/alpha/bump bindings')
            base, alpha = textures[:2]
            if s.u(base + 12) == 0xffffffff or s.data[base + 12:base + 28] != s.data[alpha + 12:alpha + 28]:
                raise ValueError('Separate decal alpha is not identical to diffuse sampling')
            textures = [textures[0], textures[2]]
            source_names = (['base_map', 'bump_map'], source_names[1])
        if group == 'decs' and alias and alias[1] == 'opaque_alpha':
            if source_names != (['base_map'], ['u_tiles', 'v_tiles']) or s.u(source_post + 92):
                raise ValueError('Opaque decal adapter requires a static diffuse-only decal')
            datum = s.u(textures[0] + 12)
            if datum == 0xffffffff or s.u(s.tags[datum & 65535]['offset'] + 0x54):
                raise ValueError('Opaque decal adapter requires a nonsprite bitmap')
            key = ('opaque_decal', datum)
            if key not in self.done:
                self.done[key] = self.bitmap_resource(*self.encode_bitmap(
                    self.bitmaps, datum & 65535, opaque_alpha=True))
            opaque_bitmap = self.done[key]
        if group == 'decs' and alias and alias[1] == 'albedo':
            # Mask albedo samples alpha in untiled coordinates. It is equivalent
            # to base alpha only for the same texture, untiled and without sprites.
            base = textures[source_names[0].index('base_map')]
            mask = textures[source_names[0].index('alpha_map')]
            datum = s.u(base + 12)
            tile_values = [s.unpack('4f', constants[source_names[1].index(name)])
                           for name in ('u_tiles', 'v_tiles')]
            mask_datum = s.u(mask + 12)
            if (datum == 0xffffffff or mask_datum == 0xffffffff
                    or s.unpack('h', base + 16)[0] != 0 or s.unpack('h', mask + 16)[0] != 0
                    or s.unpack('h4BbBhH', base + 16)[3:] != (0, 0, -1, 0, 0, 0)
                    or s.unpack('h4BbBhH', mask + 16)[3:] != (0, 0, -1, 0, 0, 0)):
                raise ValueError('Decal mask requires unsupported sampler/transform routing')
            if (datum != mask_datum or any(values != (1., 1., 1., 1.) for values in tile_values)):
                if s.data[base + 18] != 0 or s.data[mask + 18] != 17:
                    raise ValueError('Decal baking requires wrap diffuse and clamp mask addressing')
                from decal_bitmap import bake
                baked_tiles = tuple(values[0] for values in tile_values)
                key = ('decal_bake', datum, mask_datum, baked_tiles)
                if key not in self.done:
                    encoded = bake(self.bitmaps, datum & 65535, mask_datum & 65535, baked_tiles)
                    self.remember_composite_bitmap([datum&65535, mask_datum&65535], encoded,
                                                  'derived_nearest_tiled_rgb_untiled_alpha_per_authored_level')
                    self.done[key] = self.bitmap_resource(*encoded)
                baked_bitmap = self.done[key]
                alias = (alias[0], alias[1], 'Separate alpha mask composed per authored level at full base dimensions; derived nearest sampling, not a lossless source copy; native unmodulated tint/pre-lighting pass')
            elif s.u(s.tags[datum & 65535]['offset'] + 0x54):
                raise ValueError('Decal alpha alias does not support sprites')
            # Both samples address the same pixels. Retain the mask sampler for
            # the combined texture so clamp/filter behavior preserves cutouts;
            # RGB now shares its filtering instead of its old independent sampler.
            textures[source_names[0].index('base_map')] = mask
            alias = (alias[0], alias[1], alias[2] + '; RGB shares alpha-mask sampler filtering/addressing')
            mask_index = source_names[0].index('alpha_map')
            textures = [row for index, row in enumerate(textures) if index != mask_index]
            source_names = ([name for name in source_names[0] if name != 'alpha_map'], source_names[1])
        if source_names != target_names:
            raise ValueError(f'{group}:{template_name}: parameter order differs '
                             f'({source_names!r} vs {target_names!r}) or has '
                             f'{s.u(source_post + 92)} animated overlays at {source_post:#x}')
        converted = bytearray()
        for row in textures:
            bitmap = s.u(row + 12)
            index, address, filtering, comparison, external, transform, pad, block, pad2 = s.unpack('h4BbBhH', row + 16)
            if (comparison or pad or pad2
                    or (block and ((block & 1023) + (block >> 10) > s.u(source_post + 92)
                                   or not block >> 10))):
                raise ValueError('Unsupported particle sampler comparison/animation routing')
            bitmap = (opaque_bitmap if opaque_bitmap is not None else
                      baked_bitmap if baked_bitmap is not None and row == mask else
                      self.bitmap(bitmap) if bitmap != 0xffffffff else bitmap)
            converted.extend((b'bitm' if bitmap != 0xffffffff else b'\xff'*4) + bytes(8)
                             + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, block))
        output = bytearray(native_output if native_output is not None else c.data[post:post + 132])
        if sky_bridge_ldr or sky_bridge_smoke:
            from sky_bridge_particle import bind_ldr
            output=bind_ldr(self,output, 'particle-smoke-01' if sky_bridge_smoke else 'particle-ldr-01')
        native_blend_flags = bytes(output[104:108])
        if group == 'decs' and not s.u(source_post + 92):
            # Static authored decals must not inherit the donor's animations.
            output[56:104] = bytes(48)
        if s.u(source_post + 92):
            if alias or native_output is not None:
                raise ValueError('Animated effect requires an exact template in the base cache')
            from effect_animation import convert_animation
            for offset, header in convert_animation(s, c, b, self.source_strings,
                                                    self.target_strings, source_post, post).items():
                output[offset:offset + 12] = header
        for offset, stride, rows, payload in (
                (16, 24, textures, converted),
                (28, 16, constants, b''.join(struct.pack('>4I', *s.unpack('4I', row)) for row in constants))):
            struct.pack_into('>III', output, offset, len(rows), b.alloc(payload) if rows else 0, 0)
        if baked_tiles is not None:
            pointer = struct.unpack_from('>I', output, 32)[0]
            for name in ('u_tiles', 'v_tiles'):
                b.put(pointer + source_names[1].index(name) * 16, '4f', 1., 1., 1., 1.)
            # Bump retains the old tiled UVs after diffuse tiling was baked.
            index = source_names[1].index('bump_map')
            x, y, z, w = s.unpack('4f', constants[index])
            b.put(pointer + index * 16, '4f', x * baked_tiles[0], y * baked_tiles[1], z, w)
        if constant_overrides:
            pointer=struct.unpack_from('>I',output,32)[0]
            for name,values in constant_overrides.items():
                b.put(pointer+source_names[1].index(name)*16,'4f',*values)
        integers = s.block(source_post + 40, 4)
        payload = b''.join(struct.pack('>I', s.u(row)) for row in integers)
        struct.pack_into('>III', output, 40, len(integers), b.alloc(payload) if integers else 0, 0)
        struct.pack_into('>I', output, 52, s.u(source_post + 52))
        struct.pack_into('>III8h', output, 104, *s.unpack('III8h', source_post + 104))
        if alias and alias[1] == 'opaque_alpha':
            output[104:108] = native_blend_flags
        if alias and alias[1] == 'blend_mode':
            struct.pack_into('>I', output, 104, c.u(post + 104))
            index = source_names[1].index('blend_mode')
            native = c.block(post + 28, 16)[index]
            pointer = struct.unpack_from('>I', output, 32)[0]
            b.put(pointer + index * 16, '4I', *c.unpack('4I', native))
        self.report.append({'particle_template': template_name, 'retail_template': target_template,
                            'render_method_group': group,
                            'native_shader_donor': native_donor, 'sky_bridge_ldr_shader': sky_bridge_ldr,
                            'combined_alpha_mode': combined_alpha_mode,
                            'constant_overrides': constant_overrides,
                            'baked_color_scale': color_scale,
                            'animated_overlays': s.u(source_post + 92),
                            'approximation': bool(alias), 'difference': alias[2] if alias else None,
                            'textures_imported': source_names[0], 'constants_imported': source_names[1]})
        self.particle_aliases[source_post] = alias
        return bytes(output)

    def verify_zero_particle_black_point(self, source_post):
        """Allow the native black-point permutation only for proven neutral inputs."""
        s = self.source
        particles = {n for n, t in s.tags.items() if t['group'] == 'prt3'
                     and source_post in s.block(t['offset'] + 100, 140)}
        if len(particles) != 1:
            raise ValueError('Ambiguous particle black-point owner')
        count = 0
        for tag in s.tags.values():
            if tag['group'] != 'effe':
                continue
            for event in s.block(tag['offset'] + 44, 68):
                for system in s.block(event + 56, 92):
                    if s.u(system + 16) & 65535 not in particles:
                        continue
                    for emitter in s.block(system + 76, 752):
                        at = emitter + 0x2a0
                        size = s.u(at + 4)
                        pointer = s.pointer(s.u(at + 16)) if size else 0
                        function = s.data[pointer:pointer + size]
                        if (s.data[at + 2] != 0 or s.unpack('f', at + 24)[0] != 0
                                or function != b'\x01\x34\x00\x00' + bytes(28)):
                            raise ValueError('Particle black-point input is not a verified constant zero')
                        count += 1
        if not count:
            raise ValueError('No emitter evidence for neutral particle black point')

    def decal_root(self, source_offset, payload):
        """Apply reported option aliases to each converted decal render method."""
        source_rows = self.source.block(source_offset + 20, 116)
        count, pointer = struct.unpack_from('>II', payload, 20)
        if count != len(source_rows):
            raise ValueError('Decal system count changed during conversion')
        for index, row in enumerate(source_rows):
            posts = self.source.block(row + 48, 140)
            aliases = [self.particle_aliases.get(post) for post in posts]
            if not any(aliases):
                continue
            if len(posts) != 1:
                raise ValueError('Decal alias requires one postprocess record')
            options = [int(value) for value in aliases[0][0].split('_')[1:]]
            at = pointer + index * 116 + 24 - self.builder.base
            option_count, option_pointer = struct.unpack_from('>II', self.builder.meta, at)
            if option_count != len(options):
                raise ValueError('Decal option count differs from template name')
            for option, value in enumerate(options):
                self.builder.put(option_pointer + option * 2, 'h', value)
        return payload

    def particle_root(self, source_offset, payload):
        """Keep root options/runtime flags consistent with a reported alias."""
        posts = self.source.block(source_offset + 100, 140)
        if len(posts) != 1:
            return payload
        alias = self.particle_aliases.get(posts[0])
        if alias is None:
            return payload
        options = [int(x) for x in alias[0].split('_')[1:]]
        out = bytearray(payload)
        count, pointer = struct.unpack_from('>II', out, 76)
        if count != len(options):
            raise ValueError('Particle option count differs from template name')
        for index, value in enumerate(options):
            self.builder.put(pointer + index * 2, 'h', value)
        if alias[1] == 'render_targets':
            flags = struct.unpack_from('>I', out, 16)[0]
            struct.pack_into('>I', out, 16, flags & ~(1 << 14))
        return bytes(out)
