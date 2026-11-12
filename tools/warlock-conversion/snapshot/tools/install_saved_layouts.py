"""Install verified Forge saves into a repository-local OpenH3M content root.

Uses the SDK's existing saved-content discovery, without engine changes.
Refuses to overwrite an edited save or install against the wrong map revision.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from build_dlc_live import confined
from verify_dlc_stfs import verify, verify_payload


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--content-root', type=Path, required=True)
    args = p.parse_args()
    root = confined(args.content_root)
    entries = json.loads(confined(args.manifest).read_text())
    prepared = []
    checked_maps = {}
    for entry in entries:
        package, payload = confined(Path(entry['package'])), confined(Path(entry['payload']))
        if digest(package) != entry['sha256'] or entry['content_type'] != 1:
            raise ValueError('Saved-content manifest/package mismatch')
        with package.open('rb') as stream:
            verify(stream)
        verify_payload(package, payload)
        header = package.read_bytes()[:0x379]
        profile = header[0x371:0x379].hex().upper()
        if header[:4] != b'CON ' or profile != entry['profile_id']:
            raise ValueError('Saved-content profile mismatch')
        map_name = {'Forge Gulch':'forge_gulch', 'Force Cove':'forge_island'}[entry['home']]
        if map_name not in checked_maps:
            maps = list((root/'0000000000000000/4D5307E6/00000002').rglob(map_name+'.map'))
            if len(maps) != 1:
                raise ValueError('Expected exactly one installed shared base map')
            checked_maps[map_name] = digest(maps[0])
        if checked_maps[map_name] != entry['required_map_sha256']:
            raise ValueError('Install the matching LIVE map bundle first')
        source = payload/'sandbox.map'
        destination = confined(root/profile/'4D5307E6/00000001'/package.name/'sandbox.map')
        if destination.exists() and digest(destination) != digest(source):
            raise ValueError(f'Refusing to overwrite an existing changed save: {destination}')
        prepared.append((source, destination, entry['name']))
    for source, destination, name in prepared:
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Saves are mutable: never hardlink to conversion source/evidence.
            shutil.copyfile(source, destination)
        print(f'Installed {name}: {destination}')


if __name__ == '__main__':
    main()
