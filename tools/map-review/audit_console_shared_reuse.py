"""Find exact page identities already present in stock shared resource stores.

Read-only planning evidence: descriptor hashes are candidates, not byte proof.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache


def page_key(c, p):
    return c.u(p+16), c.data[p+24:p+44].hex()


def main():
    stock = {}
    for path in sorted((ROOT/'../../maps').glob('*.map')):
        if path.stem in ('shared', 'campaign', 'mainmenu'):
            continue
        c = Cache(path)
        play = next((t['offset'] for t in c.tags.values() if t['group']=='play'), None)
        if play is not None:
            files = c.block(play+12, 264)
            for p in c.block(play+24, 88):
                shared = c.unpack('h', p+4)[0]
                if shared < 0 or not c.u(p+12):
                    continue
                at = files[shared]
                name = c.data[at:at+256].split(b'\0')[0].decode('ascii')
                stock.setdefault(page_key(c,p), dict(donor=path.name,shared_file=name,
                    offset=c.u(p+8),compressed_bytes=c.u(p+12),decoded_bytes=c.u(p+16)))
        c.close()
    manifest = json.loads((ROOT/'.local/releases/current-live/manifest.json').read_text())
    reports = []
    for bundle in manifest['packages']:
        for name in bundle['maps']:
            path = Path(bundle['installed_source'])/(name+'.map')
            if path.stat().st_size <= 157286400:
                continue
            c = Cache(path)
            play = next(t['offset'] for t in c.tags.values() if t['group']=='play')
            matches = []
            unique = {}
            for i,p in enumerate(c.block(play+24,88)):
                if c.unpack('h',p+4)[0] != -1 or not c.u(p+12):
                    continue
                key = page_key(c,p)
                if key in stock:
                    matches.append(dict(page=i,local_bytes=c.u(p+12),stock=stock[key]))
                    unique[(c.u(p+8),c.u(p+12))] = (c.u(p+12)+4095)&~4095
            reports.append(dict(map=name,candidate_reusable_bytes=sum(unique.values()),matches=matches))
            print(name,len(matches),sum(unique.values()),flush=True)
            c.close()
    (ROOT/'work/elongation-console-diagnostic/shared-page-reuse-audit.json').write_text(json.dumps(dict(
        scope='Descriptor identity candidates only; requires exact byte verification before reuse',
        unique_stock_shared_pages=len(stock),maps=reports),indent=2)+'\n')


if __name__ == '__main__':
    main()
