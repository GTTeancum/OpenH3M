"""Copy each asset's new H3 tags (and their source data) from the kit into work/asset-library/<asset>/ with a manifest.

Layout per asset:  tags/<tag path>   data/<source path>   manifest.json (path, bytes, sha256 for every file)
Only files under the asset's own new tag roots are copied; stock tags they reference are listed as stock references.
Usage: python package.py [asset ...]
"""
import json, re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit

BS = chr(92)
ASSETS = {
    'ce_magnum': ['objects\\weapons\\pistol\\ce_magnum'],
    'reach_dmr': ['objects\\weapons\\rifle\\reach_dmr'],
    'reach_falcon': ['objects\\vehicles\\reach_falcon'],
    'reach_revenant': ['objects\\vehicles\\reach_revenant'],
}


def stock_refs(tag_files, own_roots):
    """Tag references (from tool.exe XML exports) that point outside the asset's own folders."""
    refs = set()
    for t in tag_files:
        rel = str(t.relative_to(kit.TAGS))
        if t.suffix in ('.bitmap',):  # bitmaps hold no tag references worth listing
            continue
        try:
            x = kit.to_xml(rel, kit.WORK / 'package-xml' / (rel.replace(BS, '__') + '.xml'))
        except Exception as ex:
            refs.add('UNREADABLE ' + rel + ': ' + str(ex)[:80]); continue
        for m in re.finditer(r'type="tag reference"[^>]*|value="([^"]+),([a-z_ *]+)"', x.read_text(errors='replace')):
            if m.group(1) and not any(m.group(1).lower().startswith(r.lower()) for r in own_roots):
                refs.add(m.group(1) + ',' + m.group(2).strip())
    return sorted(refs)


def package(asset):
    roots = ASSETS[asset]; out = kit.LIB / asset
    files = []
    for kind, base in (('tags', kit.TAGS), ('data', kit.DATA)):
        for r in roots:
            src = base / r
            if not src.exists(): continue
            for f in sorted(p for p in src.rglob('*') if p.is_file()):
                dst = out / kind / f.relative_to(base)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                files.append(dict(path=str(dst.relative_to(out)), bytes=f.stat().st_size, sha256=kit.sha(f)))
    tag_files = [base for base in (kit.TAGS / r for r in roots) if base.exists() for base in base.rglob('*') if base.is_file()]
    manifest = dict(asset=asset, tag_roots=roots, files=files, tag_bytes=sum(f['bytes'] for f in files if f['path'].startswith('tags')),
                    stock_references=stock_refs(tag_files, roots))
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    print(asset, len(files), 'files,', manifest['tag_bytes'], 'tag bytes,', len(manifest['stock_references']), 'stock references')


if __name__ == '__main__':
    for a in (sys.argv[1:] or ASSETS):
        package(a)
