"""Inventory existing H4 tags through official ManagedBlam; never create/save tags.

Reuses the official API pattern in tools/stock-h3-audit/inspect_reach_source.py
and Foundry's Corinth initialization. This is not an asset parser or converter.
Run with Blender 4.5's bundled Python and repository-local profiles/temp paths.
"""
from collections import deque
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h4ek'
TAG_ROOT = KIT / 'tags'
SOURCE = 'levels/multi/wraparound/wraparound.scenario'
FOLLOW = {'scenario', 'scenario_structure_bsp', 'scenario_structure_lighting_info',
          'structure_design', 'scenario_lightmap', 'atmosphere_fog',
          'atmosphere_globals', 'camera_fx_settings', 'sky_atm_parameters'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tag_file(relative):
    path = (TAG_ROOT / relative.replace('\\', '/')).resolve()
    if not path.is_relative_to(TAG_ROOT.resolve()):
        raise ValueError(f'Tag reference escapes the local kit: {relative}')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag-list', type=Path, help='Repository-local JSON list of tag paths to inspect')
    parser.add_argument('--output-name', default='haven-source-inventory.json')
    args = parser.parse_args()
    if Path(args.output_name).name != args.output_name or not args.output_name.endswith('.json'):
        parser.error('output-name must be a JSON filename, not a path')
    seeds = [SOURCE]
    if args.tag_list:
        input_list = args.tag_list.resolve()
        if not input_list.is_relative_to(ROOT.resolve()):
            parser.error('tag-list must be inside the repository')
        seeds = json.loads(input_list.read_text(encoding='utf-8'))
        if not isinstance(seeds, list) or not seeds or not all(isinstance(s, str) for s in seeds):
            parser.error('tag-list must contain a nonempty list of tag path strings')
        for source in seeds:
            if not tag_file(source).is_file():
                parser.error(f'Requested source tag does not exist: {source}')
    for variable, suffix in [('TEMP', 'temp'), ('TMP', 'temp'),
                             ('APPDATA', 'profile/roaming'),
                             ('LOCALAPPDATA', 'profile/local')]:
        directory = OUT / suffix
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(directory)
    os.chdir(KIT)
    sys.path.insert(0, str(ROOT / 'work/stock-h3-audit/python-packages'))
    import clr
    clr.AddReference(str(KIT / 'bin/ManagedBlam.dll'))
    import Corinth as Halo

    def fields_inventory(fields, references, blocks):
        for field in fields:
            if isinstance(field, Halo.Tags.TagFieldReference):
                if field.Path:
                    references.append(dict(field=str(field.FieldPath),
                        tag=str(field.Path.RelativePathWithExtension).replace('\\', '/')))
            elif isinstance(field, (Halo.Tags.TagFieldBlock, Halo.Tags.TagFieldStruct)):
                if isinstance(field, Halo.Tags.TagFieldBlock):
                    blocks.append(dict(field=str(field.FieldPath),
                                       count=int(field.Elements.Count)))
                for element in field.Elements:
                    fields_inventory(element.Fields, references, blocks)

    # Snapshot every seed tag, including any new paths after the API read.
    before = {str(p.relative_to(TAG_ROOT)).replace('\\', '/'): digest(p)
              for p in TAG_ROOT.rglob('*') if p.is_file()}
    assert SOURCE in before, 'Official Haven scenario must exist before inspection'
    def record_native_crash(info):
        details = {'type':str(info.GetType()), 'text':str(info)}
        for field in info.GetType().GetFields():
            try:
                details[str(field.Name)] = str(field.GetValue(info))
            except Exception as error:
                details[str(field.Name)] = repr(error)
        print('H4_NATIVE_CRASH', json.dumps(details), flush=True)
    callback = Halo.ManagedBlamCrashCallback(record_native_crash)
    parameters = Halo.ManagedBlamStartupParameters()
    parameters.InitializationLevel = Halo.InitializationType.TagsOnly
    Halo.ManagedBlamSystem.Start(str(KIT), callback, parameters)
    report = dict(source=SOURCE, requested_tags=seeds, api='Corinth.ManagedBlam', tags={}, missing=[],
        scope='Source scene references and block counts; not complete dependency closure or conversion.')
    queue = deque(seeds)
    seen = set()
    try:
        while queue:
            relative = queue.popleft()
            if relative in seen:
                continue
            seen.add(relative)
            path = tag_file(relative)
            if not path.is_file():
                report['missing'].append(relative)
                continue
            tag = Halo.Tags.TagFile()
            try:
                tag.Load(Halo.Tags.TagPath.FromPathAndExtension(*relative.rsplit('.', 1)))
                references, blocks = [], []
                fields_inventory(tag.Fields, references, blocks)
                report['tags'][relative] = dict(sha256=digest(path), bytes=path.stat().st_size,
                    references=references, blocks=blocks)
                print('READ', relative, 'references', len(references), 'blocks', len(blocks), flush=True)
                for reference in references:
                    if reference['tag'].rsplit('.', 1)[-1] in FOLLOW:
                        queue.append(reference['tag'])
            finally:
                tag.Dispose()
    finally:
        Halo.ManagedBlamSystem.Stop()
    after = {str(p.relative_to(TAG_ROOT)).replace('\\', '/'): digest(p)
             for p in TAG_ROOT.rglob('*') if p.is_file()}
    report['source_tags_unchanged'] = before == after
    report['seed_tag_manifest'] = before
    assert report['source_tags_unchanged'], 'Tag inputs changed during read-only inspection'
    (OUT / args.output_name).write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('H4_SOURCE_INVENTORY_OK', len(report['tags']), 'missing scene dependencies', len(report['missing']), flush=True)


if __name__ == '__main__':
    main()
