"""Opt-in, exact-map native audio substitutions for a Mythic-only build.

These are purpose equivalents, not claims that unavailable MCC waveforms are
identical. Only snd! leaves change: authored parent effects, placements and
loop scheduling remain. The caller must explicitly opt in before configure().
"""
from pathlib import Path
from cache_reader import Cache

BUILD = 'Jan  3 2024 10:08:58'
SCENARIOS = {
    r'levels\multi\warlock\warlock': ('warlock', BUILD),
    r'levels\multi\h2_elongation\h2_elongation': ('h2_elongation', BUILD),
    r'halo_2\levels\foundation\foundation': ('foundation', BUILD),
    r'levels\multi\resuscitation\resuscitation': ('resuscitation', BUILD),
    r'levels\multi\sancr\sancr': ('sancr', BUILD),
    r'levels\multi\cex_beavercreek\cex_beavercreek': ('cex_beavercreek', BUILD),
    r'levels\multi\dune\dune': ('dune', 'Jun 27 2023 08:39:36'),
    r'levels\multi\forge_halo\forge_halo': ('forge_halo', BUILD),
    r'levels\multi\s3d_powerhouse\s3d_powerhouse': ('s3d_powerhouse', BUILD),
    r'levels\multi\s3d_sky_bridgenew\s3d_sky_bridgenew': ('s3d_sky_bridgenew', BUILD),
}


