"""Version-checked Mythic custom-content validation patch for OpenH3M/RGH testing.

Produces a separate private XEX; never modifies the source. RGH/JTAG is required
on console. No signing, gameplay, or network compatibility claim is made.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from Crypto.Cipher import AES

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'halo3mp/tools'))
from xexlib import Xex

SOURCE_SHA256 = '18816c1da58b1371e440741fadab1df8e6e6ecca7c5b81952f2d23ceec797313'
PATCHES = (
    (0x821F6A68, '481cd201', '38600001', 'mapinfo signature call'),
    (0x821B111C, '4bffe025', '38600001', 'cache header RSA call; salted hash check retained'),
)


def patch(source, output):
    output = output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('Output must be a new repository-local path')
    x = Xex(source)
    if hashlib.sha256(x.raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported XEX version; refusing guessed patch offsets')
    if (x.image_base, x.encryption, x.compression) != (0x82000000, 1, 1):
        raise ValueError('Unexpected source layout')
    original = x.image()
    image = bytearray(original)
    changed = []
    for address, before, after, purpose in PATCHES:
        offset = address - x.image_base
        if image[offset:offset + 4] != bytes.fromhex(before):
            raise ValueError(f'Call-site bytes do not match at {address:#x}')
        image[offset:offset + 4] = bytes.fromhex(after)
        changed.append(dict(address=hex(address), before=before, after=after, purpose=purpose))
    # Repack the original BASIC layout, preserving all zero-fill regions.
    packed = bytearray()
    position = 0
    for block in range((x.ff_size - 8) // 8):
        data_size, zero_size = struct.unpack_from('>II', x.raw, x.ff_off + 8 + block * 8)
        packed += image[position:position + data_size]
        position += data_size
        if any(image[position:position + zero_size]):
            raise ValueError('Patch would modify a zero-fill region')
        position += zero_size
    if position != len(image) or len(packed) % 16:
        raise ValueError('Unexpected image coverage or AES alignment')
    encrypted = AES.new(x.session_key(), AES.MODE_CBC, iv=bytes(16)).encrypt(packed)
    if len(encrypted) != len(x.raw) - x.pe_off:
        raise ValueError('Unexpected source trailing data')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(x.raw[:x.pe_off] + encrypted)
    roundtrip = Xex(output).image()
    restored = bytearray(roundtrip)
    for address, before, _, _ in PATCHES:
        offset = address - x.image_base
        restored[offset:offset+4] = bytes.fromhex(before)
    if roundtrip != image or restored != original:
        raise ValueError('Patch roundtrip or scope verification failed')
    return dict(source_sha256=SOURCE_SHA256,
                output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                patches=changed,
                scope='Content signature call sites only; structural and salted-hash checks retained',
                console_status='RGH/JTAG candidate; hardware execution untested')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(patch(args.source, args.output), indent=2))
