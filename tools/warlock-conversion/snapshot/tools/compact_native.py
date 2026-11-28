"""Compact a finished native Halo 3 map: remove tags unreachable from the cache's root tags and repack the
remaining local resource pages (the warlock pipeline's own compact_basis step, run on its own).

For maps built inside a full copy of a stock map (tools/ho2h3): the stock map's own tags and pages stay in the file
although the new scenario never reaches them (Reflection carried ~49 MB of Guardian's). Original files are never
edited; the output is a new file, checked against the original Xbox 360 budget.
Usage: compact_native.py <map> <output> [--xex default.xex] [--report out.json]
"""
import argparse, hashlib, json, sys
from pathlib import Path
from types import SimpleNamespace
from map_builder import MapBuilder
from cache_registry import CacheRegistry
from build_scenario_checkpoint import resource_salt
from retired_resources import compact_basis
from cache_reader import Cache
from console_cache_limits import inspect_native_budget


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--xex', type=Path, default=Path('C:/Programming/GitHub/OpenH3M/.local/xenia-canary/game-local/default.xex'))
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('output exists')
    salt = resource_salt(a.xex)
    builder = MapBuilder(str(a.map))
    registry = CacheRegistry(builder, salt)
    importer = SimpleNamespace(registry=registry, builder=builder,
                               reference=Path(__file__).resolve().parents[1] / 'reference')
    report = compact_basis(importer)

    def keep_simulation_order():
        # The finished map's simulation table is already in the game's search order (ho2h3 SimTable.cs: signed
        # handle order, sub_8234D568); only entries of removed tags are dropped, the order is kept. Nothing new is added.
        import struct, xml.etree.ElementTree as ET
        schema = ET.parse(importer.reference / 'plugins/scnr.xml').getroot()
        field = next(x for x in schema if x.get('name') == 'Simulation Definition Table')
        scenario = next(t['offset'] for t in registry.cache.tags.values() if t['group'] == 'scnr')
        at = scenario + int(field.get('offset'), 0)
        original = registry.table(at, 4)
        payload = b''.join(original[j:j + 4] for j in range(0, len(original), 4)
                           if struct.unpack_from('>H', registry.tags, (struct.unpack_from('>I', original, j)[0] & 65535) * 8)[0] != 65535)
        registry.simulation_added = []
        if payload != bytes(original):
            builder.put(registry.address(at), 'III', len(payload) // 4, builder.alloc(payload), 0)
        report['simulation_entries'] = (len(original) // 4, len(payload) // 4)
    registry.stage_simulation_definitions = keep_simulation_order
    registry.finalize(0)
    payload = builder.finish(salt)
    builder.close()
    # Compaction renumbers tags, so the kept table order no longer matches the new handles; the game's binary search
    # then misses and Forge items resolve to -1 (Void crash, 2026-11-26). Re-sort by the final handles.
    from fix_simulation_order import sort_simulation_table
    from cache_integrity import refresh_cache_hashes
    a.output.write_bytes(payload)
    check = Cache(str(a.output)); data = bytearray(check.data)
    sim_count, sim_was_sorted = sort_simulation_table(data, check); check.close()
    refresh_cache_hashes(data, salt); payload = bytes(data)
    a.output.write_bytes(payload)
    report['simulation_table_resorted'] = not sim_was_sorted
    check = Cache(str(a.output))
    try:
        budget = inspect_native_budget(check, a.output)
    finally:
        check.close()
    summary = dict(source=str(a.map), output=str(a.output), source_bytes=a.map.stat().st_size, output_bytes=len(payload),
                   sha256=hashlib.sha256(payload).hexdigest(), retired_tags=report['retired_tags'],
                   retired_resources=report['retired_resources'], retired_pages=report['retired_pages'],
                   bytes_saved=report['bytes_saved'], budget=budget)
    if a.report:
        a.report.write_text(json.dumps(dict(summary, retired_names=report['retired_names']), indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != 'budget'}))
    print('within 360 cache limit:', budget['file']['within_limit'])


main()
