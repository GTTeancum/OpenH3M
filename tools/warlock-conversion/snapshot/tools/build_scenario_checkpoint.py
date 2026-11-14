"""Assemble a scenario onto original Blackout/Last Resort or the accepted Warlock seed.

This is a Warlock/Resuscitation proof-of-concept, not a general MCC converter.
All outputs are confined to the explicitly supplied project's .local directory.
"""
from source_schema import load_schema
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import time
import xml.etree.ElementTree as ET

from cache_reader import Cache
from cache_registry import CacheRegistry
from map_builder import MapBuilder
from tag_importer import TagImporter
from fmod_audio import SoundBanks
from assemble_scenario import stage_primary_objects, stage_spawn_settings
from scenario_environment import stage_environment
from scenario_decals import stage_decals, verify_runtime_decals
from scenario_geometry import stage_geometry
from scenario_runtime import stage_runtime
from scenario_forge import stage_forge
from xexlib import Xex

ACCEPTED_SHA256 = '499f0516e016524f7f8a98ca580e4acb66c2b5d58403a5c755e4ed8f23de4279'


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def resource_salt(path):
    xex = Xex(str(path))
    image = xex.image()
    table = xex.hdrs[0x2ff]
    end = table + struct.unpack_from('>I', xex.raw, table)[0]
    for offset in range(table + 4, end, 16):
        if xex.raw[offset:offset + 8].rstrip(b'\0') == b'00':
            address, size = struct.unpack_from('>II', xex.raw, offset + 8)
            start = address - xex.image_base
            if size < 34 or start < 0 or start + 34 > len(image):
                raise ValueError('Invalid resource hash salt section')
            return image[start:start + 34]
    raise ValueError('Resource hash salt section 00 is absent')


def output_path(path, project):
    path = path.resolve()
    local = (project / '.local').resolve()
    if not local.is_relative_to(project) or not path.is_relative_to(local):
        raise ValueError('Generated files must stay inside the project .local directory')
    return path


