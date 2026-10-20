"""Verify every serialized Forge object reference against the source palette."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'map', 'report'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    imported = {int(t['datum'], 16): (t['group'], t['source']) for t in report['tags']}
    reference = Path(__file__).resolve().parents[1] / 'reference'
    source, target = Cache(args.source, True), Cache(args.map)
    try:
        roots = [next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
                 for c in (source, target)]
        schemas = [ET.parse(reference / kind / 'scnr.xml').getroot() for kind in ('mcc', 'plugins')]
        counts = {}
        for category in ('Vehicle', 'Weapon', 'Equipment', 'Scenery', 'Teleporter', 'Goal', 'Spawner'):
            name = 'Map Variant ' + category + ' Palette'
            fields = [next(n for n in schema if n.get('name') == name) for schema in schemas]
            rows = [c.block(root + int(f.get('offset'), 0), int(f.get('elementSize'), 0))
                    for c, root, f in zip((source, target), roots, fields)]
            if len(rows[0]) != len(rows[1]):
                raise ValueError(f'{category}: palette count changed')
            offsets = [next(int(n.get('offset'), 0) + 12 for n in f if n.tag.lower() == 'tagref')
                       for f in fields]
            for index, (a, b) in enumerate(zip(*rows)):
                src, dst = source.u(a + offsets[0]), target.u(b + offsets[1])
                if src == dst == 0xffffffff:
                    continue
                st, dt = source.tags[src & 65535], target.tags[dst & 65535]
                expected = st['group'], source.name(src & 65535)
                actual = imported.get(dst, (dt['group'], target.name(dst & 65535)))
                if dt['salt'] != dst >> 16 or actual != expected or dt['group'] != st['group']:
                    raise ValueError(f'{category}[{index}]: object reference changed: {expected} -> {actual}')
            counts[category] = len(rows[0])
        print(json.dumps({'forge_objects_verified': sum(counts.values()), 'categories': counts}))
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    main()
