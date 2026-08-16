import struct, os, sys

ISO = r"C:\Programming\GitHub\Halo-3-MP\Halo 3 - ODST (USA, Brazil) (En,Ja,Fr,De,Es,It,Pt,Zh,Ko) (Disc 2) (Multiplayer).iso"
BASE = 0xFD90000
SECTOR = 2048

f = open(ISO, 'rb')

def read_at(off, n):
    f.seek(off); return f.read(n)

vd = read_at(BASE + 32*SECTOR, 0x30)
assert vd[:20] == b"MICROSOFT*XBOX*XBOX*"[:0] + b"MICROSOFT*XBOX*MEDIA"
root_sector, root_size = struct.unpack_from("<II", vd, 0x14)
print("root sector 0x%X size %d" % (root_sector, root_size))

entries = []
def walk_table(sector, size, path):
    data = read_at(BASE + sector*SECTOR, size)
    def node(off):
        if off*4 >= len(data): return
        o = off*4
        if o + 14 > len(data): return
        left, right, start, fsize = struct.unpack_from("<HHII", data, o)
        attr = data[o+12]; nlen = data[o+13]
        name = data[o+14:o+14+nlen].decode('utf-8','replace')
        if left == 0xFFFF: return
        if left: node(left)
        full = path + "/" + name
        isdir = bool(attr & 0x10)
        entries.append((full, isdir, start, fsize))
        if isdir and fsize:
            walk_table(start, fsize, full)
        if right: node(right)
    node(0)

walk_table(root_sector, root_size, "")
print("total entries:", len(entries))
print("\n=== ROOT LEVEL ===")
for p,d,s,sz in sorted(entries):
    if p.count('/') == 1:
        print(("DIR  " if d else "FILE "), p, sz)

with open("iso_listing.txt","w",encoding="utf-8") as out:
    for p,d,s,sz in sorted(entries):
        out.write("%s\t%s\t%d\t%d\n" % ("D" if d else "F", p, s, sz))
print("\nwrote iso_listing.txt")

os.makedirs(r"C:\Programming\GitHub\Halo-3-MP\work\extracted", exist_ok=True)
for p,d,s,sz in entries:
    if p == "/default.xex":
        f.seek(BASE + s*SECTOR)
        open(r"C:\Programming\GitHub\Halo-3-MP\work\extracted\default.xex","wb").write(f.read(sz))
        print("extracted default.xex", sz)
print("\n=== /maps ===")
for p,d,s,sz in sorted(entries):
    if p.startswith("/maps/"):
        print(p, sz)
