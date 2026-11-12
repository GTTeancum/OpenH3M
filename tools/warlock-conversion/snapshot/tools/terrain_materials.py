"""Bind MCC terrain and hologram parameters to original-disc shader templates."""
from source_schema import load_schema
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
        inactive_environment = group == 'rmtr' and source_variant == '_0_1_0_0_0_1'
        if inactive_environment:
            # All four layers are diffuse-only. MCC compiled no environment
            # samplers/constants; the native Bunkerworld permutation omits that
            # inactive option while retaining all four layers. Verify names below.
            fallback = variant = '_0_0_0_0_0_1'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
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
        single_layer = (group == 'rmtr'
                               and source_variant == '_0_0_1_2_2_0')
        if single_layer:
            # Shrine has the identical one-layer material plus environment mapping.
            # A zero environment tint disables that extra contribution.
            fallback = variant = '_0_1_1_2_2_0'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        donors = DONORS if group == 'rmtr' else self.hologram_donors
        generic_directory=Path(__file__).resolve().parents[4]/'work/sky-bridge/holograms-01'/source_variant
        sky_bridge_generic=(group=='rmhg' and str(s.file.name).replace('\\','/').endswith('/s3d_sky_bridgenew.map') and (generic_directory/'profile.json').is_file())
        if sky_bridge_generic:
            import json
            generic_profile=json.loads((generic_directory/'profile.json').read_text())
            if s.name(datum&65535) not in generic_profile['materials'] or source_options!=generic_profile['options']:
                raise ValueError('Hologram profile source changed')
        sky_bridge_soft = (s.name(datum & 65535) == r'levels\multi\s3d_sky_bridgenew\shaders\lighting\fx_lightvolume_building_bridge_rb' and source_options == [0,1,1,0,0,1,1,0,1])
        if group == 'rmhg':
            if not sky_bridge_generic and not sky_bridge_soft and (len(source_options) != 9 or any(source_options[7:])):
                raise ValueError('Nondefault MCC-only hologram options require separate conversion: ' + s.name(datum & 65535) + ' ' + str(source_options))
            variant = '_' + '_'.join(str(value) for value in source_options[:7])
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        lightvolume = (group == 'rmhg' and variant in ('_0_0_1_0_0_4_1','_0_1_1_0_0_4_1')
                       and 'lightvolume' in s.name(datum & 65535))
        if lightvolume:
            # Guardian's four coincident additive layers reproduce simple
            # illumination: the shader averages four samples. Disable depth
            # offset/attenuation and retain both overlays.
            fallback = variant = '_0_8_1_0_0_4_1'
            template_name = template_name.rsplit('\\',1)[0] + '\\' + variant
        computer_overlay = (group == 'rmhg' and s.name(datum & 65535) ==
                            r'levels\multi\s3d_powerhouse\shaders\m10_computer_screen_holo')
        if computer_overlay:
            if variant != '_0_5_1_0_0_3_1':
                raise ValueError('Powerhouse computer permutation changed')
            fallback = variant = '_0_5_1_0_0_0_1'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        native_unlit_sky = (group == 'rmhg' and variant == '_2_5_1_0_0_0_0'
                        and s.name(datum & 65535).startswith('levels\\multi\\s3d_powerhouse\\sky_settlement\\shaders\\'))
        if native_unlit_sky:
            # Guardian retains detail illumination/additive blending and no
            # edge fade. Its extra albedo samplers cannot affect this unlit
            # path: material_none contributes zero diffuse, illumination_detail
            # ignores albedo, and additive blending does not use albedo alpha.
            fallback = variant = '_0_5_1_0_0_0_0'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        neutral_edge = (group == 'rmhg' and variant == '_0_5_1_0_0_1_0'
                         and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\shaders\\'))
        neutral_edge |= (group == 'rmhg' and variant == '_0_4_1_0_0_0_0'
                         and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\'))
        if neutral_edge:
            # Original Cold Storage has identical albedo, illumination and
            # blending plus edge tint. Unit endpoint tints make that a no-op.
            fallback = variant = variant[:-1] + '1'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        neutral_warp = (group == 'rmhg' and variant == '_0_5_1_0_0_2_0'
                        and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\shaders\\'))
        if neutral_warp:
            # Native Armory has the same illumination/additive-detail overlay.
            # Zero warp amounts and unit edge tints disable its extra effects.
            fallback = variant = '_0_5_1_0_1_2_1'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        multiply_detail = (not sky_bridge_generic and group == 'rmhg' and variant == '_0_1_1_0_0_3_1'
                           and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\shaders\\lighting\\'))
        if multiply_detail:
            if s.u(post+80) or s.u(post+92):
                raise ValueError('Multiply-detail mapping requires audited static constants')
            fallback = variant = '_0_5_1_0_0_0_1'
            template_name = template_name.rsplit('\\',1)[0] + '\\' + variant
        neutral_detail = (not sky_bridge_generic and not sky_bridge_soft and group == 'rmhg' and variant == '_0_1_1_0_0_1_1'
                          and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\shaders\\lighting\\'))
        if neutral_detail:
            if s.u(post+80) or s.u(post+92):
                raise ValueError('Neutral-detail mapping requires static illumination')
            fallback = variant = '_0_5_1_0_0_1_1'
            template_name = template_name.rsplit('\\',1)[0] + '\\' + variant
        neutral_illum = (group == 'rmhg' and variant == '_0_0_1_0_0_0_0'
                         and s.name(datum & 65535) == r'levels\multi\s3d_powerhouse\sky_settlement\shaders\s3d_thunderhead')
        if neutral_illum:
            fallback = variant = '_0_1_1_0_0_0_0'
            template_name = template_name.rsplit('\\', 1)[0] + '\\' + variant
        native_sky_shader = (group == 'rmhg' and variant == '_6_5_3_0_0_0_0'
                             and s.name(datum & 65535) == r'levels\multi\s3d_powerhouse\sky_settlement\shaders\s3d_heavy_clouds')
        if native_sky_shader:
            # Citadel's clouds_2 uses the same six textures/float constants,
            # albedo overlay, illumination-detail and alpha blend. Its standard
            # shader family also exposes diffuse lighting: verify native sky.
            fallback = variant = '_6_0_0_0_0_0_5_3_0_0'
            template_name = 'shaders\\shader_templates\\' + variant
        native_alpha_sky = (group == 'rmhg' and variant == '_0_4_3_0_0_0_0'
                            and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\'))
        if native_alpha_sky:
            fallback = variant = '_0_0_0_0_0_0_4_3_0_0'
            template_name = 'shaders\\shader_templates\\' + variant
            native_sky_shader = True
        sky_bridge_lamp = (group == 'rmhg' and variant == '_0_8_0_0_0_3_0'
                           and s.name(datum & 65535).startswith('levels\\multi\\s3d_sky_bridgenew\\shaders\\lighting\\'))
        if sky_bridge_lamp:
            allowed = {'ceiling_lamp_01','fluorescent_lamp_cold','fluorescent_lamp_ceiling_cold'}
            if s.name(datum & 65535).rsplit('\\',1)[-1] not in allowed or s.u(post+92):
                raise ValueError('Sky Bridge lamp specialization changed')
            fallback = variant = '_2_8_0_0_0_1_0'
            template_name = 'shaders\\halogram_templates\\' + variant
            donors[variant] = 'sandbox.map'
        if sky_bridge_soft:
            fallback = variant = '_0_1_1_0_0_0_1'
            template_name = 'shaders\\halogram_templates\\' + variant
            donors[variant] = 'sandbox.map'
        if sky_bridge_generic:
            fallback=variant='_0_1_1_0_0_0_1'
            template_name='shaders\\halogram_templates\\'+variant
            donors[variant]='sandbox.map'
            sky_bridge_soft=False
            native_sky_shader=native_unlit_sky=native_alpha_sky=False
            neutral_edge=neutral_warp=neutral_detail=neutral_illum=multiply_detail=lightvolume=computer_overlay=False
        output_group = 'rmsh' if native_sky_shader else group
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
            # Compiled templates must retain their donor's shared shader graph.
            # Identical rmdf/glvs names across disc maps do not imply identical
            # programs or entry-point tables (e.g. Chillout versus Zanzibar).
            native.donor_scoped = True
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
                if sky_bridge_generic:
                    if offset==72 and 'layer_groups' in generic_profile:
                        values=s.unpack('4f',s.block(post+28,16)[source_names.index('layers_of_4')])
                        if values!=(float(generic_profile['layer_groups']),)*4 or any(s.unpack('HBB',r)[2]==source_names.index('layers_of_4') for r in s.block(post+80,4)):
                            raise ValueError('Hologram layer specialization changed')
                    usage={72:'4',84:'5',96:'6',108:'0'}[offset]
                    if source_names!=generic_profile['names'][usage]:raise ValueError('Source hologram parameter order changed')
                    continue
                if sky_bridge_soft:
                    target_names += {72:['overlay_map','overlay_tint','overlay_intensity','soft_fresnel_power','soft_z_range'],84:[],96:['use_soft_fresnel','use_soft_z'],108:['overlay_map']}[offset]
                    if set(source_names)!=set(target_names):raise ValueError('Soft fade parameters changed')
                    if offset==72:float_indices=[source_names.index(n) for n in target_names]
                    elif offset==108:texture_indices=[source_names.index(n) for n in target_names]
                    elif source_names!=target_names:raise ValueError('Soft fade boolean order changed')
                    continue
                if sky_bridge_lamp and offset in (72,108):
                    target_names += ['base_map','detail_map']
                    if set(source_names) != set(target_names):
                        raise ValueError('Sky Bridge lamp parameter set changed')
                    indices=[source_names.index(n) for n in target_names]
                    if offset==72:
                        float_indices=indices
                        values=s.unpack('4f',s.block(post+28,16)[source_names.index('layers_of_4')])
                        if values != (4.,)*4:
                            raise ValueError('Sky Bridge lamp must have four static layer groups')
                    else: texture_indices=indices
                    continue
                if native_unlit_sky and offset in (72,108):
                    extras = {'base_map', 'detail_map'}
                    if set(target_names)-set(source_names)!=extras or not set(source_names).issubset(target_names):
                        raise ValueError('Unlit sky donor parameters changed')
                    indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    if offset == 72:
                        float_indices = indices
                        float_defaults = {j:0.0 for j,n in enumerate(target_names) if n in extras}
                    else:
                        texture_indices = indices
                    continue
                if neutral_detail and offset in (72,108):
                    if set(target_names)-set(source_names)!={'self_illum_detail_map'} or not set(source_names).issubset(target_names):
                        raise ValueError('Neutral-detail donor parameter layout changed')
                    indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    if offset==72:
                        float_indices=indices
                        float_defaults={target_names.index('self_illum_detail_map'):0.0}
                    else:
                        texture_indices=indices
                    continue
                if multiply_detail and offset in (72,108):
                    mapped = [n.replace('self_illum_detail_map','overlay_map') for n in target_names]
                    omitted = {'overlay_tint','overlay_intensity'} if offset==72 else set()
                    if set(source_names)-set(mapped)!=omitted or any(n not in source_names for n in mapped):
                        raise ValueError('Multiply-detail donor layout changed')
                    indices = [source_names.index(n) for n in mapped]
                    if offset==72:
                        float_indices=indices
                        omitted_constants=sorted(omitted)
                    else:
                        texture_indices=indices
                    continue
                if neutral_warp and offset in (72,108):
                    extras = ({'warp_map','warp_amount_x','warp_amount_y','edge_fade_edge_tint',
                               'edge_fade_center_tint','edge_fade_power'} if offset==72 else {'warp_map'})
                    if set(target_names)-set(source_names)!=extras or not set(source_names).issubset(target_names):
                        raise ValueError('Neutral warp donor parameter layout changed')
                    indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    if offset==72:
                        float_indices=indices
                        float_defaults={j:(1.0 if n.startswith('edge_fade_') else 0.0)
                                        for j,n in enumerate(target_names) if n in extras}
                    else:
                        texture_indices=indices
                    continue
                if neutral_illum and offset in (72,108):
                    extras = {'self_illum_map','self_illum_color','self_illum_intensity'} if offset == 72 else {'self_illum_map'}
                    if set(target_names)-set(source_names) != extras or not set(source_names).issubset(target_names):
                        raise ValueError('Disabled illumination donor parameters changed')
                    indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    if offset == 72:
                        float_indices = indices
                        float_defaults = {j:0.0 for j,n in enumerate(target_names) if n in extras}
                    else:
                        texture_indices = indices
                    continue
                if native_sky_shader and not native_alpha_sky and offset == 96:
                    if source_names or target_names != ['no_dynamic_lights']:
                        raise ValueError('Native cloud boolean layout changed')
                    if s.u(post+52):raise ValueError('Unexpected cloud source boolean constants')
                    continue
                if neutral_edge and offset == 72:
                    extras = {'edge_fade_edge_tint', 'edge_fade_center_tint', 'edge_fade_power'}
                    if set(target_names) - set(source_names) != extras or not set(source_names).issubset(target_names):
                        raise ValueError('Neutral edge-fade donor constants changed')
                    float_indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    float_defaults = {j:1.0 for j,n in enumerate(target_names) if n in extras}
                    continue
                if lightvolume and offset in (72,108):
                    added = set(target_names)-set(source_names)
                    allowed = {'self_illum_map','self_illum_color','self_illum_intensity','layer_depth','layer_contrast','layers_of_4','texcoord_aspect_ratio','depth_darken'} if offset == 72 else {'self_illum_map','overlay_multiply_map'}
                    if not added.issubset(allowed) or not set(source_names).issubset(target_names):
                        raise ValueError('Light-volume donor parameters changed')
                    indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    if offset == 72:
                        float_indices = indices
                        float_defaults = {j:(1. if n in {'layer_contrast','layers_of_4','texcoord_aspect_ratio','depth_darken'} else 0.) for j,n in enumerate(target_names) if n not in source_names}
                    else:
                        texture_indices = indices
                    continue
                if lightvolume and offset == 84:
                    if source_names or target_names != ['layers_of_4']:
                        raise ValueError('Light-volume integer constants changed')
                    continue
                if computer_overlay and offset in (72,108):
                    omitted = {'overlay_map', 'overlay_tint', 'overlay_intensity'} if offset == 72 else {'overlay_map'}
                    if [n for n in source_names if n not in omitted] != target_names:
                        raise ValueError('Computer overlay donor parameter mismatch')
                    if offset == 72:
                        float_indices = [source_names.index(n) for n in target_names]
                        omitted_constants = sorted(omitted)
                    else:
                        texture_indices = [source_names.index(n) for n in target_names]
                    continue
                if inactive_environment and source_names != target_names:
                    raise ValueError('Diffuse-only terrain has active environment parameters')
                if single_layer and offset in (72, 108):
                    extra = 'env_tint_color' if offset == 72 else 'environment_map'
                    if set(target_names) - set(source_names) != {extra}:
                        raise ValueError('Unexpected One-layer donor parameters')
                    indices = [source_names.index(n) if n in source_names else -1 for n in target_names]
                    if offset == 72:
                        if set(source_names) - set(target_names) != {'blend_map'}:
                            raise ValueError('One-layer mapping drops an active parameter')
                        float_indices = indices
                        float_defaults = {target_names.index(extra): 0.0}
                        omitted_constants = ['blend_map']
                    else:
                        texture_indices = indices
                elif prt_two_layer and offset in (72, 108):
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
                    if (group == 'rmtr' and source_variant == '_0_1_1_2_2_0'
                            and offset == 72 and omitted == {'blend_map'}
                            and [n for n in source_names if n != 'blend_map'] == target_names
                            and 'blend_map' not in [i.source_strings.text(s.u(row))
                                                   for row in s.block(source_template + 108, 4)]):
                        # Official H3EK retains an unused blend UV constant in
                        # this one-layer permutation. No blend sampler exists;
                        # preserve every active constant in native order.
                        float_indices = [source_names.index(n) for n in target_names]
                        omitted_constants = ['blend_map']
                    elif reach_grid and offset == 72 and [n for n in target_names if n != 'self_illum_color'] == source_names:
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
                            and (source_options[1] == 0 or variant.endswith('_0') or getattr(i, 'stock_forge_palette', False) or getattr(i, 'battle_canyon', False))
                            and omitted and all(n.startswith('environment_specular_contribution_m_') for n in omitted)
                            and [n for n in source_names if n not in omitted] == target_names):
                        float_indices = [source_names.index(n) for n in target_names]
                        omitted_constants = sorted(omitted)
                    else:
                        raise ValueError(f'Terrain parameter order differs: {template_name} field {offset}: {source_names} vs {target_names}')
            options = [s.unpack('h', r)[0] for r in s.block(root + 16, 2)]
            if options != source_options:
                raise ValueError('Terrain root options differ from template variant')
            definition = native.import_tag(lookup['rmdf', 'shaders\\' + ('shader' if native_sky_shader else 'terrain' if group == 'rmtr' else 'halogram')])
            _, template = native.import_tag(target_template)
            lamp_evidence = None
            if sky_bridge_lamp:
                from sky_bridge_lamp import bind_lamp_template
                template,lamp_evidence=bind_lamp_template(i.materials,template,
                    Path(__file__).resolve().parents[4]/'work/sky-bridge/lamp-native-01')
            if sky_bridge_soft:
                from sky_bridge_soft import bind_soft_template, bind_soft_vertices
                directory=Path(__file__).resolve().parents[4]/'work/sky-bridge/soft-native-01'
                template,lamp_evidence=bind_soft_template(i.materials,template,directory)
                definition=bind_soft_vertices(i.materials,definition,directory)
            if sky_bridge_generic:
                from sky_bridge_hologram import bind_hologram_template
                template,lamp_evidence=bind_hologram_template(i.materials,template,generic_directory)
                if generic_profile['soft']:
                    from sky_bridge_soft import bind_soft_vertices
                    definition=bind_soft_vertices(i.materials,definition,Path(__file__).resolve().parents[4]/'work/sky-bridge/soft-native-01')
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
                    supported = kind in (0, 1, 5, 6) or (kind in (2,3,4) and s.name(datum&65535).startswith('levels\\multi\\s3d_sky_bridgenew\\'))
                    if (input_id and not (glow or seat_power)) or range_id or not 0 < period < float('inf') or not supported:
                        raise ValueError(f'{s.name(datum & 65535)}: unsupported hologram animation {kind}, function size {len(function)}')
                    convert_function(function)  # Validate the complete function structure.
            baked_computer = None
            if computer_overlay:
                from hologram_overlay import bake
                baked_computer, overlay_intensity = bake(i.materials, post)
            textures = bytearray()
            rows = s.block(post + 16, 28)
            if len(rows) != s.u(source_template + 108):
                raise ValueError('Terrain texture count differs from template')
            if texture_indices is not None:
                rows = [rows[index] if index >= 0 else None for index in texture_indices]
            for row in rows:
                if row is None and (lightvolume or neutral_illum or neutral_warp or neutral_detail or native_unlit_sky):
                    bitmap = i.native_assets.import_named(('bitm', r'shaders\default_bitmaps\bitmaps\color_white'))
                    if bitmap is None:raise ValueError('Native white bitmap missing')
                    textures.extend(b'bitm' + bytes(8) + struct.pack('>IhBBBbH', bitmap[1], 0, 0, 0, 0, -1, 0))
                    continue
                if row is None and single_layer:
                    bitmap = i.native_assets.import_named(('bitm', r'shaders\default_bitmaps\bitmaps\default_dynamic_cube_map'))
                    if bitmap is None:raise ValueError('Native cube fallback missing')
                    textures.extend(b'bitm' + bytes(8) + struct.pack('>IhBBBbH', bitmap[1], 0, 0, 1, 0, -1, 0))
                    continue
                bitmap = s.u(row + 12)
                index, address, filtering, comparison, external, transform, pad, animation, pad2 = s.unpack('h4BbBhH', row + 16)
                if comparison or pad or pad2 or (animation and not overlays):
                    raise ValueError('Unsupported terrain sampler routing')
                if index != 0:
                    raise ValueError('Terrain texture array/sub-image is unsupported')
                retained_animation = 0
                if (group == 'rmhg' and animation and
                        (sky_bridge_generic or s.name(datum & 65535).startswith('levels\\multi\\s3d_powerhouse\\sky_settlement\\'))):
                    # Conversion retains overlay order. Native sampler ranges
                    # use the same low-10-bit start/high-6-bit count encoding.
                    if (not animation >> 10 or
                            (animation & 1023) + (animation >> 10) > len(overlays)):
                        raise ValueError('Powerhouse cloud sampler animation range is invalid')
                    if not (sky_bridge_generic or computer_overlay or lightvolume or neutral_edge or neutral_warp or native_sky_shader or native_unlit_sky):
                        raise ValueError('Cloud sampler animation requires converted functions')
                    retained_animation = animation
                if float_indices is not None and transform >= 0:
                    if transform not in float_indices:
                        raise ValueError('Terrain sampler uses omitted transform')
                    transform = float_indices.index(transform)
                original_names = i.materials.parameters(s, i.source_strings, post)[0]
                original_rows = s.block(post + 16, 28)
                if computer_overlay and row == original_rows[original_names.index('self_illum_map')]:
                    bitmap = baked_computer
                elif native_sky_shader and not native_alpha_sky and row == original_rows[original_names.index('detail_map_overlay')]:
                    # Source halogram has material-none, unlike the donor's
                    # diffuse-only model. Preserve alpha and illumination while
                    # eliminating only that added diffuse contribution.
                    from cloud_alpha_mask import bake
                    bitmap = bake(i.materials, bitmap)
                else:
                    bitmap = i.materials.bitmap(bitmap) if bitmap != 0xffffffff else bitmap
                textures.extend((b'bitm' if bitmap != 0xffffffff else b'\xff' * 4) + bytes(8)
                                + struct.pack('>IhBBBbH', bitmap, index, address, filtering, external, transform, retained_animation))
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
            if lightvolume:
                struct.pack_into('>III',output,40,1,b.alloc(struct.pack('>I',1)),0)
            if multiply_detail:
                source_names = i.materials.parameters(s,i.source_strings,post)[1]
                source_values = {n:s.unpack('4f',r) for n,r in zip(source_names,s.block(post+28,16))}
                tint, intensity = source_values['overlay_tint'], source_values['overlay_intensity']
                if len(set(intensity))!=1 or tint[3]!=1.0:
                    raise ValueError('Multiply-detail constants differ from audited scalar/tint')
                names = [native_strings.text(donor.u(r)) for r in donor.block(target_root+72,4)]
                pointer = struct.unpack_from('>I',output,32)[0]
                color = source_values['self_illum_color']
                b.put(pointer+names.index('self_illum_color')*16,'4f',*(color[j]*tint[j] for j in range(4)))
                b.put(pointer+names.index('self_illum_intensity')*16,'4f',
                      *(v*intensity[0]/4.59479 for v in source_values['self_illum_intensity']))
            if neutral_detail:
                names = [native_strings.text(donor.u(r)) for r in donor.block(target_root+72,4)]
                pointer = struct.unpack_from('>I',output,32)[0]
                at = pointer+names.index('self_illum_intensity')*16
                values=struct.unpack('>4f',b.read(at,16))
                b.put(at,'4f',*(v/4.59479 for v in values))
            if computer_overlay:
                names = [native_strings.text(donor.u(r)) for r in donor.block(target_root+72,4)]
                pointer = struct.unpack_from('>I', output, 32)[0]
                at = pointer + names.index('self_illum_intensity')*16
                values = struct.unpack('>4f', b.read(at,16))
                b.put(at, '4f', *(v*overlay_intensity for v in values))
            powerhouse_cloud_gain = None
            if (native_unlit_sky
                    and str(s.file.name).replace('\\', '/').rsplit('/', 1)[-1] == 's3d_powerhouse.map'
                    and s.name(datum & 65535) == r'levels\multi\s3d_powerhouse\sky_settlement\shaders\s3d_cloud_blend'):
                names = [native_strings.text(donor.u(r)) for r in donor.block(target_root+72,4)]
                pointer = struct.unpack_from('>I', output, 32)[0]
                at = pointer + names.index('self_illum_intensity')*16
                if struct.unpack('>4f', b.read(at, 16)) != (1.,)*4:
                    raise ValueError('Powerhouse cloud intensity changed; recheck native lighting')
                # Native matched-view correction: avoid amplifying the linear
                # BC1 cloud's dark color steps into a bright colored fringe.
                # Preserve all sky geometry, texture mips and live animation.
                powerhouse_cloud_gain = .25
                b.put(at, '4f', *(.25,)*4)
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
                        if (single_layer or (source_variant == '_0_1_1_2_2_0' and omitted_constants == ['blend_map'])) and index not in float_indices and index == 0:
                            # The source single-layer shader exposes an unused blend transform.
                            struct.pack_into('>h', output, offset, -1)
                            continue
                        if index not in float_indices:
                            raise ValueError('Terrain query references an omitted parameter')
                        struct.pack_into('>h', output, offset, float_indices.index(index))
            converted_animations = 0
            # Reach Forge light markers compile to this same native H3
            # halogram permutation. Preserve their flash functions through
            # the register mapper, which rejects unmapped/ambiguous routes.
            native_light_marker = (group == 'rmhg' and variant == '_2_1_1_0_0_0_1'
                                   and not fallback and float_indices is None
                                   and texture_indices is None)
            if native_light_marker and any(s.unpack('h', row + 24)[0]
                                           for row in s.block(post + 16, 28)):
                raise ValueError('Light-marker sampler animation needs explicit range conversion')
            if (s.name(datum&65535).startswith('levels\\multi\\s3d_sky_bridgenew\\') or sky_bridge_generic or sky_bridge_soft or computer_overlay or lightvolume or neutral_edge or neutral_warp or native_sky_shader or native_unlit_sky or native_light_marker) and overlays:
                from material_animation import convert_material_animation
                converted_animations = convert_material_animation(i.materials, post, output)
            ss = load_schema(i.source, group, i.reference)
            ds = ET.parse(i.reference / 'plugins' / f'{output_group}.xml').getroot()

            def reference(value):
                if value != s.u(root + 12):
                    raise ValueError('Unexpected terrain root dependency')
                return definition

            converter = MetadataConverter(s, b, i.source_strings, i.target_strings, reference,
                special_block=lambda at, sf, df, path: bytes(output) if sf.get('name') == 'Postprocess' else None)
            payload = bytearray(converter.convert(root, ss, ds, group + ':' + s.name(datum & 65535)))
            if native_sky_shader:
                native_options = [int(v) for v in variant.split('_')[1:]]
                struct.pack_into('>III', payload, 16, len(native_options), b.alloc(struct.pack('>10h', *native_options)), 0)
            elif fallback:
                count, pointer = struct.unpack_from('>II', payload, 16)
                target_options = [int(v) for v in variant.split('_')[1:]]
                if count != len(target_options) and not (group == 'rmhg' and count == 9 and len(target_options) == 7):raise ValueError('Terrain fallback option count')
                for n,value in enumerate(target_options):b.put(pointer+n*2,'h',value)
            if group == 'rmhg' and not native_sky_shader:
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
            owner, _ = i.registry.newtag(output_group, payload)
            self.done[datum] = (output_group, owner)
            i.materials.report.append({'source': s.name(datum & 65535), 'retail_template': template_name,
                'donor_only_cloud_diffuse_removed': native_sky_shader and not native_alpha_sky,
                'powerhouse_cloud_brightness_gain': powerhouse_cloud_gain,
                'native_unlit_sky_without_edge_fade': native_unlit_sky,
                'compiled_sky_bridge_lamp': lamp_evidence, 'native_donor': donors[variant], 'donor_shader_graph_preserved': True, 'baked_static_computer_overlay': computer_overlay, 'coincident_lightvolume_layers': lightvolume, 'neutral_edge_fade': neutral_edge, 'disabled_extra_illumination': neutral_illum, 'native_cloud_shader_family': native_sky_shader,
                'converted_source_animations': converted_animations, 'neutral_extra_warp': neutral_warp, 'neutral_extra_detail': neutral_detail, 'static_multiply_as_detail': multiply_detail, 'source_template_variant': source_variant, 'fallback_template_variant': fallback,
                'approximation': bool(fallback or (overlays and not converted_animations) or suppressed_specular or omitted_constants),
                'ambient_prt_two_layer_mapping': prt_two_layer,
                'inactive_third_layer_blue_zeroed': prt_two_layer,
                'difference': ('Terrain UV animation frozen at authored initial transform' if group == 'rmtr'
                               else 'Hologram color/brightness/UV functions frozen at authored constant values') if overlays and not converted_animations else None,
                'frozen_inputs': sorted({i.source_strings.text(s.u(row + 4)) for row in overlays if s.u(row + 4)}) if not converted_animations else [],
                'textures_imported': len(textures) // 24, 'all_layer_parameters_preserved': not suppressed_specular,
                'terrain_specular_suppressed': suppressed_specular,
                'unused_mcc_environment_constants_omitted': omitted_constants, 'native_constant_defaults': float_defaults})
            return self.done[datum]
        except Exception:
            i.failed = True
            raise
        finally:
            donor.close()
