"""Read-only: dump and compare scenario zone-set PVS between a native 360 cache and an MCC cache."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

def pvs(path, mcc):
    c = Cache(path, mcc)
    scnr = [t for t in c.tags.values() if t['group'] == 'scnr']
    assert len(scnr) == 1, len(scnr)
    root = scnr[0]['offset']
    out = []
    for z in c.block(root + (0x40 if mcc else 0x3C), 0x2C):
        mask, = c.unpack('I', z)
        ver, flags = c.unpack('HH', z + 4)
        sums = [c.u(o) for o in c.block(z + 8, 4)]
        bsps = []
        for b in c.block(z + 0x14, 0x54):
            mats = {}
            for key, off in (('open', 0), ('closed', 0xC)):
                rows = []
                for r in c.block(b + off, 0xC):
                    vec = []
                    for per_bsp in c.block(r, 0xC):
                        vec.append([c.u(w) for w in c.block(per_bsp, 4)])
                    rows.append(vec)
                mats[key] = rows
            mats['attached_sky'] = [c.data[o] for o in c.block(b + 0x18, 1)]
            mats['visible_sky'] = [c.data[o] for o in c.block(b + 0x24, 1)]
            bsps.append(mats)
        out.append(dict(mask=mask, version=ver, flags=flags, checksums=sums, bsps=bsps))
    c.close()
    return out

def summarize(label, zones):
    print('==', label, 'zone sets:', len(zones))
    for zi, z in enumerate(zones):
        print(f' zone {zi}: mask={z["mask"]:#x} ver={z["version"]} flags={z["flags"]} checksums={[hex(s) for s in z["checksums"]]}')
        for bi, b in enumerate(z['bsps']):
            for key in ('open', 'closed'):
                rows = b[key]
                n = len(rows)
                counts = [sum(bin(w).count('1') for v in r for w in v) for r in rows]
                if n:
                    print(f'  bsp {bi} {key}: clusters={n} visible-per-cluster min={min(counts)} avg={sum(counts)/n:.1f} max={max(counts)} full-rows={sum(1 for k in counts if k>=n)}')
                else:
                    print(f'  bsp {bi} {key}: EMPTY')

a = pvs(sys.argv[1], False)
b = pvs(sys.argv[2], True)
summarize('360 ' + sys.argv[1], a)
summarize('MCC ' + sys.argv[2], b)
same = [za['bsps'][i][k] == zb['bsps'][i][k] for za, zb in zip(a, b) for i in range(min(len(za['bsps']), len(zb['bsps']))) for k in ('open', 'closed')]
print('matrices identical:', same)
Path(sys.argv[3]).write_text(json.dumps(dict(native=a, mcc=b)))
