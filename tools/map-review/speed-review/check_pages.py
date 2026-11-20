"""Read-only: verify every locally stored resource page of a native map (size, CRC, salted hashes)."""
import hashlib, sys, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from build_scenario_checkpoint import resource_salt
c = Cache(sys.argv[1]); salt = resource_salt(sys.argv[2])
play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
base = (c.u(0x484) + c.u(0x470)) & 0xffffffff; ok = bad = shared = 0; end = 0
for page in c.block(play + 24, 88):
    if c.unpack('h', page + 4)[0] != -1: shared += 1; continue
    block, comp, size, crc = c.unpack('4I', page + 8)
    if not size: continue
    raw = c.data[base + block:base + block + comp]; end = max(end, block + comp)
    try:
        data = zlib.decompress(raw, -15) if c.data[page + 3] == 0 else raw
        good = len(data) == size and (not crc or zlib.crc32(data) ^ 0xffffffff == crc)
        h = b''.join(hashlib.sha1(salt + bytes(x)).digest() for x in (data, data[:1024], data[-1024:]))
        good = good and h == c.data[page + 24:page + 84]
    except Exception:
        good = False
    ok += good; bad += not good
print(Path(sys.argv[1]).name, 'local pages ok', ok, 'bad', bad, 'shared-file pages', shared, 'raw section bytes', c.u(0x488), 'last used byte', end, 'file bytes', len(c.data), 'header size field', c.u(8))
c.close()
