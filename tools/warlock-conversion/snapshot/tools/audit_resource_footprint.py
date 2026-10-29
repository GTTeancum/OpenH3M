"""Compare retail resource-page demand, without decoding or copying game assets.

This is a static inventory, not measured runtime residency or a console budget
certificate. Shared pages count too. Multiple resources using one page count it
once; required/optional columns overlap and must not be added together.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache


def inspect(path):
    cache = Cache(path)
    try:
        zone = next(t['offset'] for t in cache.tags.values() if t['group'] == 'zone')
        play = next(t['offset'] for t in cache.tags.values() if t['group'] == 'play')
        resources = cache.block(zone + 88, 64)
        locations = cache.block(play + 48, 16)
        pages = cache.block(play + 24, 88)
        shared = cache.block(play + 12, 264)
        names = [cache.data[p:p+256].split(b'\0', 1)[0].decode('ascii') for p in shared]
        descriptors = []
        for page in pages:
            source = cache.unpack('h', page + 4)[0]
            if source < -1 or source >= len(names):
                raise ValueError('Invalid shared file index')
            block, compressed, size = cache.unpack('III', page + 8)
            # Identity is physical storage, not content hash: identical payloads
            # at different locations can still consume distinct allocations.
            key = (names[source] if source >= 0 else str(Path(path).resolve()), block)
            descriptors.append((key, size, compressed, source >= 0))
        required, optional = {}, {}
        control = 0
        owners = {}
        resource_pages = {}
        resource_required_pages = {}
        for index, resource in enumerate(resources):
            control += cache.u(resource + 24)
            location = cache.unpack('h', resource + 34)[0]
            if location == -1:
                continue
            if not 0 <= location < len(locations):
                raise ValueError('Invalid resource location')
            for column, page_index in zip((required, optional), cache.unpack('hh', locations[location])):
                if page_index == -1:
                    continue
                if not 0 <= page_index < len(pages):
                    raise ValueError('Invalid resource page')
                key, size, compressed, is_shared = descriptors[page_index]
                # Retail empty optional pages reuse the next block's offset.
                if size == 0 and compressed == 0:
                    continue
                value = (size, compressed, is_shared)
                if key in column and column[key] != value:
                    raise ValueError('Conflicting page descriptions')
                column[key] = value
                owners.setdefault(key, set()).add(index)
                resource_pages.setdefault(index, {})[key] = value
                if column is required:
                    resource_required_pages.setdefault(index, {})[key] = value

        def totals(collection):
            return {'pages': len(collection),
                    'uncompressed_bytes': sum(v[0] for v in collection.values()),
                    'compressed_bytes': sum(v[1] for v in collection.values()),
                    'shared_uncompressed_bytes': sum(v[0] for v in collection.values() if v[2])}

        manifests = []
        required_manifest_pages = {}
        required_manifest_base_pages = {}
        streamed_manifest_pages = {}
        schema = ET.parse(Path(__file__).resolve().parents[1] / 'reference/plugins/zone.xml').getroot()
        for field in schema:
            if field.tag != 'tagblock' or 'Manifest' not in field.get('name', ''):
                continue
            for ordinal, row in enumerate(cache.block(zone + int(field.get('offset'), 0), int(field.get('elementSize'), 0))):
                masks = {}
                for bits in field:
                    label = bits.get('name', '')
                    if bits.tag != 'tagblock' or 'Resource' not in label or 'Bits' not in label:
                        continue
                    selected = set()
                    for word_index, word_at in enumerate(cache.block(row + int(bits.get('offset'), 0), 4)):
                        value = cache.u(word_at)
                        selected.update(word_index * 32 + bit for bit in range(32) if value & (1 << bit))
                    invalid = selected - set(range(len(resources)))
                    if invalid:
                        raise ValueError(f'{label}: bits exceed resource table: {sorted(invalid)[:5]}')
                    selected_pages = {}
                    for index in selected:
                        selected_pages.update(resource_pages.get(index, {}))
                    if label == 'Required Resource Bits':
                        required_manifest_pages.update(selected_pages)
                        for index in selected:
                            required_manifest_base_pages.update(resource_required_pages.get(index, {}))
                    elif label == 'Streamed Resource Bits':
                        streamed_manifest_pages.update(selected_pages)
                    masks[label] = {'resources': len(selected),
                                    'required_and_optional_page_inventory': totals(selected_pages)}
                manifests.append({'name': field.get('name'), 'index': ordinal, 'resource_sets': masks})
        union = dict(required)
        for key, value in optional.items():
            if key in union and union[key] != value:
                raise ValueError('Required/optional page descriptions conflict')
            union[key] = value
        largest = sorted(union, key=lambda key: union[key][0], reverse=True)[:12]
        return {'map': str(Path(path).resolve()), 'file_bytes': Path(path).stat().st_size,
                'tag_memory_bytes': cache.u(0x18), 'resource_count': len(resources),
                'resource_control_bytes': control, 'required_pages': totals(required),
                'optional_pages': totals(optional), 'all_referenced_pages': totals(union),
                'manifests': manifests,
                'all_manifest_required_page_union': totals(required_manifest_pages),
                'all_manifest_required_base_page_union': totals(required_manifest_base_pages),
                'all_manifest_streamed_page_union': totals(streamed_manifest_pages),
                'manifest_union_scope': 'Deduplicated across every manifest, including alternatives; includes required and optional physical pages of selected resources. Not simultaneous residency.',
                'largest_pages': [{'source': key[0], 'block': key[1], 'uncompressed_bytes': union[key][0],
                                   'owners': [{'index': i, 'owner_datum': hex(cache.u(resources[i] + 12)),
                                               'group': cache.tags.get(cache.u(resources[i] + 12) & 65535, {}).get('group'),
                                               'tag': cache.name(cache.u(resources[i] + 12) & 65535)}
                                              for i in sorted(owners[key])]} for key in largest]}
    finally:
        cache.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps', nargs='+', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[4]
    report = args.report.resolve()
    report.relative_to(repo)
    result = {'scope': 'All referenced resource pages, including shared; not simultaneous residency. '
                       'Required and optional page totals overlap. Excludes allocator overhead, '
                       'simulation, render targets, executable and streaming staging.',
              'retail_console_budget_verified': False, 'maps': [inspect(p) for p in args.maps]}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for item in result['maps']:
        print(Path(item['map']).name, 'tag bytes', item['tag_memory_bytes'],
              'referenced page bytes', item['all_referenced_pages']['uncompressed_bytes'])


if __name__ == '__main__':
    main()
