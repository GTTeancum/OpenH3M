"""Compare native H3 object poses/properties across an editor-free reload."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("edited_run", type=Path)
parser.add_argument("reload_run", type=Path)
args = parser.parse_args()


def confined(path):
    path = path.resolve(strict=True)
    path.relative_to(ROOT)
    return path


def records(run):
    data = (run / "native-variant.bin").read_bytes()
    if len(data) != 0xe090 or struct.unpack_from('>H', data, 0xf8)[0] != 12:
        raise ValueError("Not an ordinary native H3 version-12 variant")
    result = []
    for slot in range(640):
        at = 0x130 + slot*0x54
        if not struct.unpack_from('>H', data, at)[0] & 1:
            continue
        # Ignore transient handles/slot flags, preserve identity, nine pose
        # components and all serialized object properties byte-for-byte.
        quota = struct.unpack_from('>i', data, at+12)[0]
        if quota < -1 or quota >= 256:
            raise ValueError("Invalid native object quota")
        tag = data[0xd34c+quota*12:0xd350+quota*12].hex() if quota >= 0 else None
        result.append((data[at+12:at+16].hex(), tag, data[at+16:at+52].hex(),
                       data[at+0x3c:at+0x54].hex()))
    if not result:
        raise ValueError("No occupied native placements")
    return Counter(result)


edited, reloaded = confined(args.edited_run), confined(args.reload_run)
command = json.loads((reloaded / "launch-command.json").read_text())
if any('halo3mp_advanced_forge' in arg for arg in command):
    raise ValueError("Reload must supply no Advanced Forge data or options")
log = (reloaded / "trace-runtime.log").read_text(errors='replace')
if any(marker in log for marker in ('Advanced Forge bound held piece',
                                    'Advanced Forge native editor rows',
                                    'Advanced Forge physics selected')):
    raise ValueError("Editor behavior was active during the reload")
before, after = records(edited), records(reloaded)
if before != after:
    raise ValueError(f"Reload changed native placements: missing {before-after}, added {after-before}")
report = dict(result='PASS', edited_run=edited.name, reload_run=reloaded.name,
              native_version=12, unchanged_placements=sum(before.values()),
              advanced_forge_options=False,
              limitation='Host native reload and byte comparison; inspect the game mode/capture separately. Physical console/system-link untested.')
(reloaded / 'native-reload-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
