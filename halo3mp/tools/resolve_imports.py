"""Resolve guest DLL -> guest DLL import thunks to real export addresses.

Format per ReXGlue src/system/xex_module.cpp:
  - security_info + 0x160 : export_table virtual address
  - xex2_export_table (BE): imagebaseaddr@0x20, count@0x24, base@0x28, ordOffset[]@0x2C
      addr = ordOffset[ordinal - base] + (imagebaseaddr << 16)
  - import records: value at record address; ordinal = value & 0xFFFF, type = value >> 24
      type 0 = variable/ordinal record, type 1 = thunk record; paired by ordinal.
"""
import struct, os, sys
import xexlib

G = r"C:\Programming\GitHub\Halo-3-MP\work\gamedata"


def load(path):
    x = xexlib.Xex(path)
    return x, x.image()


def export_map(path):
    x, img = load(path)
    et_va, = struct.unpack_from(">I", x.raw, x.sec_info_off + 0x160)
    if not et_va:
        return x, {}, "no export_table in security info"
    off = et_va - x.image_base
    if off < 0 or off + 0x2C > len(img):
        return x, {}, "export_table VA 0x%08X -> off 0x%X out of image (len 0x%X)" % (
            et_va, off, len(img))
    magic = struct.unpack_from(">III", img, off)
    imagebaseaddr, = struct.unpack_from(">I", img, off + 0x20)
    count, = struct.unpack_from(">I", img, off + 0x24)
    base, = struct.unpack_from(">I", img, off + 0x28)
    out = {}
    for i in range(count):
        o = off + 0x2C + i * 4
        if o + 4 > len(img):
            break
        v, = struct.unpack_from(">I", img, o)
        if v:
            out[base + i] = v + (imagebaseaddr << 16)
    return x, out, "et_va=0x%08X magic=%s imagebase=0x%X count=%d base=%d" % (
        et_va, [hex(m) for m in magic], imagebaseaddr, count, base)


def import_pairs(path, want_lib):
    """Return {thunk_addr: ordinal} for the named import library."""
    x, img = load(path)
    d = x.raw
    off = x.hdrs.get(xexlib.HDR_IMPORT_LIBS)
    total_size, string_table_size, count = struct.unpack_from(">III", d, off)
    p = off + 12
    end = p + string_table_size
    names = [s.decode("ascii", "replace") for s in d[p:end].split(b"\x00") if s]
    p = end
    result = {}
    for li in range(count):
        lib_size, = struct.unpack_from(">I", d, p)
        name_index, = struct.unpack_from(">H", d, p + 0x24)
        nimports, = struct.unpack_from(">H", d, p + 0x26)
        name = names[name_index] if name_index < len(names) else "lib%d" % li
        if name.lower() == want_lib.lower():
            last_ordinal = None
            for i in range(nimports):
                rec, = struct.unpack_from(">I", d, p + 0x28 + i * 4)
                ro = rec - x.image_base
                if ro < 0 or ro + 4 > len(img):
                    continue
                val, = struct.unpack_from(">I", img, ro)
                typ = val >> 24
                ordinal = val & 0xFFFF
                if typ == 0:
                    last_ordinal = ordinal
                elif typ == 1:
                    result[rec] = ordinal
        p += lib_size
    return x, result


if __name__ == "__main__":
    xw, exp, msg = export_map(os.path.join(G, "WavesLibDLL.dll"))
    print("WavesLibDLL base=0x%08X" % xw.image_base)
    print("  %s" % msg)
    print("  exports resolved: %d" % len(exp))
    for k in sorted(exp)[:5]:
        print("     ord %3d -> 0x%08X" % (k, exp[k]))

    for name, p in [("l360", os.path.join(G, "waves", "L360.dll")),
                    ("q10", os.path.join(G, "waves", "Q10.dll"))]:
        xi, pairs = import_pairs(p, "WavesLibDLL.dll")
        hit = sum(1 for o in pairs.values() if o in exp)
        print("\n%s: %d thunks, %d resolve against WavesLibDLL exports" % (
            name, len(pairs), hit))
        for t in sorted(pairs)[:5]:
            o = pairs[t]
            print("   thunk 0x%08X -> ord %3d -> %s" % (
                t, o, ("0x%08X" % exp[o]) if o in exp else "UNRESOLVED"))