def replacements(map_name):
    """Return a fresh exact-name table of target and audible difference."""
    out = {}
    def add(source, target, difference):
        if source in out:
            raise ValueError('Duplicate Mythic audio policy: ' + source)
        out[source] = {'target': target, 'difference': difference}
    if map_name in ('warlock', 'foundation', 'resuscitation', 'sancr',
                    'cex_beavercreek', 'dune', 'forge_halo', 's3d_sky_bridgenew'):
        add(r'sound\weapons\autoturret\autoturret_deploy\autoturret_deploy',
            r'sound\characters\sentinel\sentinel_ready',
            'Native Sentinel ready cue replaces the autoturret deployment recording.')
        for part in ('in', 'loop', 'out'):
            add('sound\\weapons\\autoturret\\autoturret_fire_loop\\track1\\' + part,
                'sound\\characters\\sentinel\\sentinel_gun\\sent_gun\\' + part,
                'Native Sentinel beam sound replaces the autoturret beam recording; parent start/loop/end scheduling remains.')
    if map_name in ('cex_beavercreek', 'forge_halo', 's3d_sky_bridgenew'):
        add(r'sound\weapons\equipment\invisibility\invisibility_deactivate',
            r'sound\weapons\equipment\bubble_shield\bubble_deativate',
            'Native Bubble Shield shutdown cue replaces invisibility shutdown audio; equipment behavior remains unchanged.')
    if map_name in ('warlock', 'sancr'):
        add(r'sound\visual_fx\cascading_stream_splash\cascading_stream_splash\loop',
            r'sound\levels\riverworld\sound_scenery\water_against_surface\water_against_surface\loop',
            'Native Valhalla moving-water loop replaces the cascading-stream splash recording.')
    if map_name == 'h2_elongation':
        for part,target in {
            'in': r'sound\device_machines\doors_lifts\voi_door_sm_open',
            'loop': r'sound\levels\dlc\docks\sound_scenery\conveyor_under_floor\conveyor_under_floor\loop',
            'out': r'sound\device_machines\doors_lifts\voi_door_sm_close',
        }.items():
            add('sound\\device_machines\\doors_lifts\\hangar02_loop\\track1\\'+part,target,
                'Native industrial door/conveyor audio replaces hangar-door audio; source attachment and loop timing remain.')
        for source,target,difference in [
            (r'sound\levels\020_base\sound_scenery\stationary_cap_ship\track1\loop',
             r'sound\levels\dlc\armory\base_hangar\hangar\loop',
             'Native Rat\'s Nest hangar ambience replaces the stationary capital-ship hum.'),
            (r'sound\visual_fx\big_explosions_hc', r'sound\visual_fx\h3_lrg_explosion',
             'Native large explosion replaces the High Charity explosion recording.'),
            (r'sound\visual_fx\cov_damage_large_hc', r'sound\vehicles\damage_effects\cov_damage_large',
             'Native large Covenant damage cue replaces the High Charity damage recording.'),
            (r'sound\vehicles\pelican\pelican_engine_lod\track1\loop',
             r'sound\levels\dlc\armory\sound_scenery\pelican_engine_lod\track1\loop',
             'Native Rat\'s Nest Pelican LOD recording; shared permutation names, different sample lengths.'),
            (r'sound\vehicles\phantom\phantom_destroyed',
             r'sound\materials\gear\covy_watchtower_destroyed\phantom_destroyed',
             'Native Snowbound Phantom-derived destruction cue; shared permutation names, not byte-identical source audio.'),
            (r'sound\vehicles\phantom\phantom_destroyed_lod_phantom',
             r'sound\vehicles\phantom\phantom_destroyed_lod',
             'Native Phantom destruction LOD cue; shared permutation names, not byte-identical source audio.'),
            (r'sound\vehicles\phantom\phantom_engine_lod\track2\loop',
             r'sound\vehicles\banshee\banshee_engine_lod\banshee_lod\loop',
             'Native Banshee distant engine replaces the unavailable Phantom distant engine recording.'),
            (r'sound\vehicles\hornet\hornet_engine_lod\track1\loop',
             r'sound\vehicles\hornet\hornet_engine_notflock_lod\track1\loop',
             'Native playable-Hornet LOD engine replaces the ambient-flock Hornet recording.'),
        ]:add(source,target,difference)
    if map_name == 'resuscitation':
        for part in ('open','close'):
            add('sound\\vehicles\\spectre\\'+part,'sound\\vehicles\\wraith\\wraith_'+part,
                'Native Wraith hatch cue replaces the Spectre hatch recording; the custom vehicle remains unchanged.')
        for part in ('in','loop'):
            add('sound\\device_machines\\lightbridge_crater\\lightbridge\\'+part,
                'sound\\levels\\snowbound\\snowbound_airlocks\\track1\\'+part,
                'Native Snowbound forcefield audio replaces the lightbridge recording.')
        add(r'sound\vehicles\monitor\guilty_pre_explodes',
            r'sound\weapons\equipment\power_drain\power_drain_flash',
            'Native Power Drain discharge replaces the Monitor pre-explosion cue; source effect timing remains.')
        add(r'sound\visual_fx\sparks_cov_large',r'sound\visual_fx\sparks_medium',
            'Native medium electrical sparks replace the large Covenant sparks recording.')
        add(r'sound\device_machines\scarab\scarab_mech_break_small',
            r'sound\vehicles\damage_effects\cov_damage_small',
            'Native small Covenant damage cue replaces the Scarab mechanical-break recording.')
    if map_name == 'sancr':
        for source,target,difference in [
            (r'sound\levels\010_jungle\sound_scenery\frogs_stereo_huge\details\frogs_stereo_huge',
             r'sound\levels\gaurdian\gaurdian\details\frog_stereo_huge',
             'Native Guardian frog family, shared permutation names but different sample lengths.'),
            (r'sound\levels\010_jungle\sound_scenery\mosquitos_point\details\mosquitos',
             r'sound\levels\zanzibar\mosquitos\mosquitos',
             'Native Last Resort mosquito family, shared permutation names but different sample lengths.'),
            (r'sound\levels\010_jungle\sound_scenery\waterfall_off_the_edge\off_the_edge\loop',
             r'sound\levels\riverworld\sound_scenery\waterfall_far\waterfall_far\loop',
             'Native Valhalla distant waterfall replaces the jungle waterfall recording.'),
            (r'sound\levels\010_jungle\sound_scenery\waterfall_bottom_of_med\waterfall_bottom_of_med\loop',
             r'sound\levels\riverworld\sound_scenery\waterfall_close_churning\waterfall_close_churning\loop',
             'Native Valhalla churning waterfall replaces the jungle waterfall-base recording.'),
            (r'sound\levels\010_jungle\sound_scenery\crashed_ship\crashed_ship\loop',
             r'sound\levels\shrine\shrine_ship\shrine_ship\loop',
             'Native Sandtrap ship hum replaces the crashed-ship ambience recording.'),
            (r'sound\levels\010_jungle\sound_scenery\crashed_ship\details\creaks',
             r'sound\materials\hard\metal_thin\hum_object_rattly_small',
             'Native metallic rattles replace large ship creaks, changing the scale/timbre of the detail cue.'),
            (r'sound\levels\010_jungle\jungle4\details\stereo_jungle_detail',
             r'sound\levels\gaurdian\gaurdian\details\gaurdian_quad_details',
             'Native Guardian forest detail replaces the jungle detail recording and its spatial presentation.'),
            (r'sound\levels\010_jungle\jungle4\details\backwards_chirping',
             r'sound\levels\riverworld\sound_scenery\backward_eagle\details\backward_eagle',
             'Native Valhalla reversed bird call replaces the jungle backwards-chirp recording.'),
            (r'sound\levels\010_jungle\jungle4\details\mosquitos',
             r'sound\levels\zanzibar\mosquitos\mosquitos',
             'Native Last Resort mosquito family replaces the jungle mosquito detail.'),
            (r'sound\levels\010_jungle\jungle4\details\mono_thunder',
             r'sound\levels\salvation\forerunner_cathedral_outside\details\mono_thunder',
             'Native Epitaph thunder family, shared permutation names but different sample lengths.'),
            (r'sound\levels\010_jungle\waterfall_layer\waterfall_layer\loop',
             r'sound\levels\riverworld\sound_scenery\waterfall_far\waterfall_far\loop',
             'Native Valhalla distant waterfall replaces the ambience waterfall layer.'),
        ]:add(source,target,difference)
        for side in ('front_speakers','rear_speakers'):
            add('sound\\levels\\010_jungle\\jungle4\\'+side+'\\loop',
                'sound\\levels\\gaurdian\\gaurdian\\'+side+'\\loop',
                'Native Guardian forest ambience replaces the jungle bed, retaining separate native front/rear roles.')
            add('sound\\levels\\010_jungle\\jungle4_cave\\'+side+'\\loop',
                'sound\\levels\\gaurdian\\gaurdian_half_inside\\'+side+'\\loop',
                'Native sheltered Guardian ambience replaces the jungle-cave bed, retaining separate front/rear roles.')
    if map_name == 'cex_beavercreek':
        prefix = 'sound\\levels\\dlc\\cex_beaverc\\'
        for source,target,difference in [
            (r'sound_scenery\ca_water_light_lapping\light_lapping\loop',
             r'sound\levels\deadlock\sound_scenery\water_light_lapping\light_lapping\loop',
             'Native High Ground lapping water replaces the Reach lapping-water recording.'),
            (r'sound_scenery\ca_water_standing\water_standing\loop',
             r'sound\levels\riverworld\sound_scenery\water_against_surface\water_against_surface\loop',
             'Native Valhalla surface-water loop replaces the standing-water recording.'),
            (r'sound_scenery\ca_computer_int\track1\loop',
             r'sound\levels\dlc\bunkerworld\sound_scenery\computer_telemetry\computer_telemetry\loop',
             'Native Standoff computer telemetry replaces the Reach computer recording.'),
            (r'sound_scenery\ca_tree_rustle\track1\loop',
             r'sound\levels\dlc\bunkerworld\sound_scenery\stereo_leaves_details\details\stereo_leaves',
             'Native Standoff leaf-rustle permutations replace the Reach tree-rustle loop; source scheduling remains.'),
            (r'sound_scenery\ca_lc_energy_distant\lc_energy_distant\loop',
             r'sound\levels\chill\sound_scenery\energy_beam\energy_beam\loop',
             'Native Narrows energy-beam hum replaces the distant-energy recording.'),
            (r'sound_scenery\ca_beaver_wheel_new\track1\loop',
             r'sound\levels\zanzibar\zanzibar_base_turbine_close\turbine_close\loop',
             'Native Last Resort turbine replaces the Reach wheel mechanism recording.'),
            (r'sound_scenery\ca_fluorescent_light\track1\loop',
             r'sound\levels\zanzibar\zanzibar_sound_scenery\flourescent_light\flourescent_light\loop',
             'Native Last Resort fluorescent-light hum replaces the Reach light recording.'),
            (r'cave_ambience\cave_ambience\loop',
             r'sound\levels\zanzibar\zanzibar_cave\zanzibar_cave\loop',
             'Native Last Resort cave ambience replaces the Reach cave recording.'),
            (r'cave_ambience\details\cave_water_drip',
             r'sound\levels\deadlock\sound_scenery\drips\details\drips',
             'Native High Ground water drips replace the Reach cave-drip recording.'),
        ]:add(prefix+source,target,difference)
        add(r'sound\levels\120_halo\sound_scenery\hq_under_glass\under_glass\loop',
            r'sound\levels\dlc\descent\sound_scenery\descent_tanks\bubbles\loop',
            'Native Assembly tank bubbles replace the under-glass machinery ambience.')
        for suffix in (r'halo_ext\loop',r'details\weird_bird',r'details\long_stereo_cicadas',
                       r'details\particulate_gusts',r'details\halo_ext_stereo_details'):
            add('sound\\levels\\100_citadel\\halo_ext\\'+suffix,
                'sound\\levels\\riverworld\\halo_ext\\'+suffix,
                'Native Valhalla Halo-exterior sample family, shared permutation names but different sample lengths.')
        for source,target,difference in [
            (r'halo_ext_ocean_layer\details\iceland_birds',
             r'sound\levels\zanzibar\zanzibar_sound_scenery\monopoint_seagulls\details\monopoint_seagulls',
             'Native Last Resort gulls replace one ocean-bird detail family.'),
            (r'halo_ext_ocean_layer\details\iceland_birds2',
             r'sound\levels\zanzibar\zanzibar_sound_scenery\earthcity_birds\details\birds',
             'Native Last Resort birds replace the second ocean-bird detail family.'),
            (r'halo_ext\details\pitched_dolphins',
             r'sound\levels\riverworld\sound_scenery\backward_eagle\details\backward_eagle',
             'Native Valhalla processed bird calls replace the pitched-dolphin ambience detail.'),
            (r'halo_ext\details\mono_thunder',
             r'sound\levels\salvation\forerunner_cathedral_outside\details\mono_thunder',
             'Native Epitaph thunder family, shared permutation names but different sample lengths.'),
        ]:add('sound\\levels\\100_citadel\\'+source,target,difference)
    if map_name == 'dune':
        for part in ('open','close'):
            add('h2\\sound\\vehicles\\spectre\\'+part,'sound\\vehicles\\wraith\\wraith_'+part,
                'Native Wraith hatch cue replaces the H2 Spectre hatch recording; custom vehicle behavior remains.')
        add(r'h2\sound\vehicles\spectre\spectre_turret_fire',
            r'sound\vehicles\spectre\spectre_turret_fire',
            'Native H3 Spectre-derived turret recording replaces the H2 custom-bank copy.')
        for side,target_side in (('l','left'),('r','right')):
            for part in ('in','loop','out'):
                add('h2\\sound\\vehicles\\spectre\\spectre_engine_'+side+'\\spectre_engine_'+side+'\\'+part,
                    'sound\\vehicles\\ghost\\ghost_'+target_side+'\\track1\\'+part,
                    'Native Ghost hovering-engine audio replaces Spectre engine audio; separate left/right and start/loop/end roles remain.')
        for part in ('in','loop','out'):
            add('h2\\sound\\vehicles\\creep\\creep_engine_left\\track1\\'+part,
                'sound\\vehicles\\wraith\\wraith_engine_left\\track1\\'+part,
                'Native Wraith hovering-engine audio replaces the Creep transport engine recording.')
        for source,target,difference in [
            (r'h2\sound\ambience\dune\jail_shield_death[jail_shield_death]',
             r'sound\weapons\equipment\bubble_shield\bubble_deativate',
             'Native shield shutdown cue replaces the H2 jail-shield failure recording.'),
            (r'h2\sound\ambience\dune\gate_loop\containment_shield',
             r'sound\levels\dlc\sidewinder\shield_barrier\track1\loop',
             'Native Avalanche shield barrier hum replaces the H2 containment-shield recording.'),
            (r'h2\sound\ambience\device_machines\zanzibar_gate_button\button_push\button_push[button_push]',
             r'sound\device_machines\zan_barricade\button_push',
             'Native Last Resort barricade button replaces the H2 Zanzibar button recording.'),
            (r'sound\levels\070_waste\sound_scenery\skittery_bugs_details\details\skittery_bugs_details',
             r'sound\levels\deadlock\deadlock_air\details\katydid_close',
             'Native High Ground insect calls replace skittering-bug ambience details.'),
            (r'h2\sound\ambience\dune\flyby_wind_from_outside\details\wind',
             r'sound\levels\zanzibar\zanzibar_sound_scenery\zanzibar_stereo_wind\details\whistley_gusts_low_short',
             'Native Last Resort gusts replace H2 flyby-wind details.'),
            (r'h2\sound\ambience\dune\zanzibar_ocean_loop\track1\loop',
             r'sound\levels\zanzibar\zanzibar_ocean_loop\track1\loop',
             'Native Last Resort ocean recording replaces the H2 Zanzibar ocean recording.'),
            (r'h2\sound\ambience\dune\zanzibar\loop',
             r'sound\levels\zanzibar\zanzibar_courtyard\fronts\loop',
             'Native Last Resort courtyard bed replaces the H2 Zanzibar bed and its spatial presentation.'),
            (r'h2\sound\ambience\dune\monopoint_seagulls\details',
             r'sound\levels\zanzibar\zanzibar_sound_scenery\monopoint_seagulls\details\monopoint_seagulls',
             'Native Last Resort gulls replace the H2 Zanzibar gull recordings.'),
        ]:add(source,target,difference)
        for path in (r'2way_teleporter_open\2way_teleporter_open\2way_teleporter_open[2way_teleporter_open]',
                     r'2way_teleporter_open\2way_teleporter_open2\2way_teleporter_open2[2way_teleporter_open2]',
                     r'2way_teleporter_open\2way_teleporter3\2way_teleporter3[2way_teleporter3]'):
            add('h2\\sound\\ambience\\device_machines\\'+path,
                r'sound\game_sfx\multiplayer\teleporter_activate',
                'Native H3 teleporter activation replaces this H2 opening cue; multiple authored event layers remain.')
        for loop in ('loop','loop2'):
            add('h2\\sound\\ambience\\device_machines\\2way_teleporter_collapsable\\teleporter_loop\\'+loop,
                r'sound\game_sfx\ui\teleport_loop\teleporter_loop\loop',
                'Native H3 teleporter hum replaces this H2 teleporter layer; both source layers remain scheduled.')
        for name in (r'sound\levels\010_jungle\sound_scenery\crashed_ship\crashed_ship\loop',
                     r'sound\levels\010_jungle\sound_scenery\crashed_ship\details\creaks'):
            item=replacements('sancr')[name];add(name,item['target'],item['difference'])
        # H2 weapon/vehicle equivalents are handled at whole-object scope by
        # generational_assets, not by replacing their subordinate audio here.
    if map_name == 's3d_powerhouse':
        for name in (r'sound\materials\havok\destructable_lcd_quiet',
                     r'sound\levels\110_hc\sound_scenery\destructable_lcd'):
            add(name,r'sound\materials\gear\computer_monitor\computer_monitor_hit',
                'Native H3 computer-monitor impact replaces LCD breakage; native gain/recording differs, including the quiet variant.')
        add(r'sound\objects\gear\human\residential\laptop_loop\laptop_loop\loop',
            r'sound\levels\dlc\lockout\sound_scenery\whirry_computer\whirry_computer\loop',
            'Native Blackout whirring computer replaces the laptop recording.')
    if map_name == 's3d_sky_bridgenew':
        add(r'sound\visual_fx\sparks_cov_large',r'sound\visual_fx\sparks_medium',
            'Native medium electrical sparks replace large Covenant spark recordings.')
        add(r'sound\visual_fx\sparks_cov_large_loop\sparky\loop',
            r'sound\levels\dlc\descent\sound_scenery\sparks_cov_large_loop\sparky\loop',
            'Native Assembly Covenant spark family, shared permutation names but different sample lengths.')
        for source,target,difference in [
            (r'sound\levels\040_voi\voi_exterior\track1\loop',
             r'sound\levels\dlc\docks\docks_outside\docks_outside\loop',
             'Native Longshore industrial-harbor ambience replaces Voi exterior ambience and its quad presentation.'),
            (r'sound\levels\040_voi\voi_rain_loop\track1\loop',
             r'sound\levels\riverworld\sound_scenery\waterfall_far\waterfall_far\loop',
             'Native sustained distant-water wash replaces the rain recording; this is not an identical rain sound.'),
            (r'sound\levels\030_outskirts\outskirts_tunnel_lrg\h2_tunnel\loop',
             r'sound\levels\dlc\docks\docks_inside_hallway\docks_inside_hallway\loop',
             'Native Longshore hallway ambience replaces the H2 tunnel bed.'),
            (r'sound\levels\030_outskirts\outskirts_tunnel_lrg\large_tunnel\loop',
             r'sound\levels\dlc\armory\base_hangar\hangar\loop',
             'Native Rat\'s Nest hangar ambience replaces the large tunnel layer.'),
        ]:add(source,target,difference)
        for number in (1,2,3):
            add('sound\\levels\\030_outskirts\\outskirts_tunnel_lrg\\details\\tunnel_details'+str(number),
                r'sound\levels\dlc\space_camp\space_camp_loops\details\ambient_clang1',
                'Native Orbital metallic ambient-clang family replaces this tunnel-detail family; source detail timing remains.')
    return out


