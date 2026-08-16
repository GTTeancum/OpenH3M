import struct
from Crypto.Cipher import AES

RETAIL_KEY = bytes([0x20,0xB1,0x85,0xA5,0x9D,0x28,0xFD,0xC3,0x40,0x58,0x3F,0xBB,0x08,0x96,0xBF,0x91])
DEVKIT_KEY = bytes(16)

HDR_FILE_FORMAT   = 0x000003FF
HDR_IMPORT_LIBS   = 0x000103FF
HDR_IMAGE_BASE    = 0x00010201
HDR_ENTRY_POINT   = 0x00010100


class Xex:
    def __init__(self, path):
        self.path = path
        self.raw = open(path, "rb").read()
        d = self.raw
        (self.magic, self.module_flags, self.pe_off, self.reserved,
         self.sec_info_off, self.hdr_count) = struct.unpack_from(">4sIIIII", d, 0)
        assert self.magic == b"XEX2", self.magic
        self.hdrs = {}
        off = 0x18
        for _ in range(self.hdr_count):
            k, v = struct.unpack_from(">II", d, off)
            off += 8
            self.hdrs[k] = v
        self.image_base = self.hdrs.get(HDR_IMAGE_BASE, 0)
        self.entry = self.hdrs.get(HDR_ENTRY_POINT, 0)
        ff = self.hdrs[HDR_FILE_FORMAT]
        self.ff_size, self.encryption, self.compression = struct.unpack_from(">IHH", d, ff)
        self.ff_off = ff
        self.file_key = d[self.sec_info_off + 0x150 : self.sec_info_off + 0x150 + 16]

    def session_key(self, key=RETAIL_KEY):
        return AES.new(key, AES.MODE_ECB).decrypt(self.file_key)

    def image(self, key=RETAIL_KEY):
        d = self.raw
        blob = d[self.pe_off:]
        if self.compression == 1:  # BASIC
            nblocks = (self.ff_size - 8) // 8
            blocks = []
            for i in range(nblocks):
                ds, zs = struct.unpack_from(">II", d, self.ff_off + 8 + i * 8)
                blocks.append((ds, zs))
        elif self.compression == 0:
            blocks = [(len(blob), 0)]
        else:
            raise NotImplementedError("compression %d" % self.compression)

        if self.encryption == 1:
            cipher = AES.new(self.session_key(key), AES.MODE_CBC, iv=bytes(16))
        else:
            cipher = None

        out = bytearray()
        pos = 0
        for ds, zs in blocks:
            chunk = blob[pos:pos + ds]
            pos += ds
            if cipher is not None:
                pad = (-len(chunk)) % 16
                if pad:
                    chunk = chunk + bytes(pad)
                chunk = cipher.decrypt(chunk)[:ds]
            out += chunk
            out += bytes(zs)
        return bytes(out)


def pe_exports(img, image_base):
    """Return {ordinal: virtual_address} from the PE export directory."""
    if img[:2] != b"MZ":
        return {}, "no MZ"
    e_lfanew = struct.unpack_from("<I", img, 0x3C)[0]
    if img[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        return {}, "no PE"
    coff = e_lfanew + 4
    nsec, = struct.unpack_from("<H", img, coff + 2)
    opt_size, = struct.unpack_from("<H", img, coff + 16)
    opt = coff + 20
    magic, = struct.unpack_from("<H", img, opt)
    dd = opt + (96 if magic == 0x10B else 112)
    exp_rva, exp_size = struct.unpack_from("<II", img, dd)
    if not exp_rva:
        return {}, "no export dir"
    base_ord, = struct.unpack_from("<I", img, exp_rva + 16)
    nfunc, = struct.unpack_from("<I", img, exp_rva + 20)
    addr_rva, = struct.unpack_from("<I", img, exp_rva + 28)
    out = {}
    for i in range(nfunc):
        f, = struct.unpack_from("<I", img, addr_rva + i * 4)
        if f:
            out[base_ord + i] = image_base + f
    return out, "ok base_ord=%d n=%d" % (base_ord, nfunc)


def imports(xex):
    """Return {libname: [(ordinal, thunk_addr), ...]}"""
    d = xex.raw
    off = xex.hdrs.get(HDR_IMPORT_LIBS)
    if not off:
        return {}
    total_size, string_table_size, count = struct.unpack_from(">III", d, off)
    p = off + 12
    names = []
    end = p + string_table_size
    blob = d[p:end]
    for s in blob.split(b"\0"):
        if s:
            names.append(s.decode("ascii", "replace"))
    p = end
    result = {}
    for li in range(count):
        # library descriptor
        (lib_size,) = struct.unpack_from(">I", d, p)
        nimports, = struct.unpack_from(">H", d, p + 0x24)
        recs = []
        rp = p + 0x28
        for i in range(nimports):
            addr, = struct.unpack_from(">I", d, rp + i * 4)
            recs.append(addr)
        name = names[li] if li < len(names) else "lib%d" % li
        result[name] = recs
        p += lib_size
    return result
