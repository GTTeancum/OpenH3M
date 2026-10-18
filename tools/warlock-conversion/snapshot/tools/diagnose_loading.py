"""Log original loader preflight failures without rebuilding or patching OpenH3M."""
import hashlib
import struct
from pathlib import Path
from xexlib import Xex

ROOT = Path(__file__).resolve().parents[2]
xex = Xex(str(ROOT / 'default.xex'))
image = xex.image()
limits = struct.unpack_from('>II', image, 0x76B8A0)
resource_offset = xex.hdrs[0x2FF]
resource_length = struct.unpack_from('>I', xex.raw, resource_offset)[0]
for p in range(resource_offset + 4, resource_offset + resource_length, 16):
    if xex.raw[p:p + 8].rstrip(b'\0') == b'00':
        address = struct.unpack_from('>I', xex.raw, p + 8)[0]
        salt = image[address - xex.image_base:address - xex.image_base + 0x22]
        break

lines = ['DATA-SIDE PREFLIGHT; not runtime event tracing or proof of loading.',
         'Source: original default.xex sub_821B0DD0, sub_821B1020, sub_82206440.']
for path in (ROOT / 'maps/lockout.map',
             Path('D:/Programming/GitHub/H3M/game/maps/lockout.map'),
             ROOT / '.local/candidate/lockout.map'):
    with path.open('rb') as f:
        header = bytearray(f.read(0x3000))
    u = lambda o: struct.unpack_from('>I', header, o)[0]
    base, size = u(0x2E8), u(0x18)
    lines.append(str(path))
    ok = size <= limits[1] - limits[0] and (size == 0 or base + size == limits[1])
    lines.append(f"  {'PASS' if ok else 'FAIL'} TAG_MEMORY: {base:#010x}+{size:#x}={base + size:#010x}; required end={limits[1]:#010x}")
    stored = bytes(header[0x330:0x344])
    for start, length in [(0x320, 4), (0x328, 8), (0x330, 0x13C), (0x1C, 0x100),
                          (0x144, 8), (0x16C, 0x20), (0x49C, 0x10)]:
        header[start:start + length] = bytes(length)
    actual = hashlib.sha1(salt + header).digest()
    lines.append(f"  {'PASS' if stored == actual else 'FAIL'} HEADER_HASH: stored={stored.hex()} computed={actual.hex()}")
lines.append('RSA authentication and downstream resource/gameplay checks are not certified by this preflight.')
output = '\n'.join(lines) + '\n'
(ROOT / '.local/reports/loading-failures.log').write_text(output, encoding='utf-8')
print(output)
