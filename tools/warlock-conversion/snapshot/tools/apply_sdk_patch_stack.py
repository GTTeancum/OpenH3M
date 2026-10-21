"""Validate a layered SDK patch stack with a private index before changing files.

Accept only pristine or known intermediate contents, never unknown local edits.
The real SDK Git index is not changed. Handles patches extending earlier patches.
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk', type=Path, required=True)
parser.add_argument('--index', type=Path, required=True)
parser.add_argument('patches', type=Path, nargs='+')
args = parser.parse_args()
sdk = args.sdk.resolve(strict=True)
index = args.index.resolve()
repo = Path(__file__).resolve().parents[4]
sdk.relative_to(repo)
index.relative_to(repo)
index.parent.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, GIT_INDEX_FILE=str(index))

def git(*parts):
    return subprocess.check_output(['git', '-C', str(sdk), *parts], env=env, stderr=subprocess.STDOUT)

def digest(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).digest()

git('read-tree', 'HEAD')
accepted, expected = {}, {}
for patch in args.patches:
    patch = patch.resolve(strict=True)
    patch.relative_to(repo)
    paths = [line[6:] for line in patch.read_text().splitlines() if line.startswith('+++ b/')]
    if not paths:
        raise ValueError(f'No supported file changes in {patch}')
    for name in paths:
        (sdk / name).resolve().relative_to(sdk)
        accepted.setdefault(name, set()).add(digest(git('show', ':' + name)))
    git('apply', '--cached', '--ignore-space-change', str(patch))
    for name in paths:
        expected[name] = git('show', ':' + name)
        accepted[name].add(digest(expected[name]))

# Validate every file before any write, so a partial failure cannot erase edits.
for name, versions in accepted.items():
    if digest((sdk / name).read_bytes()) not in versions:
        raise SystemExit(f'Unrecognized local SDK changes: {name}; nothing written')
changed = []
for name, data in expected.items():
    path = sdk / name
    if digest(path.read_bytes()) != digest(data):
        path.write_bytes(data)
        changed.append(name)
print(f'Validated {len(args.patches)} patches; updated {len(changed)} SDK files')
