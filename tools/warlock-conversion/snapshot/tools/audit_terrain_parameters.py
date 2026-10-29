"""Read terrain specular constants from stock, source, and converted caches."""
import argparse
import json
from pathlib import Path

from cache_reader import Cache
from string_ids import StringTable


def inspect(path, mcc=False):
    cache = Cache(path, mcc)
    try:
        strings = StringTable(cache)
        result = []
        for index, tag in cache.tags.items():
            if tag['group'] != 'rmtr':
                continue
            for post in cache.block(tag['offset'] + 40, 140 if mcc else 132):
                template = cache.u(post + 12) & 65535
                root = cache.tags[template]['offset']
                names = [strings.text(cache.u(row)) for row in cache.block(root + 72, 4)]
                values = cache.block(post + 28, 16)
                if len(names) != len(values):
                    raise ValueError('Terrain parameter count mismatch')
                result.append({'material': cache.name(index), 'material_index': index,
                    'template': cache.name(template), 'template_index': template,
                    'parameters': {name: cache.unpack('4f', row) for name, row in zip(names, values)
                                   if any(term in name for term in ('specular', 'fresnel', 'reflection'))}})
        return result
    finally:
        cache.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retail', nargs='+', required=True)
    parser.add_argument('--mcc')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = {str(path): inspect(path) for path in args.retail}
    if args.mcc:
        report[args.mcc] = inspect(args.mcc, True)
    args.report.write_text(json.dumps(report, indent=2))
    print('Terrain materials inspected:', {path: len(rows) for path, rows in report.items()})
