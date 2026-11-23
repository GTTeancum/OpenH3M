"""Export Halo 2 tags to XML with the Halo 2 editing kit's own tool (export-tag-to-xml), on a hidden desktop.
Usage: h2_export_xml.py <file listing tag paths relative to the tags folder, with extension> <out dir>"""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/asset-library'))
import hidden_run
K = ROOT / '.local/h2ek-source'
BS = chr(92)
e = os.environ.copy(); e['TEMP'] = e['TMP'] = str(K / 'temp')
out = Path(sys.argv[2]).resolve();out.mkdir(parents=True, exist_ok=True); ok = 0
for line in Path(sys.argv[1]).read_text().split('\n'):
    t = line.strip().replace('/', BS)
    if not t: continue
    dest = out / (t.replace(BS, '~') + '.xml')
    rc, log = hidden_run.run([str(K / 'tool.exe'), 'export-tag-to-xml', str(K / 'tags' / t), str(dest)], str(K), str(K / 'temp/xml.log'), timeout=120, env=e)
    ok += dest.exists()
    if not dest.exists(): print('FAILED', t, log[-300:])
print('exported', ok)
