"""Select retained Assembly schemas by cache build, without changing source bytes.

The April 2022 MCC layout predates the December 2022 and July 2023 changes.
Only the observed build is enabled; this is not a date-range compatibility claim.
Callers receive fresh XML trees because conversion stages may annotate them.
"""
import json
import struct
from pathlib import Path
import xml.etree.ElementTree as ET


REFERENCE = Path(__file__).resolve().parents[1] / 'reference'
MCC_2022_BUILD = 'Apr 20 2022 11:55:21'
# Verified Halo3 inheritance already used by TagImporter for modern MCC.
SHARED_MCC_SCHEMAS = {
    'jmad', 'ligh', 'jpt!', 'lsnd', 'rwrd', 'snde', 'skya', 'chmt', 'dctr',
    'wind', 'chad', 'foot', 'drdf', 'pmdf', 'styl', 'sefc', 'trak', 'cddf',
    'pmov', 'flck',
}


def profile(cache):
    if not cache.mcc:
        return 'retail'
    build = bytes(cache.data[0xA0:0xC0]).split(b'\0', 1)[0].decode('ascii')
    return 'mcc-2022' if build == MCC_2022_BUILD else 'mcc'


def schema_path(cache, group, reference=None):
    reference = Path(reference) if reference is not None else REFERENCE
    group = group.rstrip()
    if not group or any(c in group for c in '/\\:'):
        raise ValueError(f'Invalid schema group: {group!r}')
    filename = group + '.xml'
    selected = profile(cache)
    if selected == 'mcc-2022':
        manifest = json.loads((reference / selected / 'manifest.json').read_text(encoding='utf-8'))
        overrides = {item['file']: item['schema'] for item in manifest['files']}
        if filename in overrides:
            path = reference / overrides[filename]
        elif filename in manifest['inherits']:
            path = reference / 'plugins' / filename
        else:
            raise ValueError(f'{group}: absent from the pinned MCC 2022 schema set and Halo3 inheritance')
    else:
        folder = 'plugins' if selected == 'retail' or group in SHARED_MCC_SCHEMAS else 'mcc'
        path = reference / folder / filename
    if not path.is_file():
        raise ValueError(f'{group}: missing {selected} schema: {path}')
    return path


def load_schema(cache, group, reference=None):
    return ET.parse(schema_path(cache, group, reference)).getroot()


def validate_tree(cache, root, schema):
    """Check every nested block, data allocation and tag reference in one tag.

    This establishes structural readability only, not conversion support or
    semantic correctness. It follows schema blocks, never dependency graphs.
    """
    counts = dict(block_headers=0, block_rows=0, tag_references=0, data_references=0)
    errors = []

    def walk(node, base, label, depth=0):
        if depth > 32:
            raise ValueError('Schema nesting exceeds 32 levels')
        for field in node:
            if field.get('offset') is None or '[Readable]' in field.get('name', ''):
                continue
            at = base + int(field.get('offset'), 0)
            path = label + '/' + field.get('name', '?')
            kind = field.tag.lower()
            try:
                if kind == 'tagblock':
                    count, pointer = cache.unpack('II', at)
                    counts['block_headers'] += 1
                    if not count:
                        continue
                    stride = int(field.get('elementSize'), 0)
                    start = cache.pointer(pointer)
                    if stride <= 0 or start + count * stride > len(cache.data):
                        raise ValueError('Block allocation exceeds cache bounds')
                    if counts['block_rows'] + count > 1000000:
                        raise ValueError('Schema walk exceeds one million rows')
                    counts['block_rows'] += count
                    for index in range(count):
                        walk(field, start + index * stride, f'{path}[{index}]', depth + 1)
                elif kind == 'tagref':
                    with_group = field.get('withGroup', 'true') != 'false'
                    datum = cache.u(at + 12 if with_group else at)
                    if datum == 0xffffffff:
                        continue
                    target = cache.tags.get(datum & 65535)
                    if target is None or target['salt'] != datum >> 16:
                        raise ValueError(f'Invalid tag datum {datum:#x}')
                    if with_group:
                        group = bytes(cache.data[at:at + 4])
                        if cache.mcc:
                            group = group[::-1]
                        if group != target['group'].encode('ascii'):
                            raise ValueError(f'Tag group differs from datum {datum:#x}')
                    counts['tag_references'] += 1
                elif kind == 'dataref':
                    size = cache.u(at)
                    if size:
                        start = cache.pointer(cache.u(at + 12))
                        if start + size > len(cache.data):
                            raise ValueError('Data allocation exceeds cache bounds')
                    counts['data_references'] += 1
            except (ValueError, KeyError, IndexError, struct.error) as error:
                errors.append(dict(field=path, error=str(error)))

    walk(schema, root, 'root')
    return dict(profile=profile(cache), counts=counts, errors=errors,
                valid=not errors, scope='Structural readability only; not conversion or runtime acceptance')
