"""Verify the four approved Forge replacements use complete stock definitions."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    c = Cache(args.map)
    try:
        strings = StringTable(c)
        native = {(t['group'], t['source']): int(t['datum'], 16)
                  for t in report['tags'] if 'native_asset_donor' in t}
        native.update({(t['group'], c.name(n)): t['salt'] << 16 | n
                       for n, t in c.tags.items() if c.name(n)})
        size = int(ET.parse(Path(__file__).resolve().parents[1] /
                           'reference/plugins/vehi.xml').getroot().get('baseSize'), 0)
        checked = []
        for entry in report['tags']:
            if 'stock_equivalent' not in entry:
                continue
            base = native[(entry['group'], entry['stock_equivalent'])]
            result = int(entry['datum'], 16)
            a, b = c.tags[base & 65535]['offset'], c.tags[result & 65535]['offset']
            if entry['stock_variant'] is None:
                assert result == base, 'Soccer ball must reference the native object itself'
            else:
                left, right = bytearray(c.data[a:a+size]), bytearray(c.data[b:b+size])
                assert strings.text(c.u(b+0x30)) == entry['stock_variant']
                left[0x30:0x34] = right[0x30:0x34]
                assert left == right, 'Vehicle root differs from stock beyond variant selection'
                model = c.tags[c.u(b+0x40) & 65535]['offset']
                variants = {strings.text(c.u(row)): row for row in c.block(model+0x64, 0x38)}
                assert entry['stock_variant'] in variants
                children = c.block(variants[entry['stock_variant']]+0x20, 0x1c)
                assert children, 'Expected native turret/attachment missing'
                for row in children:
                    datum = c.u(row+24)
                    assert c.tags[datum & 65535]['salt'] == datum >> 16
            checked.append(entry['source'])
        assert len(checked) == 4, checked
        print(json.dumps({'stock_equivalents_verified': checked}))
    finally:
        c.close()


if __name__ == '__main__':
    main()
