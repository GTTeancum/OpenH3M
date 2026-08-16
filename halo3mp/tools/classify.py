"""Classify each declared function boundary as a genuine entry or a mid-function
tail-branch target.

A genuine entry is preceded by a flow terminator (blr / b / bctr / bctrl-less
unconditional branch). Anything else means the previous instruction falls
through into it, so declaring it as a separate function splits a real function
and breaks shared register state -- those need share_registers = true.
"""
import struct, os
import xexlib

G = r"C:\Programming\GitHub\Halo-3-MP\work\gamedata"

MODULES = {
    "entrypoint": ("default.xex", 0x82000000),
    "waveshell-xbox": ("WaveShell-Xbox.dll", 0x88000000),
    "waveslibdll": ("WavesLibDLL.dll", 0x8A000000),
}

ADDRS = [
    (0x822C0AA8, "entrypoint"), (0x821BEFC0, "entrypoint"), (0x82511008, "entrypoint"),
    (0x826DACD8, "entrypoint"), (0x8230D988, "entrypoint"), (0x826DA390, "entrypoint"),
    (0x825B8320, "entrypoint"), (0x826DEA78, "entrypoint"),
    (0x88055560, "waveshell-xbox"), (0x88057C60, "waveshell-xbox"), (0x88065DB8, "waveshell-xbox"),
    (0x8A087178, "waveslibdll"), (0x8A078060, "waveslibdll"), (0x8A076E18, "waveslibdll"),
]

_img = {}


def img_for(mod):
    if mod not in _img:
        fn, base = MODULES[mod]
        p = os.path.join(G, fn)
        x = xexlib.Xex(p)
        _img[mod] = (x, x.image())
    return _img[mod]


def insn(mod, addr):
    x, im = img_for(mod)
    o = addr - x.image_base
    if o < 0 or o + 4 > len(im):
        return None
    return struct.unpack_from(">I", im, o)[0]


def is_terminator(w):
    if w is None:
        return False, "oob"
    op = w >> 26
    if op == 18:  # b / ba / bl / bla
        lk = w & 1
        return (lk == 0), ("b" if not lk else "bl")
    if op == 19:
        xo = (w >> 1) & 0x3FF
        if xo == 16:  # bclr
            return (w & 1) == 0, "blr"
        if xo == 528:  # bcctr
            return (w & 1) == 0, "bctr"
    return False, "op%d" % op


print("%-12s %-10s  %-10s %s" % ("addr", "module", "prev", "verdict"))
for a, mod in ADDRS:
    prev = insn(mod, a - 4)
    term, kind = is_terminator(prev)
    verdict = "ENTRY" if term else "MID-FUNCTION (needs share_registers)"
    print("0x%08X  %-14s %-8s  %s" % (a, mod, kind, verdict))
