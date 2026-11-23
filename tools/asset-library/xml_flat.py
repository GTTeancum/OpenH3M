"""Flatten a tool.exe export-tag-to-xml file to 'path<TAB>value' lines (read-only helper for inspection).

Usage: python xml_flat.py <file.xml> [regex filter on path] [--nonzero]
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit


def flat(xml_path):
    root = kit.parse_xml(xml_path); out = []
    def walk(e, prefix):
        pending = None
        for c in e:
            if c.tag == 'field':
                n, v, t = c.get('name'), c.get('value'), c.get('type')
                if t == 'block': pending = n; out.append((prefix + n, v)); continue
                if t in ('pad', 'explanation', 'custom', 'useless pad', 'skip'): continue
                out.append((prefix + n, v))
            elif c.tag == 'element':
                walk(c, prefix + '%s[%s]/' % (pending, c.get('index')))
            elif c.tag in ('struct', 'array', 'block'):
                walk(c, prefix + (c.get('name') or '') + '/')
            else:
                walk(c, prefix)
    walk(root, '')
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    pat = re.compile(args[1], re.I) if len(args) > 1 else None
    nz = '--nonzero' in sys.argv
    for p, v in flat(args[0]):
        if pat and not pat.search(p): continue
        if nz and v in (None, '', '0', '0,0', '0,0,0', '-1', 'NONE', ' '): continue
        print(p + '\t' + str(v))
