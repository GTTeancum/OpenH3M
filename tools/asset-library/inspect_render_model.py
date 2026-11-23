"""Summarize a stock H3 render_model from tool.exe XML: nodes, markers, materials, triangle count."""
import sys
from pathlib import Path, PureWindowsPath
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit

def summarize(tag):
    x = kit.parse_xml(kit.to_xml(tag, kit.WORK / 'donor-xml' / (PureWindowsPath(tag).name + '.xml')))
    print('==', tag)
    for e in x.find("./block[@name='nodes']"):
        f = kit.fields(e); print('  NODE', f['name'], 'parent', f['parent node'].split(',')[-1], 'T', f['default translation'], 'R', f['default rotation'])
    for e in x.find("./block[@name='marker groups']"):
        print('  MARKER', kit.fields(e)['name'], [(kit.fields(m)['node index'], kit.fields(m)['translation']) for m in e.find('block')])
    for e in x.find("./block[@name='materials']"): print('  MAT', kit.fields(e).get('render method'))
    tris = 0
    for mesh in x.find("./block[@name='meshes']"):
        for part in mesh.find("./block[@name='parts']"):
            f = kit.fields(part); tris += int(f.get('index count', '0'))
        print('  MESH index-type', kit.fields(mesh).get('index buffer type'), 'vertex type', kit.fields(mesh).get('vertex type'))
    print('  INDEX_COUNT_TOTAL', tris)

for t in sys.argv[1:]: summarize(t)
