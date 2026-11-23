"""Remove this session's files from the shared H3EK tags tree after verifying the asset-library copies.

Lists every removed file (with SHA-256) in work/asset-library/_work/removed-from-shared-kit.json.
Asset tag files are removed only if an identical copy exists under work/asset-library/<asset>/tags/.
Test-map files (scenario, scale test, sound gestalt) are removed outright; they are throwaway build inputs.
"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit
from package import ASSETS

SHARED = kit.ROOT / '.local/h3ek-source/tags'
removed, refused = [], []
for asset, roots in ASSETS.items():
    for r in roots:
        base = SHARED / r
        if not base.exists(): continue
        for f in sorted(p for p in base.rglob('*') if p.is_file()):
            copy = kit.LIB / asset / 'tags' / f.relative_to(SHARED)
            h = kit.sha(f)
            if copy.is_file() and kit.sha(copy) == h:
                removed.append(dict(path=str(f), sha256=h, library_copy=str(copy)))
            else:
                refused.append(str(f))
throwaway = [SHARED / 'levels/test/asset_library_test', SHARED / 'reports/asset_library_test.sound_cache_file_gestalt']
for t in throwaway:
    files = [t] if t.is_file() else sorted(p for p in t.rglob('*') if p.is_file()) if t.exists() else []
    for f in files:
        removed.append(dict(path=str(f), sha256=kit.sha(f), library_copy=None))
if refused:
    print('REFUSED (no identical library copy):', refused); sys.exit(1)
(kit.WORK / 'removed-from-shared-kit.json').write_text(json.dumps(removed, indent=1))
for row in removed:
    p = Path(row['path'])
    assert str(p.resolve()).startswith(str(SHARED.resolve())), p
    p.unlink()
# remove now-empty directories under our roots only
for d in [SHARED / r for rs in ASSETS.values() for r in rs] + [SHARED / 'levels/test/asset_library_test']:
    if d.exists():
        for sub in sorted((x for x in d.rglob('*') if x.is_dir()), key=lambda x: len(str(x)), reverse=True):
            if not any(sub.iterdir()): sub.rmdir()
        if not any(d.iterdir()): d.rmdir()
print('REMOVED', len(removed), 'files from the shared kit; list in', kit.WORK / 'removed-from-shared-kit.json')
