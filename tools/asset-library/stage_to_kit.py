"""Copy asset-library tag sets back into the shared H3EK tags tree for a test build, recording every file added.

  python stage_to_kit.py in    copy work/asset-library/<asset>/tags/* -> kit tags (refuses to overwrite existing files)
  python stage_to_kit.py out   remove exactly the files recorded by 'in' (only if unchanged since copying)
"""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit
from package import ASSETS

SHARED = kit.ROOT / '.local/h3ek-source/tags'
RECORD = kit.WORK / 'staged-in-shared-kit.json'

def stage_in():
    added = []
    for asset in ASSETS:
        src = kit.LIB / asset / 'tags'
        for f in sorted(p for p in src.rglob('*') if p.is_file()):
            dst = SHARED / f.relative_to(src)
            if dst.exists(): raise SystemExit('refusing to overwrite existing kit file: %s' % dst)
            dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
            added.append(dict(path=str(dst), sha256=kit.sha(dst)))
    RECORD.write_text(json.dumps(added, indent=1)); print('STAGED', len(added), 'files')

def stage_out(only=None):
    rows = json.loads(RECORD.read_text()); removed = 0
    keep_roots = [str(SHARED / r).lower() for a, rs in ASSETS.items() if only and a not in only for r in rs]
    for r in rows:
        p = Path(r['path'])
        if any(str(p).lower().startswith(k) for k in keep_roots): continue  # owned by another session now
        if p.exists():
            if kit.sha(p) != r['sha256']: print('CHANGED, kept:', p); continue
            p.unlink(); removed += 1
    for root in [SHARED / r for a, rs in ASSETS.items() if not only or a in only for r in rs]:
        if root.exists():
            for d in sorted((x for x in root.rglob('*') if x.is_dir()), key=lambda x: len(str(x)), reverse=True):
                if not any(d.iterdir()): d.rmdir()
            if not any(root.iterdir()): root.rmdir()
    print('REMOVED', removed, 'of', len(rows))

if __name__ == '__main__':
    stage_in() if sys.argv[1] == 'in' else stage_out(sys.argv[2:] or None)
