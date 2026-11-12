"""Promote a native-installed, byte-verified bundle without replacing profiles.

All paths stay in the repository. Keeps one explicit previous-content rollback;
never changes the game executable, disc maps or bootstrap configuration.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from build_dlc_live import confined


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle-report','native-install-root','content-root','payload','rollback','report'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args()
    paths = {name:confined(value) for name,value in vars(a).items()}
    processes = subprocess.check_output(['tasklist','/FO','CSV','/NH'],text=True)
    if any(row and row[0].lower() in ('openh3m.exe','halo3mp.exe') for row in csv.reader(processes.splitlines())):
        raise ValueError('Close game processes before promoting content')
    report = json.loads(paths['bundle_report'].read_text())
    identity = report['content_id']
    if len(identity)!=40 or any(c not in '0123456789ABCDEF' for c in identity):
        raise ValueError('Invalid content ID')
    relative = Path('0000000000000000/4D5307E6/00000002')
    source = paths['native_install_root']/relative/identity
    current_root = paths['content_root']/relative
    old = [f.parent for f in current_root.glob('*/forge_gulch.map')]
    if len(old)!=1 or (current_root/identity).exists() or paths['rollback'].exists():
        raise ValueError('Expected one previous bundle and unused target/rollback paths')
    expected = {e['name']:e['sha256'] for e in report['entries']}
    if {f.name for f in source.iterdir()}!=set(expected):
        raise ValueError('Native-installed payload differs from bundle manifest')
    for name,sha in expected.items():
        if digest(source/name)!=sha or digest(paths['payload']/name)!=sha:
            raise ValueError(f'Payload byte mismatch: {name}')
    headers = Path('0000000000000000/4D5307E6/Headers/00000002')
    source_header = paths['native_install_root']/headers/(identity+'.header')
    if not source_header.is_file():
        raise ValueError('Missing header from native installer')
    # Remove the native extraction's duplicate bytes after verifying them.
    # Prefer existing installation data when identical; otherwise link payload.
    for name,sha in expected.items():
        candidate = old[0]/name
        backing = candidate if candidate.is_file() and digest(candidate)==sha else paths['payload']/name
        (source/name).unlink()
        os.link(backing,source/name)
    paths['rollback'].mkdir(parents=True)
    destination_header = paths['content_root']/headers/(identity+'.header')
    destination_header.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source_header,destination_header)
    previous = paths['rollback']/old[0].name
    old[0].rename(previous)
    try:
        source.rename(current_root/identity)
    except Exception:
        previous.rename(old[0])
        destination_header.unlink()
        raise
    old_header = paths['content_root']/headers/(old[0].name+'.header')
    if old_header.exists():
        old_header.rename(paths['rollback']/old_header.name)
    result = dict(installed=str(current_root/identity),rollback=str(previous),
                  source_bundle_sha256=report['sha256'],files=expected,
                  profiles='preserved',engine='unchanged')
    paths['report'].write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))


if __name__=='__main__':
    main()
