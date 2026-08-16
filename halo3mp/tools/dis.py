"""Disassemble a guest address range from the decrypted default.xex."""
import sys, os, subprocess, struct
import xexlib

G = r"C:\Programming\GitHub\Halo-3-MP\work\gamedata"
OBJDUMP = r"C:\Programming\GitHub\Halo-3-MP\work\rexglue-sdk\tools\binutils\powerpc-none-elf-objdump.exe"
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_dis.bin")

_cache = {}


def image(path):
    if path not in _cache:
        x = xexlib.Xex(path)
        _cache[path] = (x, x.image())
    return _cache[path]


def dis(path, start, end):
    x, img = image(path)
    off = start - x.image_base
    n = end - start
    if off < 0 or off + n > len(img):
        print("range out of image (image len 0x%X, off 0x%X)" % (len(img), off))
        return
    open(TMP, "wb").write(img[off:off + n])
    out = subprocess.run([OBJDUMP, "-D", "-b", "binary", "-m", "powerpc:common64",
                          "-EB", "--adjust-vma=0x%X" % start, TMP],
                         capture_output=True, text=True)
    lines = out.stdout.splitlines()
    started = False
    for ln in lines:
        if "<.data>:" in ln:
            started = True
            continue
        if started and ln.strip():
            print(ln)


if __name__ == "__main__":
    path = os.path.join(G, "default.xex")
    for a, b, label in [(int(sys.argv[1], 16), int(sys.argv[2], 16), "range")]:
        print("=== 0x%08X .. 0x%08X ===" % (a, b))
        dis(path, a, b)
