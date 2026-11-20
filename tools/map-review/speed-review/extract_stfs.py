"""Extract flat files from a single-backing STFS container (read-only source)."""
import struct, sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/warlock-conversion/snapshot/tools'))
from verify_dlc_stfs import data_block, table_block, read_directory

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
with src.open('rb') as s:
    base, directory, used = read_directory(s)
    for o in range(0, len(directory), 64):
        row = directory[o:o + 64]
        n = row[40] & 63
        if not n:
            continue
        name = row[:n].decode('ascii')
        assert Path(name).name == name
        size = int.from_bytes(row[52:56], 'big')
        index = int.from_bytes(row[47:50], 'little')
        h = hashlib.sha256()
        with (out / name).open('wb') as f:
            left = size
            while left > 0:
                s.seek(base + data_block(index) * 4096)
                b = s.read(4096)[:min(4096, left)]
                f.write(b); h.update(b); left -= len(b)
                s.seek(base + table_block(index, 0) * 4096 + index % 170 * 24 + 20)
                index = struct.unpack('>I', s.read(4))[0] & 0xFFFFFF
        print(name, size, h.hexdigest())
