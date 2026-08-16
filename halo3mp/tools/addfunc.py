"""Add a faulting guest address to the correct module's [*.functions] table.

Module image ranges are taken from the runtime log lines:
  Function table initialized for module: code=..., image=<base>-<end>
"""
import sys, re, os

MANIFEST = r"C:\Programming\GitHub\Halo-3-MP\halo3mp\halo3mp_manifest.toml"

# module key in manifest -> (image_base, image_end)
RANGES = [
    ("entrypoint",      0x82000000, 0x83320000),
    ("waveshell-xbox",  0x88000000, 0x880A0000),
    ("l360",            0x89400000, 0x89470000),
    ("waveslibdll",     0x8A000000, 0x8A0C0000),
    ("q10",             0x8B900000, 0x8B970000),
]

# manifest module ordering for [[modules]] entries (must match file order)
MODULE_ORDER = ["waveshell-xbox", "waveslibdll", "l360", "q10"]


def owner(addr):
    for name, lo, hi in RANGES:
        if lo <= addr < hi:
            return name
    return None


def add(addr):
    name = owner(addr)
    if name is None:
        return "unmapped"
    sym = "sub_%08X" % addr
    line = "0x%08X = { name = \"%s\" }" % (addr, sym)
    t = open(MANIFEST, encoding="utf-8").read()
    if "0x%08X = {" % addr in t:
        return "already"

    if name == "entrypoint":
        hdr = "[entrypoint.functions]"
        if hdr in t:
            t = t.replace(hdr, hdr + "\n" + line, 1)
        else:
            anchor = 'out_directory_path = "generated/default"\nincludes = []\n'
            t = t.replace(anchor, anchor + "\n" + hdr + "\n" + line + "\n", 1)
    else:
        idx = MODULE_ORDER.index(name)
        hdr = "[modules.functions]  # %s" % name
        if hdr in t:
            t = t.replace(hdr, hdr + "\n" + line, 1)
        else:
            # insert right after that module's block
            blocks = t.split("[[modules]]")
            # blocks[0] is preamble; module i is blocks[i+1]
            b = blocks[idx + 1]
            b = b.rstrip("\n") + "\n\n" + hdr + "\n" + line + "\n\n"
            blocks[idx + 1] = b
            t = "[[modules]]".join(blocks)

    open(MANIFEST, "w", encoding="utf-8").write(t)
    return "added:%s->%s" % (sym, name)


if __name__ == "__main__":
    a = int(sys.argv[1], 16)
    print(add(a))
