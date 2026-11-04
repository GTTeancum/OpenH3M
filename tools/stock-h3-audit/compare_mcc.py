"""Compare existing TagTool text reports, without reading asset binaries."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'

def palette(name):
    result = []
    category = None
    text = (OUT / name).read_text(encoding='utf-8-sig')
    assert 'ERROR' not in text.upper()
    for line in text.splitlines():
        marker = re.search(r'CATEGORY (\w+)', line)
        if marker:
            category = marker[1]
        match = re.search(r'Object: CachedTag = \[(0x[0-9A-F]+)\] (.*?)\s*$', line)
        if match:
            result.append(dict(category=category, index=match[1], tag=match[2]))
        for field in ('Name', 'MaxAllowed', 'Cost'):
            match = re.match(field + r': \w+ = (.*?)\s*$', line)
            if match:
                result[-1][field] = match[1]
    assert result and all(len(r) == 6 for r in result)
    return result

stock = palette('standoff-forge-palette.txt')
mcc = palette('standoff-mcc-forge-palette.txt')
key = lambda r: (r['category'], r['tag'])
stock_lookup = {key(r): r for r in stock}
mcc_lookup = {key(r): r for r in mcc}
added = [r for r in mcc if key(r) not in stock_lookup]
missing = [r for r in stock if key(r) not in mcc_lookup]
changed = [dict(stock=r, mcc=mcc_lookup[key(r)]) for r in stock
           if key(r) in mcc_lookup and any(r[f] != mcc_lookup[key(r)][f]
                                         for f in ('Name', 'MaxAllowed', 'Cost'))]
kept = [r for r in stock if r['category'] != 'Vehicles']
kit = ROOT / 'work/editing-kits/h3ek/tags'
missing_files = [r['tag'] for r in kept if not (kit / r['tag']).is_file()]
report = dict(stock_palette_count=len(stock), mcc_palette_count=len(mcc),
              vehicle_free_stock_count=len(kept), mcc_additions=added,
              missing_in_mcc=missing, changed_palette_fields=changed,
              missing_editing_kit_files=missing_files,
              limit='Names and palette fields only; dependencies, behavior and visuals remain unverified.')
report['mcc_duplicate_choices'] = [dict(category=k[0], tag=k[1], count=n)
                                   for k, n in Counter(map(key, mcc)).items() if n > 1]
(OUT / 'standoff-mcc-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
for label, lookup in [('360', stock_lookup), ('mcc', mcc_lookup)]:
    lines = []
    for r in kept:
        if key(r) in lookup:
            lines.extend(['Echo ROOT ' + r['tag'], 'TagDependency List ' + lookup[key(r)]['index']])
    (OUT / f'dependencies-{label}.commands').write_text('\n'.join(lines) + '\n')
print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in report.items()}, indent=2))

def dependencies(label):
    text = (OUT / f'dependencies-{label}.txt').read_text(encoding='utf-8-sig')
    assert not re.search(r'ERROR|Exception|Warning', text)
    result = {}
    root = None
    for line in text.splitlines():
        marker = re.match(r'ROOT (\S+)', line)
        if marker:
            root = marker[1]
            result[root] = set()
        match = re.search(r'\[Index: 0x[0-9A-F]+, Offset: 0x[0-9A-F]+\] (.*?)\s*$', line)
        if match:
            assert root
            result[root].add(match[1])
    assert len(result) == len(kept)
    return result

if all((OUT / f'dependencies-{label}.txt').exists() for label in ('360', 'mcc')):
    a, b = dependencies('360'), dependencies('mcc')
    diffs = [dict(root=k, mcc_added=sorted(b[k]-a[k]), mcc_removed=sorted(a[k]-b[k]))
             for k in a if a[k] != b[k]]
    dep_report = dict(roots_compared=len(a), changed_roots=diffs,
                      limit='Immediate tag references only, not recursive closure or content equivalence.')
    (OUT / 'standoff-dependency-comparison.json').write_text(json.dumps(dep_report, indent=2)+'\n')
    print(json.dumps(dict(dependency_roots=len(a), changed_roots=len(diffs))))
