import struct, os, sys
import xexlib

G = r"C:\Programming\GitHub\Halo-3-MP\work\gamedata"


def sections(img):
    e = struct.unpack_from("<I", img, 0x3C)[0]
    coff = e + 4
    nsec, = struct.unpack_from("<H", img, coff + 2)
    opt_size, = struct.unpack_from("<H", img, coff + 16)
    opt = coff + 20
    sh = opt + opt_size
    secs = []
    for i in range(nsec):
        o = sh + i * 40
        name = img[o:o + 8].split(b"\x00")[0].decode("ascii", "replace")
        vs, va, rs, pr = struct.unpack_from("<IIII", img, o + 8)
        secs.append((name, va, vs, rs, pr))
    return secs, opt


def rva2off(secs, rva):
    for name, va, vs, rs, pr in secs:
        if va <= rva < va + max(vs, rs):
            return pr + (rva - va)
    return None


def xex_exports(path):
    """Xbox 360 XEX export table (big-endian), located at the .edata RVA."""
    x = xexlib.Xex(path)
    img = x.image()
    secs, opt = sections(img)
    dd = opt + 96
    exp_rva, exp_size = struct.unpack_from("<II", img, dd)
    off = rva2off(secs, exp_rva)
    if off is None:
        return x, {}, "export rva 0x%X unmapped" % exp_rva
    # XEX_EXPORT_TABLE, big-endian
    magic = struct.unpack_from(">III", img, off)
    imagebase, = struct.unpack_from(">I", img, off + 0x28)
    count, = struct.unpack_from(">I", img, off + 0x2C)
    base, = struct.unpack_from(">I", img, off + 0x30)
    out = {}
    for i in range(count):
        v, = struct.unpack_from(">I", img, off + 0x34 + i * 4)
        if v:
            out[base + i] = (imagebase << 16) + v
    return x, out, "magic=%s imagebase=0x%X count=%d base=%d" % (
        [hex(m) for m in magic], imagebase, count, base)


def xex_imports(path):
    """{libname: [thunk_addr,...]} - count lives at +0x26, name_index at +0x24."""
    x = xexlib.Xex(path)
    d = x.raw
    off = x.hdrs.get(xexlib.HDR_IMPORT_LIBS)
    if not off:
        return x, {}
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
        recs = []
        for i in range(nimports):
            a, = struct.unpack_from(">I", d, p + 0x28 + i * 4)
            recs.append(a)
        name = names[name_index] if name_index < len(names) else "lib%d" % li
        result[name] = recs
        p += lib_size
    return x, result


if __name__ == "__main__":
    x, exp, msg = xex_exports(os.path.join(G, "WavesLibDLL.dll"))
    print("WavesLibDLL base=0x%08X  %s" % (x.image_base, msg))
    print("export count:", len(exp))
    for k in sorted(exp)[:6]:
        print("   ord %3d -> 0x%08X" % (k, exp[k]))

    for name, p in [("l360", os.path.join(G, "waves", "L360.dll")),
                    ("q10", os.path.join(G, "waves", "Q10.dll"))]:
        xi, imps = xex_imports(p)
        print("\n%s base=0x%08X" % (name, xi.image_base))
        for lib, recs in imps.items():
            print("   %-20s %d records  first=%s" % (
                lib, len(recs), ["0x%08X" % r for r in recs[:3]]))
