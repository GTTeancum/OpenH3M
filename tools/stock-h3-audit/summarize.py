"""Format stock TagTool text reports; does not read or modify map/tag binaries."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'


def write_csv(name, rows, fields):
    with (OUT / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


tags = []
for line in (OUT / 'standoff-all-tags.txt').read_text(encoding='utf-8-sig').splitlines():
    match = re.match(r'^\[Index: (0x[0-9A-F]+), Offset: (0x[0-9A-F]+)\] (.*)\.([^.]*)$', line)
    if match:
        tags.append(dict(zip(('index', 'offset', 'path', 'group'), match.groups())))
assert tags and len({r['index'] for r in tags}) == len(tags)
tag_lookup = {r['index']: r for r in tags}
palette_text = (OUT / 'standoff-forge-palette.txt').read_text(encoding='utf-8-sig')
assert 'ERROR' not in palette_text.upper()
palette = []
category = None
current = None
for line in palette_text.splitlines():
    marker = re.search(r'CATEGORY (\w+)', line)
    if marker:
        category = marker[1]
    obj = re.search(r'Object: CachedTag = \[(0x[0-9A-F]+)\] (.*?)\s*$', line)
    if obj:
        assert category
        tag = tag_lookup[obj[1]]
        assert obj[2] == tag['path'] + '.' + tag['group']
        current = dict(category=category, index=obj[1], path=tag['path'], group=tag['group'])
        palette.append(current)
    for field, pattern in [('name', r'^Name: StringId = (.*?)\s*$'),
                           ('max_allowed', r'^MaxAllowed: Int32 = (\d+)\s*$'),
                           ('cost', r'^Cost: Single = ([\d.]+)\s*$')]:
        value = re.search(pattern, line)
        if value:
            assert current is not None
            current[field] = value[1]
fields = ['category', 'index', 'path', 'group', 'name', 'max_allowed', 'cost']
assert all(set(r) == set(fields) for r in palette)
counts = dict(Counter(r['category'] for r in palette))
assert set(counts) == {'Vehicles', 'Weapons', 'Equipment', 'Scenery', 'Teleporters', 'Goals', 'Spawning'}
kept = [r for r in palette if r['category'] != 'Vehicles']
removed = [r for r in palette if r['category'] == 'Vehicles']
write_csv('standoff-all-tags.csv', tags, ['index', 'offset', 'path', 'group'])
write_csv('standoff-forge-no-vehicles.csv', kept, fields)
write_csv('standoff-excluded-vehicles.csv', removed, fields)
summary = {
    'source_map': 'stock Xbox 360 Standoff (bunkerworld.map)',
    'tag_count': len(tags), 'tag_groups': dict(sorted(Counter(r['group'] for r in tags).items())),
    'forge_counts': counts, 'nonvehicle_forge_entries': len(kept),
    'excluded_vehicle_entries': len(removed),
    'stock_forge_budget': float(re.search(r'SandboxBudget: Single = ([\d.]+)', palette_text)[1]),
    'scope': 'Stock tag inventory and authoring palette candidate; no map edits, conversion, or asset extraction.',
    'limits': ['Full tag inventory intentionally includes vehicle dependencies.',
               'Only the Forge Vehicles category is excluded from the candidate palette.',
               'Stationary turrets and scenery are retained in their original categories.',
               'Tag presence proves stock provenance, not that an MCC version of the tag is byte-compatible.',
               'No new map geometry, material matching, shared-resource payload audit, or memory-fit validation is implied.'],
}
(OUT / 'standoff-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k != 'tag_groups'}, indent=2))
