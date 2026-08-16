import struct, os, sys

ISO = r"C:\Programming\GitHub\Halo-3-MP\Halo 3 - ODST (USA, Brazil) (En,Ja,Fr,De,Es,It,Pt,Zh,Ko) (Disc 2) (Multiplayer).iso"
BASE = 0xFD90000
SECTOR = 2048
OUT = r"C:\Programming\GitHub\Halo-3-MP\work\gamedata"

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

files = [e for e in entries if not e[1]]
dirs = [e for e in entries if e[1]]
total = sum(e[3] for e in files)
print("dirs=%d files=%d total=%.2f GiB" % (len(dirs), len(files), total / 1024**3))
sys.stdout.flush()

for p, d, s, sz in dirs:
    os.makedirs(os.path.join(OUT, p.lstrip("/").replace("/", os.sep)), exist_ok=True)
os.makedirs(OUT, exist_ok=True)

done = 0
CHUNK = 8 * 1024 * 1024
for i, (p, d, s, sz) in enumerate(sorted(files)):
    dest = os.path.join(OUT, p.lstrip("/").replace("/", os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) == sz:
        done += sz
        continue
    f.seek(BASE + s * SECTOR)
    remaining = sz
    with open(dest, "wb") as out:
        while remaining > 0:
            n = min(CHUNK, remaining)
            buf = f.read(n)
            if not buf:
                break
            out.write(buf)
            remaining -= len(buf)
    done += sz
    if i % 20 == 0 or sz > 50 * 1024**2:
        print("[%3d/%3d] %.1f%%  %s" % (i + 1, len(files), 100.0 * done / total, p))
        sys.stdout.flush()

print("EXTRACT_COMPLETE files=%d" % len(files))
