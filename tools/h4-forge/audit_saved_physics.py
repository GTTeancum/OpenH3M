"""Read current Gulch/Cove object definitions; never modify map or save data."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/warlock-conversion/snapshot/tools"))
from cache_reader import Cache


def audit(path, bindings):
    cache = Cache(path)
    try:
        names = {int(row["datum"], 16): row["label"] for row in bindings
                 if row["map"] == path.name}
        scenario = next(tag["offset"] for tag in cache.tags.values()
                        if tag["group"] == "scnr")
        counts, objects = Counter(), []
        for row in cache.block(scenario + 0x20c, 48):
            datum = cache.u(row + 12)
            obj = cache.tags.get(datum & 65535)
            if not obj or obj["salt"] != datum >> 16:
                raise ValueError(f"Invalid palette datum: {datum:08x}")
            if obj["group"] not in ("bloc", "scen"):
                continue

            def tag(reference, group):
                result = cache.tags[reference & 65535]
                if result["salt"] != reference >> 16 or result["group"] != group:
                    raise ValueError(f"Invalid {group} reference: {reference:08x}")
                return result["offset"]

            model = tag(cache.u(obj["offset"] + 0x40), "hlmt")
            physics = cache.u(model + 0x3c)
            motions = [] if physics == 0xffffffff else [
                cache.unpack("H", body + 0x1a)[0]
                for body in cache.block(tag(physics, "phmo") + 0x58, 176)
            ]
            fixed = bool(motions) and all(value == 5 for value in motions)
            counts["fixed" if fixed else "other"] += 1
            if datum in names:
                objects.append(dict(datum=f"{datum:08x}", label=names[datum],
                                    motion_types=sorted(set(motions)), fixed=fixed))
        return dict(map=path.name, map_id=cache.u(scenario + 8),
                    sha256=hashlib.sha256(cache.data).hexdigest(),
                    scenery_palette=dict(counts), magnet_objects=objects,
                    magnet_count=len(objects),
                    magnet_fixed=sum(obj["fixed"] for obj in objects),
                    limitation="Definition audit; not a console or dynamic-behavior test")
    finally:
        cache.close()


if __name__ == "__main__":
    output = ROOT / "work/h4-forge-research/isolated/saved-physics-audit.json"
    bindings = json.loads(output.with_name("marker-bindings.json").read_text())
    maps = sorted((ROOT / "work/dlc/installed-current/0000000000000000").rglob("forge_*.map"))
    if not maps:
        raise ValueError("Current Gulch/Cove map inputs are missing")
    results = [audit(path, bindings) for path in maps]
    output.write_text(json.dumps(results, indent=2) + "\n")
    for result in results:
        print(f"{result['map']}: {result['magnet_fixed']}/{result['magnet_count']} magnet objects authored Fixed")
        for obj in result["magnet_objects"]:
            if not obj["fixed"]:
                print(f"  Exception: {obj['label']}, motion types {obj['motion_types']}")
