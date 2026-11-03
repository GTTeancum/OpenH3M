"""Read-only audit of a terrain template's specialized native draw programs/routes."""
import argparse
import hashlib
import json
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable


def template_snapshot(cache, root):
    strings = StringTable(cache)
    def block(offset, stride):
        return [bytes(cache.data[row:row + stride]).hex()
                for row in cache.block(root + offset, stride)]
    result = {'available_entries': cache.u(root + 32),
              'entry_ranges': block(36, 2), 'passes': block(48, 28),
              'routes': block(60, 4),
              'parameters': {str(offset): [strings.text(cache.u(row))
                  for row in cache.block(root + offset, 4)]
                  for offset in (72, 84, 96, 108)}}
    for offset, kind in ((0, 'vertex'), (16, 'pixel')):
        datum = cache.u(root + offset + 12)
        if datum == 0xffffffff:
            result[kind] = None
            continue
        shader = cache.tags[datum & 65535]['offset']
        entries = cache.block(shader + 4, 12 if kind == 'vertex' else 2)
        entry_table = ([[bytes(cache.data[r:r+2]).hex() for r in cache.block(e, 2)]
                        for e in entries] if kind == 'vertex'
                       else [bytes(cache.data[e:e+2]).hex() for e in entries])
        programs = []
        for row in cache.block(shader + 20, 80):
            pointer = cache.u(row + 76)
            digest = None
            if pointer:
                header = cache.pointer(pointer)
                debug = header + (0x368 if kind == 'vertex' else 0x28)
                size = cache.u(debug + 8)
                start = cache.pointer(cache.u(header + 16))
                if size <= 0 or start < 0 or start + size > len(cache.data):
                    raise ValueError('Shader microcode outside cache')
                digest = hashlib.sha256(cache.data[start:start+size]).hexdigest()
            constants = [(strings.text(cache.u(r)), *cache.unpack('HBB', r + 4))
                         for r in cache.block(row + 40, 8)]
            programs.append({'microcode': digest, 'constants': constants})
        result[kind] = {'flags': cache.u(shader), 'entries': entry_table, 'programs': programs}
    return result


def verify(candidate, donor, material_index, template_name):
    target, stock = Cache(candidate), Cache(donor)
    try:
        material = target.tags[material_index]
        if material['group'] != 'rmtr':
            raise ValueError('Selected material is not terrain')
        post = target.block(material['offset'] + 40, 132)[0]
        root = target.tags[target.u(post + 12) & 65535]['offset']
        donor_roots = [v['offset'] for k, v in stock.tags.items()
                       if v['group'] == 'rmt2' and stock.name(k) == template_name]
        if len(donor_roots) != 1:
            raise ValueError('Expected exactly one donor template')
        actual, expected = template_snapshot(target, root), template_snapshot(stock, donor_roots[0])
        checks = {key: actual[key] == expected[key] for key in expected}
        return {'candidate': str(candidate), 'material_index': material_index,
                'donor': str(donor), 'template': template_name,
                'passed': all(checks.values()), 'checks': checks, 'target': actual,
                'scope': 'Cache programs, parameter names, pass states and routes; does not prove runtime binding or rendered output.'}
    finally:
        target.close()
        stock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('candidate', 'donor', 'report'):
        parser.add_argument('--' + key, required=True, type=Path)
    parser.add_argument('--material-index', required=True, type=int)
    parser.add_argument('--template', required=True)
    args = parser.parse_args()
    result = verify(args.candidate, args.donor, args.material_index, args.template)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'checks': result['checks']}))
    raise SystemExit(0 if result['passed'] else 1)
