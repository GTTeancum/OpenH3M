"""Turn exported texture pixels (MaterialSwap export-pixels-list) into half-size TIFFs in the kit's data folder,
ready for the kit's own importer (tool bitmaps <folder>). Writes the list of folders to import."""
import subprocess, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / '.local/texture-shrink'
E = WORK / 'export'; DATA = ROOT / '.local/h3ek-source/data'
BS = chr(92)
ok, bad = [], []
for line in (Path(sys.argv[1]) if len(sys.argv) > 1 else WORK / 'list.txt').read_text().split():
    tag = line[:-len('.bitmap')]
    b = E / (tag.replace(BS, '~') + '.bitmap.bin')
    out = DATA / (tag.replace(BS, '/') + '.tif')
    r = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('texture_to_tiff.py')), str(b), str(out)], capture_output=True, text=True)
    msg = (r.stdout or r.stderr).strip().splitlines()
    (ok if r.returncode == 0 else bad).append((tag, msg[-1] if msg else ''))
print('converted', len(ok), 'failed', len(bad))
for t, m in bad: print('  FAILED', t, m)
dirs = sorted({BS.join(t.split(BS)[:-1]) for t, _ in ok})
(Path(sys.argv[2]) if len(sys.argv) > 2 else WORK / 'dirs.txt').write_text('\n'.join(dirs) + '\n')
(WORK / 'converted.txt').write_text('\n'.join(t for t, _ in ok) + '\n')
print(len(dirs), 'folders')
print(collections.Counter(m.split('->')[1].split()[0] if '->' in m else m for _, m in ok).most_common(8))
