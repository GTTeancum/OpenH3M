"""Find the longjmp counterpart of the setjmp at 0x825B8320.

setjmp saves with:  std r14,152(r5) ... std r31,288(r5)
longjmp restores:   ld  r14,152(rX) ... ld  r31,288(rX)

`ld rD,off(rA)` encodes as 0xE8000000 | D<<21 | A<<16 | (off & 0xFFFC) | 0
(DS-form, low 2 bits are the sub-opcode 0 for ld).
"""
import struct, os
import xexlib

G = r"C:\Programming\GitHub\Halo-3-MP\work\gamedata"
x = xexlib.Xex(os.path.join(G, "default.xex"))
img = x.image()
BASE = x.image_base


def ld(d, a, off):
    return 0xE8000000 | (d << 21) | (a << 16) | (off & 0xFFFC)


# scan for `ld r14,152(rA)` followed shortly by `ld r15,160(rA)`
hits = []
for a in range(0, 32):
    pat14 = struct.pack(">I", ld(14, a, 152))
    pat15 = struct.pack(">I", ld(15, a, 160))
    start = 0
    while True:
        i = img.find(pat14, start)
        if i < 0:
            break
        start = i + 4
        if i % 4:
            continue
        # r15 restore should follow within a few instructions
        window = img[i:i + 64]
        if pat15 in window:
            hits.append((BASE + i, a))

print("candidate longjmp restore sequences:")
seen = set()
for addr, a in hits:
    if addr in seen:
        continue
    seen.add(addr)
    print("  at 0x%08X  base=r%d" % (addr, a))

# Also locate the enclosing function start by walking back to a flow terminator.
def prev_terminator(addr, limit=0x400):
    off = addr - BASE
    for back in range(4, limit, 4):
        w, = struct.unpack_from(">I", img, off - back)
        op = w >> 26
        term = False
        if op == 18 and (w & 1) == 0:
            term = True
        elif op == 19:
            xo = (w >> 1) & 0x3FF
            if xo in (16, 528) and (w & 1) == 0:
                term = True
        if term:
            return addr - back + 4
    return None


print()
for addr, a in sorted(seen and [(h, b) for h, b in hits if h in seen]):
    s = prev_terminator(addr)
    if s:
        print("  restore 0x%08X -> enclosing function starts 0x%08X" % (addr, s))
    seen.discard(addr)
