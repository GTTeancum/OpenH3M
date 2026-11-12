"""Inspect stock native Forge UI data; read-only map access."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/warlock-conversion/snapshot/tools"))
from cache_reader import Cache
from string_ids import StringTable

path = next((ROOT / "work/dlc/installed-current").rglob("forge_gulch.map"))
cache = Cache(path)
strings = StringTable(cache)
try:
    for index, tag in cache.tags.items():
        if tag["group"] != "dsrc" or strings.text(cache.u(tag["offset"])) != "object_properties_datasource":
            continue
        print(f"dsrc {index:x} name {strings.text(cache.u(tag['offset']))}")
        for i, row in enumerate(cache.block(tag["offset"] + 0x10, 0x28)):
            print(f"  row {i} submenu {strings.text(cache.u(row+0x24))}")
            for entry in cache.block(row, 8):
                print("    integer", strings.text(cache.u(entry)), cache.u(entry+4))
            for entry in cache.block(row+12, 0x24):
                print("    text", strings.text(cache.u(entry)), bytes(cache.data[entry+4:entry+36]))
            for entry in cache.block(row+24, 8):
                print("    sid", strings.text(cache.u(entry)), strings.text(cache.u(entry+4)), hex(cache.u(entry+4)))
finally:
    cache.close()
