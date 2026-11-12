"""Inspect private decoded Halo 4 PPC without executing the game."""
import argparse
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

BASE = 0x82000000
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument("address", type=lambda v: int(v, 0))
p.add_argument("--bytes", type=lambda v: int(v, 0), default=256)
p.add_argument("--callers", action="store_true")
p.add_argument("--game", choices=("h3", "h4"), default="h4")
p.add_argument("--words", action="store_true", help="Print original data words instead of decoding instructions")
a = p.parse_args()
image = "work/advanced-forge/guest-image.bin" if a.game == "h3" else "work/h4-forge-research/h4-image.bin"
b = (ROOT / image).read_bytes()
if a.callers:
    for off in range(0, len(b)-3, 4):
        w = struct.unpack_from(">I", b, off)[0]
        if w >> 26 != 18:
            continue
        displacement = w & 0x3fffffc
        if displacement & 0x2000000:
            displacement -= 0x4000000
        target = (displacement if w & 2 else BASE+off+displacement) & 0xffffffff
        if target == a.address:
            print(f"{BASE+off:08X} {'bl' if w & 1 else 'b'} {target:08X}")
else:
    off = a.address-BASE
    if not 0 <= off < len(b):
        p.error("address is outside the decoded image")
    if a.words:
        for pos in range(off, min(off+a.bytes,len(b))-3, 4):
            word = struct.unpack_from('>I',b,pos)[0]
            value = struct.unpack_from('>f',b,pos)[0]
            print(f"{BASE+pos:08X} {word:08X} {value:g}")
    else:
        md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
        for i in md.disasm(b[off:off+a.bytes], a.address):
            print(f"{i.address:08X} {i.mnemonic} {i.op_str}")
