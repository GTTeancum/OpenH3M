"""Read-only source/native PVS and portal comparison; no visibility guessed."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools/warlock-conversion/snapshot/tools'
sys.path.insert(0, str(TOOLS))
from cache_reader import Cache
from source_schema import load_schema

REFERENCE = TOOLS.parent / 'reference'

def field(schema, name):
    return next(n for n in schema if n.get('name') == name)

def rows(cache, at, node):
    return cache.block(at + int(node.get('offset'), 0), int(node.get('elementSize'), 0))

def inspect(path, mcc):
    cache = Cache(path, mcc)
    try:
        schema = load_schema(cache, 'scnr', REFERENCE) if mcc else ET.parse(REFERENCE / 'plugins/scnr.xml').getroot()
        bsp_schema = load_schema(cache, 'sbsp', REFERENCE) if mcc else ET.parse(REFERENCE / 'plugins/sbsp.xml').getroot()
        scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
        zone_node = field(schema, 'Zone Set Potentially Visible Sets')
        zones = []
        for zone in rows(cache, scenario, zone_node):
            structures = field(zone_node, 'Structure Potentially Visible Sets')
            matrices = []
            for bsp in rows(cache, zone, structures):
                views = []
                for node in structures:
                    if node.tag != 'tagblock' or 'Potentially Visible' not in node.get('name', ''):
                        continue
                    values = []
                    for row in rows(cache, bsp, node):
                        vectors = []
                        vector_node = next(n for n in node if n.tag == 'tagblock')
                        word_node = next(n for n in vector_node if n.tag == 'tagblock')
                        for vector in rows(cache, row, vector_node):
                            vectors.append([cache.u(word) for word in rows(cache, vector, word_node)])
                        values.append(vectors)
                    views.append(dict(name=node.get('name'), rows=values))
                matrices.append(views)
            zones.append(matrices)
        bsps = []
        for tag in cache.tags.values():
            if tag['group'] != 'sbsp':
                continue
            at = tag['offset']
            cluster_node = field(bsp_schema, 'Clusters')
            portal_node = field(bsp_schema, 'Cluster Portals')
            clusters = rows(cache, at, cluster_node)
            portals = rows(cache, at, portal_node)
            bsps.append(dict(clusters=len(clusters), portals=len(portals),
                             portal_connections=[cache.unpack('2h', p) for p in portals]))
        return dict(path=str(path), zones=zones, bsps=bsps)
    finally:
        cache.close()

installed = next((ROOT / 'work/dlc/installed-corrections').rglob('powerhouse.map'))
source = Path('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_powerhouse.map')
native = inspect(installed, False)
original = inspect(source, True)
assert len(native['zones']) == len(original['zones']) == 1
assert len(native['zones'][0]) == 1
tables = native['zones'][0][0]
assert len(tables) == 2 and all(len(t['rows']) == 18 for t in tables)
assert all(len(row) == 1 and len(row[0]) == 1 for t in tables for row in t['rows'])
report = dict(native=native, source=original,
              pvs_values_equal=native['zones'] == original['zones'],
              cluster_portal_topology_equal=native['bsps'] == original['bsps'],
              visible_clusters_per_row=[[sum(word.bit_count() for vector in row for word in vector)
                                         for row in t['rows']] for t in tables],
              scope='Static PVS words and cluster portal topology only; does not prove runtime culling or draw cost.')
output = ROOT / 'work/map-review-20261105/powerhouse-visibility-audit.json'
output.write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('native','source')}))
print('Native BSP counts:', [(b['clusters'], b['portals']) for b in native['bsps']])
