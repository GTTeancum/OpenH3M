import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import mopp_validate as mv
from mopp_validate import *
maps = Path(sys.argv[1])
ops = collections.Counter(); maxkey = 0; sizes = []
for path in sys.argv[2:]:
    c = Cache(path)
    bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
    mopps = c.block(bsp + 0x320, 0x20)
    for mo in mopps:
        size = c.u(mo)
        if not size: continue
        at = c.pointer(c.u(mo + 0xC)); blob = bytes(c.data[at:at + size])
        for (off, scale, code, _, _) in mopp_objects(blob)[:1]:
            # linear reachable scan
            stack = [0]; seen = set()
            while stack:
                a = stack.pop()
                while a not in seen and 0 <= a < len(code):
                    seen.add(a); op = code[a]; ops[op if op < 0x30 or op >= 0x50 else 0x30] += 1
                    if op == 0 or 0x30 <= op <= 0x53: break
                    if 1 <= op <= 4: a += 4
                    elif 5 <= op <= 7: s = op - 4; a += 1 + s + int.from_bytes(code[a+1:a+1+s], 'big')
                    elif op in (9, 10, 11): a += {9: 2, 10: 3, 11: 5}[op]
                    elif 0x10 <= op <= 0x1c: stack.append(a + 4 + code[a+3]); a += 4
                    elif 0x20 <= op <= 0x22: stack.append(a + 3 + code[a+2]); a += 3
                    elif 0x23 <= op <= 0x25: stack.append(a + 7 + int.from_bytes(code[a+5:a+7], 'big')); a += 7 + int.from_bytes(code[a+3:a+5], 'big')
                    elif 0x26 <= op <= 0x28: a += 3
                    elif 0x29 <= op <= 0x2b: a += 7
                    else: ops['unknown %#x' % op] += 1; break
            sizes.append(len(code))
    c.close()
print({(hex(k) if isinstance(k, int) else k): v for k, v in sorted(ops.items(), key=lambda x: str(x[0]))})
print('max code size', max(sizes))
