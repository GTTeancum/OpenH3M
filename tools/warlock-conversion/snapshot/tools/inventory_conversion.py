"""Read-only semantic inventory of source content and the converted scenario.

Counts are evidence of omissions, not proof that equal-count content is correct.
No assets are extracted. All paths are explicit; reports belong in the project.
"""
import argparse
import collections
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache
from scenario_placements import plan_placements


def describe_reference(cache, datum):
    if datum == 0xffffffff:
        return None
    tag = cache.tags.get(datum & 0xffff)
    if not tag:
        return {'invalid_datum': hex(datum)}
    return {'group': tag['group'], 'name': cache.name(datum & 0xffff)}


def scenario(cache, schema):
    tag = next(t for t in cache.tags.values() if t['group'] == 'scnr')
    blocks, references = {}, {}
    for field in schema:
        kind, name = field.tag.lower(), field.get('name')
        if kind not in ('tagblock', 'tagref'):
            continue
        offset = tag['offset'] + int(field.get('offset'), 0)
        if kind == 'tagref':
            references[name] = describe_reference(cache, cache.u(offset + 12))
            continue
        rows = cache.block(offset, int(field.get('elementSize'), 0))
        item = {'count': len(rows)}
        ref_fields = [f for f in field if f.tag.lower() == 'tagref']
        if ref_fields:
            item['references'] = [
                {f.get('name'): describe_reference(cache, cache.u(row + int(f.get('offset'), 0) + 12))
                 for f in ref_fields} for row in rows]
        blocks[name] = item
    return {'blocks': blocks, 'references': references}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    refs = Path(__file__).resolve().parents[1] / 'reference'
    source, target = Cache(args.source, True), Cache(args.candidate)
    try:
        src = scenario(source, ET.parse(refs / 'mcc/scnr.xml').getroot())
        dst = scenario(target, ET.parse(refs / 'plugins/scnr.xml').getroot())
        placements = plan_placements(source, target, ET.parse(refs / 'mcc/scnr.xml').getroot(),
                                     ET.parse(refs / 'plugins/scnr.xml').getroot())
        differences = []
        for name in sorted(src['blocks'].keys() | dst['blocks'].keys()):
            a, b = src['blocks'].get(name), dst['blocks'].get(name)
            if a != b:
                differences.append({'block': name, 'source': a, 'candidate': b})
        target_names = {(t['group'], target.name(i)) for i, t in target.tags.items()}
        missing = [dict(group=t['group'], name=source.name(i)) for i, t in source.tags.items()
                   if (t['group'], source.name(i)) not in target_names]
        report = {'note': 'Missing names are an inventory, not proof of missing runtime dependencies; imported tags may be unnamed.',
                  'source': str(args.source), 'candidate': str(args.candidate),
                  'scenario_differences': differences,
                  'source_scenario': src, 'candidate_scenario': dst,
                  'source_tags_absent_by_name': missing,
                  'placement_plan': {name: {'source_count': p['source_count'],
                      'convertible_count': len(p['converted']), 'unresolved': p['unresolved']}
                      for name, p in placements.items()},
                  'absent_by_group': dict(collections.Counter(t['group'] for t in missing))}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        for d in differences:
            print(f"{d['block']}: {d['source']['count'] if d['source'] else '-'} -> {d['candidate']['count'] if d['candidate'] else '-'}")
        print('Report:', args.output)
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    main()
