"""Compare native vehicle/physics/animation metadata with its disc donors."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from cache_reader import Cache
from string_ids import StringTable
from resource_reader import Resource
import struct
from collections import OrderedDict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('map', 'report', 'disc-maps'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    target = Cache(args.map)
    target_strings = StringTable(target)
    reference = Path(__file__).resolve().parents[1] / 'reference/plugins'
    verified = {}
    resource_count = 0
    shared = {'maps\\' + p.name: p for p in args.disc_maps.glob('*.map')}
    verified_resources = set()
    decoded = OrderedDict()
    try:
        for tag in report['tags']:
            group = tag['group']
            if group not in ('vehi', 'phmo', 'jmad', 'mode', 'bitm') or 'native_asset_donor' not in tag:
                continue
            donor = Cache(args.disc_maps / tag['native_asset_donor'])
            try:
                strings = StringTable(donor)
                source = next(t for n, t in donor.tags.items()
                              if t['group'] == group and donor.name(n) == tag['source'])
                destination = target.tags[int(tag['datum'], 16) & 65535]
                schema = ET.parse(reference / (group + '.xml')).getroot()

                def compare(a, b, node, size):
                    nonlocal resource_count
                    left = bytearray(donor.data[a:a + size])
                    right = bytearray(target.data[b:b + size])
                    for f in node:
                        if 'offset' not in f.attrib:
                            continue
                        offset, kind = int(f.get('offset'), 0), f.tag.lower()
                        x, y = a + offset, b + offset
                        width = 0
                        if kind == 'tagblock':
                            stride = int(f.get('elementSize'), 0)
                            aa, bb = donor.block(x, stride), target.block(y, stride)
                            if len(aa) != len(bb):
                                raise ValueError('Native block count changed: ' + f.get('name'))
                            if group == 'jmad' and f.get('sort') == 'true':
                                aa = sorted(aa, key=lambda p: strings.text(donor.u(p)) or '')
                                bb = sorted(bb, key=lambda p: target_strings.text(target.u(p)) or '')
                            for xx, yy in zip(aa, bb):
                                compare(xx, yy, f, stride)
                            width = 12
                        elif kind == 'stringid':
                            if strings.text(donor.u(x)) != target_strings.text(target.u(y)):
                                raise ValueError('Native string changed: ' + f.get('name'))
                            width = 4
                        elif kind == 'tagref':
                            width = 4 if f.get('withGroup') == 'false' else 16
                        elif kind == 'datum':
                            aa, bb = donor.u(x), target.u(y)
                            if aa != 0xffffffff and '[zone]' in f.get('name', '') and bb not in verified_resources:
                                ra, rb = Resource(donor, aa, shared, decoded), Resource(target, bb, shared, decoded)
                                while len(decoded) > 6:
                                    decoded.popitem(last=False)
                                ends = [0, 0]
                                for pointer, value in ra.fix.items():
                                    slot = {0x40000000: 0, 0x60000000: 1}.get(value & 0xe0000000)
                                    if slot is not None:
                                        length = struct.unpack_from('>I', ra.data, pointer - 12)[0]
                                        ends[slot] = max(ends[slot], (value & 0x1fffffff) + length)
                                for slot, length in enumerate(ends):
                                    if length and ra.raw[slot][:length] != rb.raw[slot][:length]:
                                        raise ValueError('Native resource payload changed: ' + tag['source'])
                                verified_resources.add(bb)
                                resource_count += 1
                            width = 4
                        elif kind == 'dataref':
                            count = donor.u(x)
                            if count != target.u(y):
                                raise ValueError('Native data length changed')
                            if count:
                                xx, yy = donor.pointer(donor.u(x + 12)), target.pointer(target.u(y + 12))
                                if donor.data[xx:xx + count] != target.data[yy:yy + count]:
                                    raise ValueError('Native opaque payload changed')
                            width = 20
                        elif kind == 'shader':
                            width = 4
                        if width:
                            left[offset:offset + width] = bytes(width)
                            right[offset:offset + width] = bytes(width)
                    if left != right:
                        raise ValueError(f'Native scalar/physics bytes changed: {tag["source"]}/{node.get("name", group)}')

                compare(source['offset'], destination['offset'], schema, int(schema.get('baseSize'), 0))
                verified[group] = verified.get(group, 0) + 1
            finally:
                donor.close()
        print(json.dumps({'native_metadata_verified': verified,
                          'native_resource_segments_verified': resource_count,
                          'scope': 'scalar/physics bytes, strings, block counts, opaque payloads and resource bytes'}))
    finally:
        target.close()


if __name__ == '__main__':
    main()
