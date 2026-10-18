"""Assemble completed scenario converters onto the accepted geometry checkpoint.

This is an integration command, NOT the final seed-independent map converter.
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

from cache_reader import Cache
from cache_registry import CacheRegistry
from map_builder import MapBuilder
from tag_importer import TagImporter
from fmod_audio import SoundBank
from assemble_scenario import stage_primary_objects, stage_spawn_settings
from scenario_environment import stage_environment
from scenario_decals import stage_decals
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'source', 'basis', 'xex', 'sound-bank', 'decoder', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
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
    if file_hash(args.basis) != ACCEPTED_SHA256:
        raise ValueError('This checkpoint command requires the accepted geometry basis')
    for path in (output.parent, report.parent):
        path.mkdir(parents=True, exist_ok=True)
    work = output_path(project / '.local/temp', project)
    work.mkdir(parents=True, exist_ok=True)
    state = {'status': 'building', 'basis_sha256': ACCEPTED_SHA256,
             'limitations': ['Accepted geometry checkpoint still required; seed-independent pipeline unfinished.',
                            'Remaining map-material/reflection work is not completed by this command.',
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
            args.sound_bank, args.decoder, work))
        stages = [('objects', lambda: stage_primary_objects(importer, True, True)),
                  ('spawn', lambda: stage_spawn_settings(importer)),
                  ('environment', lambda: stage_environment(importer)),
                  ('decals', lambda: stage_decals(importer))]
        for stage, action in stages:
            print(stage, flush=True)
            state['stages'][stage] = action()
        stage = 'finalize'
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
