"""Assemble scenario converters onto original Lockout or the accepted checkpoint.

This is a Warlock-specific proof-of-concept, not a general MCC converter.
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
from scenario_decals import stage_decals
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
    return {'source_blocks': inventory, 'slot_identity': 'Blackout / map ID 520',
            'simulation_definitions': 'Original retail definitions plus imported dependencies',
            'unused_placement_palettes': 'Only entries referenced by placements are imported'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'source', 'basis', 'xex', 'sound-bank', 'decoder', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--disc-maps', type=Path, help='Original disc maps directory; defaults to PROJECT/maps')
    args = parser.parse_args()
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
    original = (args.disc_maps or project / 'maps') / 'lockout.map'
    if basis_hash not in (ACCEPTED_SHA256, file_hash(original)):
        raise ValueError('Basis must be original disc Lockout or the accepted geometry checkpoint')
    for path in (output.parent, report.parent):
        path.mkdir(parents=True, exist_ok=True)
    work = output_path(project / '.local/temp', project)
    work.mkdir(parents=True, exist_ok=True)
    state = {'status': 'building', 'basis_sha256': basis_hash,
             'historical_seed_used': basis_hash == ACCEPTED_SHA256,
             'limitations': ['Warlock-specific POC; unsupported content fails explicitly.',
                            'Material POC approximations include native reflection substitutes and frozen shader animation; see materials report.',
                            'Native gameplay and system-link behavior unverified.'], 'stages': {}}
    started = time.monotonic()
    temporary = None
    source = builder = None
    stage = 'inputs'
    try:
        salt = resource_salt(args.xex)
        state['source_sha256'] = file_hash(args.source)
        source = Cache(str(args.source), True)
        builder = MapBuilder(str(args.basis), 0x1000000)
        importer = TagImporter(source, CacheRegistry(builder, salt), sound_bank=SoundBank(
            args.sound_bank, args.decoder, work), disc_maps=args.disc_maps or project / 'maps')
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
            state['stages'][stage] = action()
        stage = 'finalize'
        state['scenario_coverage'] = scenario_coverage(importer, state['stages'])
        importer.finalize()
        state.update(tags=importer.added, materials=importer.materials.report,
                     metadata_used=builder.used, raw_bytes_added=len(builder.raw))
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