def configure(importer):
    source = importer.source
    identities = [source.name(n) for n,t in source.tags.items() if t['group'] == 'scnr']
    build = bytes(source.data[0xA0:0xC0]).split(b'\0',1)[0].decode('ascii')
    if not source.mcc or len(identities) != 1 or identities[0] not in SCENARIOS:
        raise ValueError('No audited Mythic-only audio policy for this scenario')
    map_name, expected_build = SCENARIOS[identities[0]]
    if build != expected_build:
        raise ValueError('No audited Mythic-only audio policy for this cache build')
    present = {(t['group'],source.name(n)) for n,t in source.tags.items()}
    selected = {('snd!',name):item for name,item in replacements(map_name).items()
                if ('snd!',name) in present}
    aliases = dict(getattr(importer,'stock_asset_aliases',{}))
    for key,item in selected.items():
        value = ('snd!',item['target'],None)
        if key in aliases and aliases[key] != value:
            raise ValueError('Conflicting stock audio alias: ' + key[1])
        aliases[key] = value
    importer.stock_asset_aliases = aliases
    importer.mythic_audio_policy = selected
    return {'mode':'explicit Mythic-only native audio substitutions',
            'scenario':identities[0], 'build':build,
            'planned_source_leaves':len(selected),
            'waveform_identity_claimed':False,
            'parent_effects_and_placements_preserved':True}


