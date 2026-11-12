"""Read private retail H4 Forge string IDs without extracting or modifying assets."""
import struct
from pathlib import Path
from Crypto.Cipher import AES

ROOT = Path(__file__).resolve().parents[2]
data = (ROOT/'work/h4-forge-research/disc2-assets/ca_forge_ravine.map').read_bytes()
def u(offset):
    return struct.unpack_from('>I', data, offset)[0]
key = bytes(v ^ 0xa5 for v in b'ILikeSafeStrings').ljust(16, b'\0')
iv = bytes(v ^ 0x3c for v in key)
offset = (u(0x164) + u(0x47c)) & 0xffffffff
size = u(0x15c)
strings = AES.new(key, AES.MODE_CBC, iv).decrypt(data[offset:offset + ((size+15)//16)*16])[:size]
indices = (u(0x160) + u(0x47c)) & 0xffffffff
for index in range(u(0x158)):
    start = u(indices + index*4)
    if start == 0xffffffff:
        continue
    name = strings[start:strings.index(b'\0', start)].decode('utf8')
    if ('forge' in name or 'sandbox' in name) and any(v in name for v in ('physic', 'precis', 'coord', 'position', 'rotat', 'snap', 'magnet', 'movement')):
        # Retail menu strings verified by the existing magnet callbacks use
        # namespace 1 with table start 0x631. Print candidate IDs for tracing.
        print(f'{index:5d} candidate=0x{0x80000+index-0x631:08X} {name}')
