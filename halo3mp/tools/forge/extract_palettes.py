"""Read the Forge scenery palette (piece name -> object definition) of the
Advanced Forge maps from their installed LIVE packages, for binding the code
magnet tables to the pieces actually in each map.

Usage: python extract_palettes.py <content dir 00000002> <work dir inside repo> <out palettes.json>
The repository reader tools/warlock-conversion/snapshot/tools is used read-only.
"""
import json
import sys
from pathlib import Path

REPO = Path('C:/Programming/GitHub/OpenH3M')
sys.path.insert(0, str(REPO / 'tools/warlock-conversion/snapshot/tools'))
from verify_dlc_stfs import read_directory, data_block  # noqa: E402
from cache_reader import Cache  # noqa: E402
from string_ids import StringTable  # noqa: E402

MAPS = {1730: ('ForgeGulch', 'forge_gulch.map'), 1731: ('ForceCove', 'forge_cove.map')}
PALETTES = {0x20c: 'scenery', 0x218: 'teleporters'}   # Halo 3 scenario sandbox blocks
content, work, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
work.mkdir(parents=True, exist_ok=True)
result = {}
for map_id, (prefix, name) in MAPS.items():
    packages = sorted(p for p in content.iterdir() if p.name.startswith(prefix + '_'))
    if not packages:
        print('no package for', prefix)
        continue
    package = packages[-1]
    target = work / name
    with package.open('rb') as st, target.open('wb') as w:
        cb, cd, _ = read_directory(st)
        for off in range(0, len(cd), 64):
            row = cd[off:off + 64]
            if row[:40].split(b'\0')[0] != name.encode():
                continue
            first = int.from_bytes(row[47:50], 'little')
            size = int.from_bytes(row[52:56], 'big')
            for k in range((size + 4095) // 4096):
                st.seek(cb + data_block(first + k) * 4096)
                w.write(st.read(4096)[:min(4096, size - k * 4096)])
    c = Cache(target)
    strings = StringTable(c)
    scnr = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    entries = {}
    for block in PALETTES:
        n, p = c.unpack('II', scnr + block)
        at = c.pointer(p) if n else 0
        for k in range(n):
            e = at + k * 0x30
            entries[strings.text(c.u(e + 16))] = c.u(e + 12)
    c.data.close()
    c.file.close()
    target.unlink()
    result[str(map_id)] = {'package': package.name, 'pieces': entries}
    print(map_id, package.name, len(entries), 'palette entries')
out.write_text(json.dumps(result, indent=1, sort_keys=True))
