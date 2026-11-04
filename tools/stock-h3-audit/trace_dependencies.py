"""Run upstream TagTool List queries recursively; parse text, never asset bytes."""
import argparse
import csv
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
parser = argparse.ArgumentParser()
parser.add_argument('platform', choices=['360', 'mcc'])
args = parser.parse_args()
label = args.platform
cache = ('C:/X360/ISOs/H3M/maps/bunkerworld.map' if label == '360' else
         'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/maps/bunkerworld.map')
inventory = OUT / ('standoff-all-tags.txt' if label == '360' else 'standoff-mcc-all-tags.txt')
tags = {}
for line in inventory.read_text(encoding='utf-8-sig').splitlines():
    m = re.match(r'\[Index: (0x[0-9A-F]+), Offset: 0x[0-9A-F]+\] (.*)$', line)
    if m:
        tags[m[1]] = m[2].strip()
by_name = {v: k for k, v in tags.items()}
with (OUT / 'standoff-forge-no-vehicles.csv').open(newline='') as stream:
    roots = [r['path'] + '.' + r['group'] for r in csv.DictReader(stream)]
pending = {by_name[n] for n in roots}
graph = {}
env = dict(os.environ, DOTNET_ROLL_FORWARD='Major', TEMP=str(OUT / 'temp'), TMP=str(OUT / 'temp'))
for wave in range(30):
    if not pending:
        break
    commands = OUT / f'trace-{label}-{wave:02d}.commands'
    output = OUT / f'trace-{label}-{wave:02d}.txt'
    commands.write_text('\n'.join(line for idx in sorted(pending)
                                   for line in (f'Echo ROOT {idx}', f'TagDependency List {idx}'))+'\n')
    with output.open('w', encoding='utf-8') as stream:
        run = subprocess.run([str(OUT / 'bin/TagTool.exe'), cache, 'RunCommands', str(commands)],
                             cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    text = output.read_text(encoding='utf-8-sig')
    if run.returncode or re.search(r'ERROR|Exception|Warning', text):
        raise RuntimeError(f'Inspect {output}: dependency query failed or warned; no completion claim')
    batch = {}
    root = None
    # Echo has no newline; a tag containing only null references prints nothing.
    for line in text.replace('ROOT ', '\nROOT ').splitlines():
        m = re.match(r'ROOT (0x[0-9A-F]+)', line)
        if m:
            root = m[1]
            batch[root] = []
        m = re.search(r'\[Index: (0x[0-9A-F]+), Offset: 0x[0-9A-F]+\]', line)
        if m:
            assert root
            batch[root].append(m[1])
    assert set(batch) == pending
    graph.update(batch)
    pending = {d for refs in batch.values() for d in refs} - graph.keys()
    print(f'{label}: wave {wave}, queried {len(batch)}, total {len(graph)}, next {len(pending)}', flush=True)
else:
    raise RuntimeError('Dependency query wave limit reached')
report = dict(platform=label, cache=cache, roots=roots,
              tags={tags[k]: sorted(tags[d] for d in refs) for k, refs in graph.items()},
              tag_count=len(graph), scope='Transitive references exposed by upstream TagDependency List; no binary equivalence or resource-page validation.')
(OUT / f'closure-{label}.json').write_text(json.dumps(report, indent=2)+'\n')
print(f'{label}: traversal complete, {len(graph)} tags', flush=True)
