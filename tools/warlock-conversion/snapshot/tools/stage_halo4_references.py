"""Extract official-API tag references with 7-Zip and verify against its index.

Orchestration only: no asset decoding, rewriting, format conversion or kit edits.
The archive index is the JSON transcription of 7-Zip's -slt listing.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h4ek'
ARCHIVE = Path('Z:/SteamLibrary/steamapps/common/H4EK/H4EK.7z')
SEVEN_ZIP = Path('C:/Program Files/7-Zip/7z.exe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('--label', required=True)
    parser.add_argument('--extract', action='store_true')
    args = parser.parse_args()
    inventory_path = args.inventory.resolve()
    if not inventory_path.is_relative_to(ROOT.resolve()):
        parser.error('inventory must be inside the repository')
    if not args.label or not all(c.isalnum() or c in '-_' for c in args.label):
        parser.error('label must contain only letters, numbers, hyphens and underscores')
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    index = {row['path'].lower(): row for row in
             json.loads((OUT / 'h4ek-archive-index.json').read_text(encoding='utf-8'))}
    references = sorted({ref['tag'].replace('\\', '/')
        for tag in inventory['tags'].values() for ref in tag['references']})
    requested, unavailable = [], []
    for reference in references:
        row = index.get('tags/' + reference.lower())
        if row is None:
            unavailable.append(reference)
            continue
        destination = (KIT / row['path']).resolve()
        if not destination.is_relative_to((KIT / 'tags').resolve()):
            raise ValueError(f'Reference escapes local tag root: {reference}')
        if not destination.is_file():
            requested.append(row)
    report = dict(inventory=str(inventory_path.relative_to(ROOT)), archive=str(ARCHIVE),
        referenced_tags=len(references), selected_files=len(requested),
        selected_bytes=sum(row['size'] for row in requested),
        unavailable=unavailable, extracted=False)
    stem = OUT / args.label
    file_list = stem.with_name(stem.name + '-files.txt')
    file_list.write_text('\n'.join(row['path'].replace('/', '\\') for row in requested) + '\n', encoding='utf-8')
    if args.extract and requested:
        if shutil.disk_usage(ROOT).free < report['selected_bytes'] + 2 * 1024**3:
            raise RuntimeError('Insufficient repository space for this extraction plus 2 GiB reserve')
        environment = os.environ.copy()
        temp = OUT / 'temp'
        temp.mkdir(parents=True, exist_ok=True)
        environment.update(TEMP=str(temp), TMP=str(temp))
        with stem.with_name(stem.name + '-extract.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([str(SEVEN_ZIP), 'x', '-aos', '-y', '-bb0', '-bsp0',
                '-o' + str(KIT), str(ARCHIVE), '@' + str(file_list)], cwd=ROOT,
                env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        if result.returncode:
            raise RuntimeError(f'7-Zip failed with exit code {result.returncode}')
        verified = []
        for row in requested:
            data = (KIT / row['path']).read_bytes()
            if len(data) != row['size'] or f'{zlib.crc32(data):08X}' != row['crc'].upper():
                raise RuntimeError(f'Archive verification failed: {row["path"]}')
            verified.append(dict(path=row['path'], bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(), archive_crc_verified=True))
        report.update(extracted=True, verified_files=verified)
    stem.with_name(stem.name + '-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key != 'verified_files'}, indent=2))


if __name__ == '__main__':
    main()
