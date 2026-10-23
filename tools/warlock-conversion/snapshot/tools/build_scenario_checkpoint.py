"""Assemble a scenario onto original Blackout/Last Resort or the accepted Warlock seed.

This is a Warlock/Resuscitation proof-of-concept, not a general MCC converter.
All outputs are confined to the explicitly supplied project's .local directory.
"""
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
from fmod_audio import SoundBank
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
    schema = ET.parse(importer.reference / 'mcc/scnr.xml').getroot()
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
            'unused_placement_palettes': 'Only entries referenced by placements are imported'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'source', 'basis', 'xex', 'sound-bank', 'decoder', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--slot', choices=('lockout', 'zanzibar', 'chillout', 'sandbox'), default='lockout')
    parser.add_argument('--forge-gulch', action='store_true', help='Build the spatially partitioned Forge Gulch candidate over Sandbox')
    parser.add_argument('--forge-island', action='store_true', help='Build the complementary Forge Island partition over the Sandbox basis')
    parser.add_argument('--disc-maps', type=Path, help='Original disc maps directory; defaults to PROJECT/maps')
    args = parser.parse_args()
    if args.forge_gulch and args.forge_island:
        parser.error('Select one Forge partition')
    project = args.project.resolve(strict=True)
    output, report = (output_path(path, project) for path in (args.output, args.report))
    inputs = [path.resolve(strict=True) for path in
              (args.source, args.basis, args.xex, args.sound_bank, args.decoder)]
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
    source = builder = None
    stage = 'inputs'
    try:
        salt = resource_salt(args.xex)
        state['source_sha256'] = file_hash(args.source)
        source = Cache(str(args.source), True)
        gulch_partition = None
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
        builder = MapBuilder(str(args.basis), 0xc00000 if args.slot != 'lockout' else 0x800000)
        importer = TagImporter(source, CacheRegistry(builder, salt), sound_bank=SoundBank(
            args.sound_bank, args.decoder, work), disc_maps=args.disc_maps or project / 'maps')
        importer.slot = args.slot
        importer.gulch_partition = gulch_partition
        importer.forge_partition_side = 'island' if args.forge_island else 'gulch'
        from native_assets import NativeAssets
        importer.native_assets = NativeAssets(importer, args.disc_maps or project / 'maps')
        importer.materials.native_assets = importer.native_assets
        if args.slot == 'sandbox':
            from forge_world import configure
            state['asset_policy'] = configure(importer)
        if args.slot == 'chillout':
            importer.materials.prisoner_materials = True
            importer.omitted_assets = {('eqip', r'custom\powerups\health_pack\tripmine_permanent')}
            state['omitted_assets'] = sorted(importer.omitted_assets)
            # Same native template options as the original Blackout prototype.
            importer.materials.opaque_prototype = r'levels\dlc\chillout\shaders\chillout_halltile'
        if args.slot == 'zanzibar':
            importer.materials.resuscitation_sky = True
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
            state.setdefault('stage_seconds', {})[stage] = round(time.monotonic() - stage_started, 2)
            print(f'{stage}: {state["stage_seconds"][stage]}s', flush=True)
        stage = 'finalize'
        state['scenario_coverage'] = scenario_coverage(importer, state['stages'])
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
                     metadata_used=builder.used, raw_bytes_added=len(builder.raw))
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
        if builder is not None:
            state.update(metadata_used=builder.used, metadata_reserved=builder.reserve)
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
