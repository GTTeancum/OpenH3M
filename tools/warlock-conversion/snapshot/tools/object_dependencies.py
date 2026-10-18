"""Inventory direct dependencies of unresolved placement tags without extraction."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache
from assemble_scenario import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference = Path(__file__).resolve().parents[1] / 'reference'
    source, target = Cache(args.source, True), Cache(args.candidate)
    try:
        source_names = {(t['group'], source.name(i)): t for i, t in source.tags.items()}
        retail_names = {(t['group'], target.name(i)) for i, t in target.tags.items()}
        plan = prepare(source, target, ET.parse(reference / 'mcc/scnr.xml').getroot(),
                       ET.parse(reference / 'plugins/scnr.xml').getroot())
        roots = sorted({tuple(x['tag']) for x in plan['unresolved'] if 'tag' in x})
        report = []
        for group, name in roots:
            schema = ET.parse(reference / 'mcc' / f'{group}.xml').getroot()
            dependencies = []

            def walk(node, offset, depth=0):
                if depth > 32:
                    raise ValueError('Schema nesting limit exceeded')
                for field in node:
                    if field.get('offset') is None or '[Readable]' in field.get('name', ''):
                        continue
                    at = offset + int(field.get('offset'), 0)
                    if field.tag.lower() == 'tagref':
                        datum = source.u(at + 12)
                        if datum == 0xffffffff:
                            continue
                        tag = source.tags[datum & 65535]
                        key = tag['group'], source.name(datum & 65535)
                        dependencies.append({'group': key[0], 'name': key[1],
                                             'in_retail': key in retail_names})
                    elif field.tag.lower() == 'tagblock':
                        for row in source.block(at, int(field.get('elementSize'), 0)):
                            walk(field, row, depth + 1)

            walk(schema, source_names[group, name]['offset'])
            report.append({'group': group, 'name': name, 'dependencies': dependencies})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f'{len(report)} unresolved object tags inventoried; direct dependencies only.')
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    main()
