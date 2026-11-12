"""Find exact authored base-mip matches across original H3 bitmap donors.

Uses the same verified native untile and MCC resource readers as the existing
mip audits. A nonmatch is not proof that no visually equivalent material exists.
Unsupported formats/resources are reported, never treated as nonmatches.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np

from cache_reader import Cache
from encode_bitmap import mip_size
from mcc_bitmap_source import BitmapSource
from native_assets import NativeAssets
from resource_reader import Resource
from xbox_bitmap import untile_base


def audit(source_path, disc_maps, prefix):
    source = Cache(source_path, True)
    try:
        bitmaps = BitmapSource(source)
        wanted, source_rows, skipped = {}, [], []
        for index, tag in source.tags.items():
            name = source.name(index)
            if tag['group'] != 'bitm' or not name.startswith(prefix):
                continue
            infos = bitmaps.info(index)
            if len(infos) != 1:
                skipped.append(dict(source=name, reason='Multiple bitmap images'))
                continue
            info = infos[0]
            w, h, fmt = info['width'], info['height'], info['format']
            row = source.block(tag['offset'] + 96, 56)[0]
            if (source.unpack('H', row + 10)[0] != 0 or min(w, h) < 32
                    or fmt not in (11, 14, 15, 16, 22, 26, 28, 33)):
                skipped.append(dict(source=name, reason='Outside 2D base-mip comparison scope',
                                    width=w, height=h, format=fmt))
                continue
            payload = bitmaps.pixels(index)[:mip_size(w, h, fmt)]
            if fmt == 33:
                # Same signed-BC5 endpoint conversion used by audit_missing_mips.
                blocks = np.frombuffer(payload, dtype=np.uint8).reshape(-1, 16).copy()
                for column in (0, 1, 8, 9):
                    blocks[:, column] = (blocks[:, column].astype(np.uint16) + 128) % 256
                payload = blocks.tobytes()
            key = w, h, fmt, hashlib.sha256(payload).hexdigest()
            result = dict(source=name, index=index, width=w, height=h, format=fmt,
                          base_sha256=key[3], matches=[])
            source_rows.append(result)
            wanted.setdefault(key, []).append(result)
        dimensions = {key[:3] for key in wanted}
        inventory = NativeAssets(None, disc_maps)
        compared, failures, digests = 0, [], {}
        donors = sorted((path, index, name)
                        for (group, name), candidates in inventory.candidates.items() if group == 'bitm'
                        for path, index in candidates)
        cache, current_path = None, None
        try:
            for donor_path, index, name in donors:
                if donor_path != current_path:
                    if cache is not None:
                        cache.close()
                    cache, current_path = Cache(donor_path), donor_path
                    cache.decoded_pages = {}
                    zone = next(t['offset'] for t in cache.tags.values() if t['group'] == 'zone')
                    play = next(t['offset'] for t in cache.tags.values() if t['group'] == 'play')
                    resources = cache.block(zone + 88, 64)
                    locations = cache.block(play + 48, 16)
                    pages = cache.block(play + 24, 88)
                    files = cache.block(play + 12, 264)
                    filenames = [bytes(cache.data[p:p + 256]).split(b'\0')[0].decode('ascii') for p in files]
                    print('Bitmap donors:', donor_path.name, flush=True)
                rows = cache.block(cache.tags[index]['offset'] + 96, 48)
                handles = cache.block(cache.tags[index]['offset'] + 140, 8)
                if len(rows) != 1 or len(handles) != 1:
                    continue
                row = rows[0]
                w, h = cache.unpack('HH', row + 4)
                fmt = cache.unpack('H', row + 12)[0]
                if (w, h, fmt) not in dimensions or cache.unpack('H', row + 10)[0] != 0:
                    continue
                try:
                    datum = cache.u(handles[0])
                    if datum == 0xffffffff or (datum & 65535) >= len(resources):
                        raise ValueError('Missing bitmap resource')
                    owner = resources[datum & 65535]
                    if cache.unpack('H', owner + 16)[0] != datum >> 16 or not cache.u(owner + 24):
                        raise ValueError('Stripped or invalid bitmap resource')
                    location_index = cache.unpack('h', owner + 34)[0]
                    if not 0 <= location_index < len(locations):
                        raise ValueError('Missing bitmap resource location')
                    location = locations[location_index]
                    storage = []
                    for slot, page_index in enumerate(cache.unpack('hh', location)):
                        if page_index == -1:
                            storage.append(None)
                            continue
                        page = pages[page_index]
                        shared = cache.unpack('h', page + 4)[0]
                        filename = str(donor_path) if shared < 0 else filenames[shared]
                        storage.append((filename, *cache.unpack('4I', page + 8),
                                        cache.u(location + 4 + slot * 4)))
                    key = (w, h, fmt, cache.data[row + 9], *storage)
                    digest = digests.get(key)
                    if digest is None:
                        resource = Resource(cache, datum, shared_paths={
                            r'maps\shared.map': Path(disc_maps) / 'shared.map',
                            r'maps\mainmenu.map': Path(disc_maps) / 'mainmenu.map'})
                        if (len(resource.data) != 64 or resource.unpack('HH', 40) != (w, h)
                                or resource.data[44] != 1 or resource.data[46] != 0
                                or resource.data[47] not in (0, 1)):
                            raise ValueError('Bitmap control layout requires separate comparison')
                        segment = resource.data[47]
                        raw = untile_base(resource.raw[segment], w, h, fmt)
                        digest = digests[key] = hashlib.sha256(raw).hexdigest()
                        compared += 1
                        if sum(map(len, cache.decoded_pages.values())) > 64 * 1024 * 1024:
                            cache.decoded_pages.clear()
                    for match in wanted.get((w, h, fmt, digest), []):
                        match['matches'].append(dict(donor=str(donor_path), index=index,
                            name=name, resource_datum=hex(cache.u(handles[0])), base_sha256=digest))
                    # Deduplicate only identical physical storage. Same-name
                    # bitmaps in different maps are not assumed identical.
                except (ValueError, AssertionError, IndexError, KeyError) as error:
                    failures.append(dict(donor=str(donor_path), index=index, name=name, error=str(error)))
        finally:
            if cache is not None:
                cache.close()
        return dict(scope='Exact base payload matching after native untile; not shader equivalence or runtime proof',
                    source=str(source_path), prefix=prefix, source_bitmaps=source_rows,
                    skipped_source=skipped, donor_failures=failures, native_bitmaps_compared=compared,
                    matched_source_bitmaps=sum(bool(row['matches']) for row in source_rows),
                    failure_reasons=dict(Counter(row['error'] for row in failures)))
    finally:
        source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--disc-maps', type=Path, required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    args.report.resolve().relative_to(Path(__file__).resolve().parents[4])
    result = audit(args.source, args.disc_maps, args.prefix)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('native_bitmaps_compared', 'matched_source_bitmaps', 'failure_reasons')}))
