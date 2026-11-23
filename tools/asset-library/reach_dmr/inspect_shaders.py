"""Export Reach shaders with the official HREK tool and list options, parameters, bitmaps and function values.

Reach XML writes block elements as siblings after the block field, so this walks elements in document order.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit

D = kit.WORK / 'reach_dmr' / 'reach-xml'
def summarize(xml):
    text = Path(xml).read_bytes().decode('latin-1')
    rec = {'definition': re.search(r'name="definition" value="([^"]*)"', text).group(1), 'options': [], 'params': []}
    opt = text.split('name="options"', 1)[1].split('name="parameters"', 1)[0]
    rec['options'] = [int(v) for v in re.findall(r'name="short" value="(-?\d+)"', opt)]
    body = text.split('name="parameters"', 1)[1]
    for chunk in re.split(r'<element index="\d+" name="(?=[a-z_0-9]+">\s*<field name="parameter name")', body)[1:]:
        name = re.search(r'name="parameter name" value="([^"]*)"', chunk).group(1)
        p = {'name': name, 'type': re.search(r'name="parameter type" value="([^"]*)"', chunk).group(1)}
        b = re.search(r'name="bitmap" value="([^"]*)"', chunk)
        if b and b.group(1): p['bitmap'] = b.group(1)
        r = re.search(r'name="real" value="([^"]*)"', chunk)
        if r and r.group(1) != '0': p['real'] = r.group(1)
        data = re.findall(r'name="data" value="([^"]*)"', chunk)
        if data: p['function_data'] = data[0][:120]
        rec['params'].append(p)
    return rec

out = {}
for n in sys.argv[1:]:
    n = n.replace('/', '\\')
    tag = n if '\\' in n else 'objects\\weapons\\rifle\\dmr\\shaders\\' + n + '.shader'
    name = tag.split('\\')[-1]
    rec = summarize(kit.rxml(tag, D / (name + '.xml')))
    out[name] = rec
    print(name, rec['definition'], 'options', rec['options'])
    for p in rec['params']:
        print('    ', p['name'], p.get('bitmap', ''), p.get('real', ''), ('fn ' + p['function_data'][:60]) if 'function_data' in p else '')
(D / 'shader-summary.json').write_text(json.dumps(out, indent=1))
