import struct, os

ISO = r"C:\Programming\GitHub\Halo-3-MP\Halo 3 - ODST (USA, Brazil) (En,Ja,Fr,De,Es,It,Pt,Zh,Ko) (Disc 2) (Multiplayer).iso"
BASE = 0xFD90000
SECTOR = 2048
OUT = r"C:\Programming\GitHub\Halo-3-MP\work\extracted"

f = open(ISO, "rb")


def read_at(off, n):
    f.seek(off)
    return f.read(n)


vd = read_at(BASE + 32 * SECTOR, 0x30)
root_sector, root_size = struct.unpack_from("<II", vd, 0x14)

entries = []


def walk(sector, size, path):
    data = read_at(BASE + sector * SECTOR, size)

    def node(off):
        o = off * 4
        if o + 14 > len(data):
            return
        left, right, start, fsize = struct.unpack_from("<HHII", data, o)
        attr = data[o + 12]
        nlen = data[o + 13]
        name = data[o + 14 : o + 14 + nlen].decode("utf-8", "replace")
        if left == 0xFFFF:
            return
        if left:
            node(left)
        full = path + "/" + name
        isdir = bool(attr & 0x10)
        entries.append((full, isdir, start, fsize))
        if isdir and fsize:
            walk(start, fsize, full)
        if right:
            node(right)

    node(0)


walk(root_sector, root_size, "")

WANT = ["/WaveShell-Xbox.dll", "/WavesLibDLL.dll"]
os.makedirs(OUT, exist_ok=True)
for p, d, s, sz in entries:
    if p in WANT:
        dest = os.path.join(OUT, p.lstrip("/"))
        f.seek(BASE + s * SECTOR)
        data = f.read(sz)
        open(dest, "wb").write(data)
        print("%-24s %9d bytes  magic=%r" % (os.path.basename(dest), sz, data[:4]))