def applied_replacements(importer):
    """Report only aliases actually resolved, using their actual native donor."""
    policy = getattr(importer,'mythic_audio_policy',{})
    output = []
    for row in importer.added:
        key = row.get('source_group'),row.get('source')
        if key not in policy or row.get('stock_equivalent') != policy[key]['target']:
            continue
        datum = int(row['datum'],16)
        sound = next((s for s in importer.sounds.report if int(s['datum'],16)==datum),None)
        if sound is not None:
            if sound.get('encoding') != 'native retail':
                raise ValueError('Mythic audio replacement did not use native sound packets')
            target = policy[key]['target'];path,_ = importer.sounds.native.paths[target]
            if path.name != sound['donor']:
                raise ValueError('Native audio donor report disagrees with selection')
            cache = Cache(path)
            close = True
        else:
            cache = importer.registry.cache
            close = False
        try:
            index = next(n for n,t in cache.tags.items()
                         if t['group']=='snd!' and cache.name(n)==policy[key]['target'])
            output.append({'source':key[1], 'target':policy[key]['target'],
                           'datum':row['datum'], 'donor':Path(cache.file.name).name,
                           'donor_tag_index':index,
                           'donor_resource':hex(cache.u(cache.tags[index]['offset']+24)),
                           'difference':policy[key]['difference'],
                           'native_resource_reuse':True, 'source_waveform_identical':False,
                           'serialized_packet_identity_verified':False,
                           'audible_runtime_verified':False})
        finally:
            if close:cache.close()
    return output
