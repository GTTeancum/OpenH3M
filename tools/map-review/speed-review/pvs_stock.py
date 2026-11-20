import sys, importlib.util
from pathlib import Path
sys.argv_backup = sys.argv
spec = importlib.util.spec_from_file_location('p', Path(__file__).with_name('pvs_compare.py'))
src = Path(__file__).with_name('pvs_compare.py').read_text().split("\na = pvs(")[0]
ns = {'__file__': __file__}
exec(src, ns)
for path in sys.argv[1:]:
    try:
        z = ns['pvs'](path, False)
    except Exception as e:
        print(Path(path).name, 'ERR', e); continue
    for zone in z:
        for b in zone['bsps']:
            rows = b['open']; n = len(rows)
            if not n: continue
            counts = [sum(bin(w).count('1') for v in r for w in v) for r in rows]
            print(f'{Path(path).name:22s} clusters={n:3d} min={min(counts):3d} avg={sum(counts)/n:5.1f} ({100*sum(counts)/n/n:4.0f}%) max={max(counts)}')
