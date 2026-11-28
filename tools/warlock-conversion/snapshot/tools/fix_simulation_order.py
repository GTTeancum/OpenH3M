"""Put a finished native Halo 3 map's scenario Simulation Definition Table back into the game's search order.

The game finds an object definition in this table by binary search over the 32-bit tag handles compared as signed
numbers (tools/ho2h3/README.md, SimTable.cs: sub_82425660 -> sub_82105770 / sub_8234D568). If the table is out of
order the search misses, the item resolves to -1 and Forge creation crashes (Void, user report 2026-11-26).
compact_native.py renumbers tags but kept the old order, leaving Void, Reflection and Sword Base unsorted.
Only the table's entries are reordered (same handles, same count); body XOR and salted digests are refreshed.
Usage: fix_simulation_order.py <map> <output> [--xex default.xex]   (or import sort_simulation_table)
"""
import argparse
import struct
from pathlib import Path

from cache_reader import Cache
from cache_integrity import refresh_cache_hashes
from build_scenario_checkpoint import resource_salt

TABLE = 0x6A4   # scnr 'Simulation Definition Table' (retail plugin)


def signed(v):
    return v - (1 << 32) if v & 0x80000000 else v


def sort_simulation_table(data, cache):
    """Sort the table in place in `data` (a bytearray copy of the cache). Returns (entries, was_sorted)."""
    scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
    rows = cache.block(scenario + TABLE, 4)
    if not rows:
        return 0, True
    start = rows[0]
    if rows[-1] != start + 4 * (len(rows) - 1):
        raise ValueError('Simulation table is not contiguous')
    values = list(struct.unpack_from('>%dI' % len(rows), data, start))
    ordered = sorted(values, key=signed)
    if len(set(values)) != len(values):
        raise ValueError('Duplicate handles in simulation table')
    struct.pack_into('>%dI' % len(rows), data, start, *ordered)
    return len(rows), values == ordered


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--xex', type=Path, default=Path('C:/Programming/GitHub/OpenH3M/.local/xenia-canary/game-local/default.xex'))
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('output exists')
    salt = resource_salt(a.xex)
    cache = Cache(a.map)
    data = bytearray(cache.data)
    probe = bytearray(data); refresh_cache_hashes(probe, salt)
    if probe[0x2C4:0x2C8] != data[0x2C4:0x2C8] or probe[0x330:0x344] != data[0x330:0x344]:
        raise SystemExit('Input header digest does not reproduce with this xex salt; refusing to edit')
    del probe
    count, was_sorted = sort_simulation_table(data, cache)
    cache.close()
    refresh_cache_hashes(data, salt)
    a.output.write_bytes(data)
    print(f'{a.map.name}: {count} entries, {"already sorted" if was_sorted else "re-sorted"} -> {a.output}')


if __name__ == '__main__':
    main()
