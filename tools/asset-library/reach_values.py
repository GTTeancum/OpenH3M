"""Export Reach gameplay tags with the official HREK tool and print selected non-zero fields.

Usage: python reach_values.py <out_dir> <tag rel path ('/' ok)> [--grep a,b,c]
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit

out = Path(sys.argv[1]); words = None
args = sys.argv[2:]
if '--grep' in args:
    i = args.index('--grep'); words = args[i + 1].lower().split(','); args = args[:i] + args[i + 2:]
for t in args:
    rel = t.replace('/', '\\'); name = rel.split('\\')[-1]
    x = kit.rxml(rel, out / (name + '.xml'))
    print('==', rel)
    text = x.read_bytes().decode('latin-1')
    for m in re.finditer(r'<field name="([^"]+)" value="([^"]*)" type="([^"]+)"', text):
        n, v, ty = m.groups()
        if ty in ('block', 'struct', 'explanation', 'custom') or v in ('', '0', '0,0', '0,0,0', '-1'): continue
        if words and not any(w in n.lower() for w in words): continue
        print('  ', n, '=', v)
