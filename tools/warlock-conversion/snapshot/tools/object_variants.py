"""Resolve source variants only after proving their changes against a stock tag.

Do not infer equivalence from names. Walk all schema fields, nested arrays and
data payloads. A recognized scalar delta is applied to a retail clone, retaining
its platform-native dependency graph. Any other difference stops conversion.
"""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from scenario_placements import FORMATS


VARIANTS = (
    ('bloc', r'levels\multi\warlock\fx\teleporter_sender\teleporter_sender',
     r'objects\multi\teleporter_sender\teleporter_sender', {}),
    ('eqip', r'levels\multi\warlock\fx\powerup_blue\powerup_blue',
     r'objects\multi\powerups\powerup_blue\powerup_blue', {'Bounding Radius': 'f'}),
)


def differences(cache, schema, left, right, prefix='', depth=0):
    if depth > 32:
        raise ValueError('Variant schema nesting exceeded')
    result = []
    for field in schema:
        if field.get('offset') is None:
            continue
        kind = field.tag.lower()
        path = prefix + field.get('name')
        offset = int(field.get('offset'), 0)
        a, b = left + offset, right + offset
        if kind == 'tagblock':
            stride = int(field.get('elementSize'), 0)
            ar, br = cache.block(a, stride), cache.block(b, stride)
            if len(ar) != len(br):
                result.append((path, 'block count'))
            else:
                for index, (aa, bb) in enumerate(zip(ar, br)):
                    result.extend(differences(cache, field, aa, bb, path + f'[{index}]/', depth + 1))
        elif kind == 'dataref':
            def payload(at):
                count = cache.u(at)
                if not count:
                    return b''
                start = cache.pointer(cache.u(at + 12))
                if start + count > len(cache.data):
                    raise ValueError('Variant data payload outside map')
                return cache.data[start:start + count]
            if payload(a) != payload(b):
                result.append((path, 'data payload'))
        else:
            fmt = FORMATS.get(kind) or {'rangef': '2f', 'uint32': 'I', 'undefined': 'I',
                                       'tagref': '4I', 'colorf': '3f', 'degree2': '2f'}.get(kind)
            if fmt is None:
                raise ValueError(f'Unverified variant field {path}: {kind}')
            size = struct.calcsize('<' + fmt)
            # Compare raw scalar bits as well as unusual NaNs / signed zero.
            if cache.data[a:a + size] != cache.data[b:b + size]:
                result.append((path, fmt))
    return result


def resolve_variants(source, target, newtag, reference=None):
    reference = reference or Path(__file__).resolve().parents[1] / 'reference'
    src = {(t['group'], source.name(i)): t for i, t in source.tags.items()}
    dst = {(t['group'], target.name(i)): (i, t) for i, t in target.tags.items()}
    resolved, report = {}, []
    for group, custom_name, stock_name, permitted in VARIANTS:
        if (group, custom_name) not in src:
            continue
        custom, stock = src[group, custom_name], src[group, stock_name]
        index, retail = dst[group, stock_name]
        ss = ET.parse(reference / 'mcc' / f'{group}.xml').getroot()
        ds = ET.parse(reference / 'plugins' / f'{group}.xml').getroot()
        changes = differences(source, ss, custom['offset'], stock['offset'])
        if any(permitted.get(name) != fmt for name, fmt in changes):
            raise ValueError(f'{custom_name}: unhandled variant changes {changes}')
        if not changes:
            datum = (retail['salt'] << 16) | index
        else:
            size = int(ds.get('baseSize'), 0)
            payload = bytearray(target.data[retail['offset']:retail['offset'] + size])
            for name, fmt in changes:
                sf = next(x for x in ss if x.get('name') == name)
                df = next(x for x in ds if x.get('name') == name)
                if sf.tag.lower() != df.tag.lower():
                    raise ValueError('Variant field type differs across platforms')
                values = source.unpack(fmt, custom['offset'] + int(sf.get('offset'), 0))
                struct.pack_into('>' + fmt, payload, int(df.get('offset'), 0), *values)
            datum, _ = newtag(group, payload)
        resolved[group, custom_name] = datum
        report.append({'source': custom_name, 'retail_base': stock_name,
                       'changed_fields': [name for name, _ in changes], 'datum': hex(datum)})
    return resolved, report