def scenario_coverage(importer, stages):
    """Reject newly populated source blocks that no assembly stage handles."""
    handled = {'Structure BSPs', 'Decals', 'Decal Palette'}
    for name in ('runtime', 'spawn', 'environment', 'forge'):
        handled.update(stages[name])
    handled.update(stages['objects']['counts'])
    schema = load_schema(importer.source, 'scnr', importer.reference)
    source = importer.source
    root = next(t['offset'] for t in source.tags.values() if t['group'] == 'scnr')
    inventory = {}
    references = {'Camera Effects', 'Global Screen Effect', 'Sky Parameters',
                  'Global Lighting', 'Lightmaps', 'Performance Throttles'}
    for node in schema:
        name = node.get('name')
        if node.tag == 'tagblock':
            count = source.u(root + int(node.get('offset'), 0))
            if count and name not in handled:
                raise ValueError(f'Unconverted scenario block: {name} ({count})')
            inventory[name] = count
        elif node.tag.lower() == 'tagref':
            datum = source.u(root + int(node.get('offset'), 0) + 12)
            if datum != 0xffffffff and name not in references:
                raise ValueError(f'Unconverted scenario reference: {name}')
    return {'source_blocks': inventory, 'slot_identity': getattr(importer, 'slot', 'lockout'),
            'simulation_definitions': 'Live retail definitions in original order, followed by imported dependencies',
            'unused_placement_palettes': (
                'Placement-referenced entries plus the explicitly audited inactive Dune fireteam weapon/vehicle references; no extra placements added'
                if getattr(importer, 'dune_inactive_ai_guard', None) else
                'Only entries referenced by placements are imported')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'source', 'basis', 'xex', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--sound-bank', type=Path,
                        help='Optional MCC FSB, needed only for sounds with no intact native H3 donor')
    parser.add_argument('--decoder', type=Path,
                        help='vgmstream CLI; required when an MCC sound bank is supplied')
    parser.add_argument('--mythic-only-audio', action='store_true',
                        help='Use audited map-specific Mythic sound substitutes; record audible differences, reject MCC banks')
    parser.add_argument('--slot', choices=('lockout', 'zanzibar', 'chillout', 'sandbox'), default='lockout')
    parser.add_argument('--powerhouse-ambient-quarter-stops', type=int, choices=range(9), default=0,
                        help='Experimental Powerhouse baked ambient boost; 0 preserves source lighting')
    parser.add_argument('--powerhouse-room-fill', type=float, choices=(0., .125, .25, .5), default=0.,
                        help='Experimental machinery-room C0 fill; default disabled')
    parser.add_argument('--forge-gulch', action='store_true', help='Build the spatially partitioned Forge Gulch candidate over Sandbox')
    parser.add_argument('--forge-island', action='store_true', help='Build the complementary Force Cove partition over the Sandbox basis')
    parser.add_argument('--chiron', action='store_true', help='Convert HGC Chiron with native H3 surface shaders over the Cold Storage basis')
    parser.add_argument('--desolation', action='store_true', help='Convert the identified 2022 Desolation source with the full stock H3 Forge palette')
    parser.add_argument('--haven-draft', action='store_true', help='Convert the official H3EK Haven preview using exact stock H3 shader permutations')
    parser.add_argument('--stock-h3-draft', action='store_true', help='Convert the fresh Battle Canyon H3EK draft using exact stock H3 shaders, without legacy Battle Canyon repairs')
    parser.add_argument('--battle-canyon', action='store_true', help='Convert Remember Reach Battle Canyon using the Last Resort assembly basis')
    parser.add_argument('--battle-canyon-rebuilt', action='store_true', help='Convert the fresh official-H3EK Battle Canyon build without legacy collision or material repairs')
    parser.add_argument('--battle-protect-decals', action='store_true', help='Use separately verified decal-preserving Battle Canyon collision intermediates')
    parser.add_argument('--mcc-shared', type=Path, help='Explicit read-only MCC H3 shared.map for Workshop resources')
    parser.add_argument('--additional-sound-bank', type=Path, action='append', default=[],
                        help='Additional read-only FSB; primary Workshop bank takes precedence')
    parser.add_argument('--disc-maps', type=Path, help='Original disc maps directory; defaults to PROJECT/maps')
    parser.add_argument('--metadata-reserve', type=lambda value: int(value, 0),
                        help='Smaller measured staging reserve, a positive 64KiB multiple; never raises native limits')
    args = parser.parse_args()
    bank_paths = ([args.sound_bank] if args.sound_bank else []) + args.additional_sound_bank
    if args.mythic_only_audio and bank_paths:
        parser.error('--mythic-only-audio cannot be combined with an MCC sound bank')
    if bank_paths and args.decoder is None:
        parser.error('--decoder is required when supplying an MCC sound bank')
    if args.decoder is not None and not bank_paths:
        parser.error('--decoder requires --sound-bank or --additional-sound-bank')
    if args.haven_draft and any((args.desolation, args.chiron, args.battle_canyon,
                                args.battle_canyon_rebuilt, args.battle_protect_decals,
                                args.forge_gulch, args.forge_island)):
        parser.error('Haven draft cannot be combined with another map profile')
    if args.battle_canyon_rebuilt and (args.battle_canyon or args.battle_protect_decals):
        parser.error('The fresh H3EK build must not use legacy Battle Canyon repairs')
    if args.forge_gulch and args.forge_island:
        parser.error('Select one Forge partition')
    if args.desolation and any((args.chiron,args.battle_canyon,args.battle_canyon_rebuilt,args.forge_gulch,args.forge_island)):
        parser.error('Desolation cannot be combined with another map profile')
    project = args.project.resolve(strict=True)
    output, report = (output_path(path, project) for path in (args.output, args.report))
    inputs = [path.resolve(strict=True) for path in
              (args.source, args.basis, args.xex, *bank_paths,
               *([args.decoder] if args.decoder else []))]
    if output == report or any(path in inputs for path in (output, report)):
        raise ValueError('Outputs must be distinct from one another and all inputs')
    if output.exists():
        raise ValueError('Output already exists; choose a fresh checkpoint path')
    if report.exists() and any(os.path.samefile(report, path) for path in inputs):
        raise ValueError('Report aliases an input file')
    basis_hash = file_hash(args.basis)
    original = (args.disc_maps or project / 'maps') / (args.slot + '.map')
    if basis_hash != file_hash(original) and not (args.slot == 'lockout' and basis_hash == ACCEPTED_SHA256):
        raise ValueError('Basis must match the selected original disc map (or the accepted Lockout checkpoint)')
    for path in (output.parent, report.parent):
        path.mkdir(parents=True, exist_ok=True)
    work = output_path(Path(__file__).resolve().parents[4] / '.local/build-temp', project)
    work.mkdir(parents=True, exist_ok=True)
    state = {'status': 'building', 'basis_sha256': basis_hash,
             'historical_seed_used': basis_hash == ACCEPTED_SHA256,
             'limitations': ['Map conversion POC; unsupported content fails explicitly.',
                            'Per-material approximations and converted animations are listed in the materials report.',
                            'Native gameplay and system-link behavior unverified.'], 'stages': {}}
    started = time.monotonic()
    temporary = None
    source = builder = importer = None
    stage = 'inputs'
    try:
        salt = resource_salt(args.xex)
        state['source_sha256'] = file_hash(args.source)
        source = Cache(str(args.source), True)
        from source_schema import profile
        state['source_schema_profile'] = profile(source)
        if args.stock_h3_draft:
            if any((args.haven_draft,args.battle_canyon,args.battle_canyon_rebuilt,args.desolation,args.chiron,args.forge_gulch,args.forge_island)):
                raise ValueError('Stock draft cannot be combined with another profile')
            names=[source.name(n) for n,t in source.tags.items() if t['group']=='scnr']
            if args.slot!='zanzibar' or names != [r'levels\custom\battle_canyon_fresh\battle_canyon_fresh']:
                raise ValueError('Unexpected fresh stock-H3 draft source')
            from preflight_collision_budget import inspect as inspect_collision
            from preflight_variant_budget import inspect as inspect_variant
            state['collision_budget']=inspect_collision(source)
            state['variant_budget']=inspect_variant(source)
            if not all(state[k]['conversion_ready'] for k in ('collision_budget','variant_budget')):
                raise ValueError('Fresh source exceeds native collision/placement limits')
            state['source_pipeline']='Original Reach -> unchanged Blender exporter -> official H3EK -> original H3; MCC playtest waived by user 2026-11-04'
        if args.haven_draft:
            scenario_names = [source.name(i) for i, t in source.tags.items() if t['group'] == 'scnr']
            if args.slot != 'zanzibar' or scenario_names not in ([r'levels\custom\haven_h4\haven_preview'], [r'levels\custom\haven_h4\haven_skyview']):
                raise ValueError('Haven draft requires the official H3EK preview and zanzibar basis')
            from preflight_collision_budget import inspect as inspect_collision
            from preflight_variant_budget import inspect as inspect_variant
            state['collision_budget'] = inspect_collision(source)
            state['variant_budget'] = inspect_variant(source)
            if not all(state[k]['conversion_ready'] for k in ('collision_budget', 'variant_budget')):
                raise ValueError('Haven exceeds original H3 collision or placement limits')
            state['source_pipeline'] = 'Original H4EK authoring -> unchanged Foundry/General101 -> official H3EK; compiled collision retained'
        from powerhouse_lighting import configure
        configure(source, args.powerhouse_ambient_quarter_stops)
        source.powerhouse_room_fill = args.powerhouse_room_fill
        state['powerhouse_room_fill'] = args.powerhouse_room_fill
        state['powerhouse_ambient_quarter_stops'] = args.powerhouse_ambient_quarter_stops
        if args.mcc_shared:
            source.shared_paths = {r'maps\shared.map': args.mcc_shared.resolve(strict=True)}
            source.decoded_pages = {}  # Bounded resource-reader cache; no disk asset copies.
        if args.battle_canyon:
            scenario_names = [source.name(i) for i,t in source.tags.items() if t['group']=='scnr']
            if args.slot != 'zanzibar' or scenario_names != [r'levels\multi\cex_beavercreek\cex_beavercreek']:
                raise ValueError('Battle Canyon profile requires cex_beavercreek and zanzibar basis')
        if args.battle_canyon_rebuilt:
            scenario_names = [source.name(i) for i,t in source.tags.items() if t['group']=='scnr']
            if args.slot != 'zanzibar' or scenario_names != [r'levels\mod_levels\battle_canyon\battle_canyon']:
                raise ValueError('Fresh Battle Canyon requires the official H3EK scenario and zanzibar basis')
            from preflight_collision_budget import inspect
            state['collision_budget'] = inspect(source)
            if not state['collision_budget']['conversion_ready']:
                raise ValueError('Fresh H3EK collision exceeds original H3 limits')
            from preflight_variant_budget import inspect as inspect_variant
            state['variant_budget'] = inspect_variant(source)
            if not state['variant_budget']['conversion_ready']:
                raise ValueError('Scenario placements exceed original H3 variant capacity')
            state['source_pipeline'] = 'Original Reach authoring -> ASS -> official H3EK; compiled collision retained'
        if args.chiron:
            scenario_names = [source.name(i) for i,t in source.tags.items() if t['group']=='scnr']
            if args.slot != 'chillout' or scenario_names != [r'custom\levels\multiplayer\putput\putput']:
                raise ValueError('Chiron profile requires HGC putput and chillout basis')
        gulch_partition = None
        reference_rebuild = None
        prepared_maps = {r'levels\multi\s3d_avalanche\s3d_avalanche': 'diamondback',
                         r'levels\multi\s3d_reactor\s3d_reactor': 'reactor'}
        for n,t in source.tags.items():
            if t['group'] == 'scnr' and source.name(n) in prepared_maps:
                from prepared_collision import prepare
                stage = 'prepared_collision_integration'
                tables, maps, proof = prepare(source,
                    Path(__file__).resolve().parents[4]/'work'/prepared_maps[source.name(n)], source.name(n))
                reference_rebuild = tables, maps
                state['prepared_collision'] = proof
        if any(source.name(n) == r'levels\multi\s3d_sky_bridgenew\s3d_sky_bridgenew'
               for n,t in source.tags.items() if t['group'] == 'scnr'):
            from rebuild_collision_references import prepare
            stage = 'sky_bridge_collision_integration'
            tables, maps, proof = prepare(source, Path(__file__).resolve().parents[4]/'work/sky-bridge',
                                         r'levels\multi\s3d_sky_bridgenew\s3d_sky_bridgenew')
            reference_rebuild = tables, maps
            state['sky_bridge_collision'] = proof
        if args.battle_canyon:
            from prepare_battle_collision import prepare
            stage = 'battle_collision_integration'
            tables, maps, proof = prepare(source, protect_decals=args.battle_protect_decals)
            gulch_partition = tables, maps
            state['battle_canyon_collision'] = proof
        if (args.forge_gulch or args.forge_island) and args.slot != 'sandbox':
            raise ValueError('Forge Gulch requires the Sandbox slot')
        if args.slot == 'sandbox':
            from preflight_collision_budget import inspect
            stage = 'collision_budget_preflight'
            state['collision_budget'] = inspect(source)
            if args.forge_gulch or args.forge_island:
                from partition_forge_collision import prepare
                _, tables, maps, proof = prepare(source, 'island' if args.forge_island else 'gulch')
                gulch_partition = tables, maps
                state['gulch_collision'] = proof
                state['limitations'].append('Development candidate: split containment and native validation pending.')
            elif not state['collision_budget']['conversion_ready']:
                raise ValueError('Forge World needs an offline large-collision BSP rebuild/partition before retail conversion; see collision_budget in report. No engine limits may be raised.')
        metadata_reserve = 0x1000000 if args.source.name == 's3d_sky_bridgenew.map' else (0xc00000 if args.slot != 'lockout' else 0x800000)
        if args.mythic_only_audio and args.slot == 'lockout':
            # Complete native Forge dependency graphs exceed the old 8 MiB
            # staging reservation. This is allocator space below stock tags,
            # not an engine limit; serialized native budgets still gate export.
            metadata_reserve = 0xc00000
        if args.metadata_reserve is not None:
            if not 0 < args.metadata_reserve <= metadata_reserve or args.metadata_reserve % 0x10000:
                raise ValueError('Metadata reserve must be a positive 64KiB multiple no larger than the profile default')
            metadata_reserve = args.metadata_reserve
        state['metadata_staging_reserve'] = metadata_reserve
        builder = MapBuilder(str(args.basis), metadata_reserve)
        state['sound_banks'] = [str(path.resolve(strict=True)) for path in bank_paths]
        state['audio_policy'] = 'Native H3 reuse first; MCC decoding only when explicitly supplied and required'
        importer = TagImporter(source, CacheRegistry(builder, salt), sound_bank=SoundBanks(
            bank_paths, args.decoder, work), disc_maps=args.disc_maps or project / 'maps')
        importer.slot = args.slot
        importer.chiron = args.chiron
        importer.battle_canyon = args.battle_canyon
        importer.battle_canyon_rebuilt = args.battle_canyon_rebuilt
        importer.materials.battle_canyon = args.battle_canyon
        importer.materials.battle_canyon_rebuilt = args.battle_canyon_rebuilt
        importer.materials.chiron_materials = args.chiron
        importer.materials.haven_draft = args.haven_draft or args.stock_h3_draft
        importer.stock_h3_draft = args.stock_h3_draft
        if args.haven_draft or args.stock_h3_draft:
            # Preserve authored 2D mip dimensions using the existing encoder's
            # per-bitmap override. Some source sky images have only a base mip;
            # the generic 512px prototype cap cannot select a nonexistent mip.
            overrides = {}
            for index, tag in source.tags.items():
                name = source.name(index)
                prefix='levels\\custom\\battle_canyon_fresh\\' if args.stock_h3_draft else 'levels\\custom\\haven_h4\\bitmaps\\'
                if tag['group'] != 'bitm' or not name.startswith(prefix):
                    continue
                rows = source.block(tag['offset'] + 0x60, 0x38)
                if len(rows) != 1 or source.unpack('H', rows[0] + 10)[0] != 0:
                    continue
                info = importer.materials.bitmaps.info(index)[0]
                maximum = max(info['width'], info['height'])
                if maximum > 4096:
                    raise ValueError('Haven 2D texture exceeds the reviewed authoring bound: ' + name)
                overrides[name] = maximum
            importer.materials.bitmap_size_overrides = overrides
            state['authored_2d_bitmap_sizes'] = overrides
        importer.gulch_partition = gulch_partition
        importer.reference_rebuild = reference_rebuild
        importer.forge_partition_side = 'island' if args.forge_island else 'gulch'
        from native_assets import NativeAssets
        importer.native_assets = NativeAssets(importer, args.disc_maps or project / 'maps')
        importer.materials.native_assets = importer.native_assets
        if args.mythic_only_audio:
            from mythic_audio import configure as configure_mythic_audio
            state['mythic_audio_policy'] = configure_mythic_audio(importer)
            state['audio_policy'] = 'Supplied Mythic native packets only; explicit map-specific audible substitutes; no MCC bank'
        if args.desolation:
            from desolation_assets import configure as configure_desolation
            state['asset_policy'] = configure_desolation(importer, args.disc_maps or project / 'maps')
        if args.slot == 'sandbox':
            from forge_world import configure
            state['asset_policy'] = configure(importer)
        if args.slot == 'chillout':
            importer.materials.prisoner_materials = True
            importer.omitted_assets = {('eqip', r'custom\powerups\health_pack\tripmine_permanent')}
            if args.chiron:
                importer.omitted_assets.add(('bipd', r'custom\characters\hce_marine\hce_marine'))
            state['omitted_assets'] = sorted(importer.omitted_assets)
            # Same native template options as the original Blackout prototype.
            importer.materials.opaque_prototype = r'levels\dlc\chillout\shaders\chillout_halltile'
        if any(t['group'] == 'scnr' and source.name(k) ==
               r'custom\levels\multiplayer\boardingaction\boardingaction'
               for k, t in source.tags.items()):
            importer.materials.boarding_action = True
            # User approved removing CE health packs, including Forge entries.
            importer.omitted_assets = {('eqip', r'custom\powerups\health_pack\tripmine_permanent')}
            state['omitted_assets'] = sorted(importer.omitted_assets)
        if args.slot == 'zanzibar':
            importer.materials.resuscitation_sky = not (args.desolation or args.haven_draft)
            importer.materials.opaque_prototype = r'levels\solo\040_voi\shaders\metals\metal_factory_outerpanel_i'
        if args.slot in ('zanzibar', 'chillout'):
            from player_animations import stage_player_animations
            stage = 'player_animations'
            state['stages'][stage] = stage_player_animations(importer)
        terrain, water = importer.terrain, importer.water
        stages = [('runtime', lambda: stage_runtime(importer)),
                  ('geometry', lambda: stage_geometry(importer, terrain, water)),
                  ('objects', lambda: stage_primary_objects(importer, True, True)),
                  ('spawn', lambda: stage_spawn_settings(importer)),
                  ('environment', lambda: stage_environment(importer)),
                  ('decals', lambda: stage_decals(importer)),
                  ('forge', lambda: stage_forge(importer))]
        for stage, action in stages:
            print(stage, flush=True)
            stage_started = time.monotonic()
            state['stages'][stage] = action()
            if stage == 'runtime' and hasattr(importer, 'script_conversion'):
                state['script_conversion'] = importer.script_conversion
            if stage == 'runtime' and hasattr(importer, 'scenario_compatibility_notes'):
                state['scenario_compatibility_notes'] = importer.scenario_compatibility_notes
            state.setdefault('stage_seconds', {})[stage] = round(time.monotonic() - stage_started, 2)
            print(f'{stage}: {state["stage_seconds"][stage]}s', flush=True)
        stage = 'finalize'
        state['scenario_coverage'] = scenario_coverage(importer, state['stages'])
        if args.forge_gulch or args.forge_island:
            from unused_shader_bitmaps import prune_unused_shader_bitmaps
            state['unused_shader_bitmaps'] = prune_unused_shader_bitmaps(importer)
        from retired_resources import compact_basis
        state['compaction'] = compact_basis(importer)
        from scenario_residency import stage_residency
        state['residency'] = stage_residency(importer)
        if args.slot in ('zanzibar', 'chillout', 'sandbox'):
            from resource_indices import compact_resource_indices
            state['resource_indices'] = compact_resource_indices(importer)
        importer.finalize()
        if args.slot == 'sandbox':
            from forge_world import finalize_residency
            state['multi_bsp_residency'] = finalize_residency(importer)
        state.update(tags=importer.added, materials=importer.materials.report, sounds=importer.sounds.report,
                     bitmap_preservation=importer.materials.bitmap_preservation_report(state.get('resource_indices')),
                     metadata_used=builder.used, raw_bytes_added=len(builder.raw))
        if args.mythic_only_audio:
            from mythic_audio import applied_replacements
            state['mythic_audio_replacements'] = applied_replacements(importer)
        if hasattr(importer,'stock_forge_report'):
            state['stock_forge_palette'] = importer.stock_forge_report
        if hasattr(importer, 'empty_forge_placeholders'):
            state['empty_forge_placeholders'] = importer.empty_forge_placeholders
        if args.forge_gulch or args.forge_island:
            state['gulch_containment'] = importer.gulch_containment_report
        payload = builder.finish(salt)
        state.update(output_bytes=len(payload), output_sha256=hashlib.sha256(payload).hexdigest())
        stage = 'serialize'
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.warlock-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Reopen the serialized cache; validate its tag table and memory boundary.
        check = Cache(str(temporary))
        try:
            from console_cache_limits import inspect_native_budget, require_native_budget
            state['serialized_console_budget'] = inspect_native_budget(check, temporary)
            state['forge_quota_capacity'] = state['serialized_console_budget']['forge_quotas']
            require_native_budget(state['serialized_console_budget'])
            from verify_collision_trees import verify as verify_collision_trees
            state['collision_trees_verified'] = verify_collision_trees(check)
            if args.slot == 'chillout':
                from verify_player_animations import verify as verify_player_animations
                state['player_animations_verified'] = verify_player_animations(check)
            state['runtime_decals_verified'] = verify_runtime_decals(check, importer.reference)
            if check.u(8) != len(payload) or check.base + check.u(0x18) != 0xbfc00000:
                raise ValueError('Serialized cache size/memory boundary is invalid')
            tag_count = check.u(check.pointer(check.u(16)) + 8)
            if tag_count != len(importer.registry.tags) // 8:
                raise ValueError('Serialized tag table differs from assembled registry')
            # Retail tables may contain empty slots; Cache.tags omits those.
            for index in range(importer.registry.first_tag, tag_count):
                group, tag_salt, address = struct.unpack_from('>HHI', importer.registry.tags, index * 8)
                if group == 65535:
                    if (tag_salt, address) != (65535, 0) or index in check.tags:
                        raise ValueError(f'Serialized retired tag {index} is not an inert slot')
                    continue
                tag = check.tags[index]
                if (tag['group'] != check.groups[group] or tag['salt'] != tag_salt
                        or tag['offset'] != check.pointer(address)):
                    raise ValueError(f'Serialized imported tag {index} differs from registry')
        finally:
            check.close()
        if file_hash(temporary) != state['output_sha256']:
            raise ValueError('Serialized cache hash mismatch')
        # Windows rename refuses to overwrite an output created concurrently.
        os.rename(temporary, output)
        temporary = None
        state.update(status='checkpoint_built', output=str(output))
    except Exception as error:
        state.update(status='failed', failed_stage=stage, error=str(error))
        if getattr(error, '__notes__', None):
            state['error_context'] = list(error.__notes__)
        if importer is not None:
            state['bitmap_preservation'] = importer.materials.bitmap_preservation_report(state.get('resource_indices'))
            try:
                from partial_conversion_report import snapshot
                state['partial_conversion_notes'] = snapshot(importer)
            except Exception as audit_error:
                state['compatibility_reporting_error'] = str(audit_error)
        if args.mythic_only_audio and importer is not None:
            try:
                from mythic_audio import applied_replacements
                state['mythic_audio_replacements'] = applied_replacements(importer)
            except Exception as audit_error:
                state['mythic_audio_reporting_error'] = str(audit_error)
        if builder is not None:
            state.update(metadata_used=builder.used, metadata_reserved=builder.reserve)
        if temporary is not None and temporary.is_file():
            try:
                from audit_resource_footprint import inspect as inspect_footprint
                footprint = inspect_footprint(temporary, True)
                pages = {}
                for resource in footprint['resource_details']:
                    for page in resource['pages']:
                        if page['shared']:
                            continue
                        item = pages.setdefault(page['block'], dict(page, owners=[]))
                        item['owners'].append({k: resource[k] for k in ('owner_datum', 'group', 'owner')})
                state['rejected_resource_footprint'] = dict(
                    tag_memory_bytes=footprint['tag_memory_bytes'],
                    all_referenced_pages=footprint['all_referenced_pages'],
                    largest_local_pages=sorted(pages.values(), key=lambda p: p['compressed_bytes'], reverse=True)[:32],
                    scope='Static diagnostic inventory, not simultaneous RAM usage')
            except Exception as footprint_error:
                state['rejected_resource_footprint_error'] = str(footprint_error)
        raise
    finally:
        if source is not None:
            source.close()
        if builder is not None:
            builder.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        state['seconds'] = round(time.monotonic() - started, 2)
        report.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print(f'Checkpoint saved: {output}', flush=True)


if __name__ == '__main__':
    main()
