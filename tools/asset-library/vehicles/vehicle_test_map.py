"""Throwaway vehicle-only test map for the Reach Falcon / Revenant (separate from test_map.py's asset_library_test so
the two sessions' builds never share a scenario or cache name). Same base and fixes as test_map.py: copy of stock
s3d_edge, Falcon and Revenant placed in front of the player start, test-only lightmap copy, scripts cleared.

  python vehicle_test_map.py scenario          levels\\test\\asset_library_test\\vehicle_test.scenario
  python vehicle_test_map.py build [x64|pc]    build-cache-file into the private kit's maps folder (hidden desktop)
Run with OPENH3M_ASSET_KIT=.local/asset-kit-h3-veh.
"""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit

BS = chr(92)
def wp(*p): return BS.join(p)
SCN = wp('levels', 'test', 'asset_library_test', 'vehicle_test')
SRC = wp('levels', 'multi', 's3d_edge', 's3d_edge.scenario')
W = kit.WORK / 'vehicle-session'; W.mkdir(parents=True, exist_ok=True)
# player start (18.56, -1.74, 0.06) faces +x; vehicles a few metres ahead
NEW_VEHICLES = [(wp('objects', 'vehicles', 'reach_revenant', 'reach_revenant.vehicle'), (21.5, -5.5, 0.6), 20261131),
                (wp('objects', 'vehicles', 'reach_falcon', 'reach_falcon.vehicle'), (22.5, 0.5, 2.5), 20261132)]


def scenario():
    T = SCN + '.scenario'
    ops = [{'op': 'copy', 'from': SRC, 'to': T, 'overwrite': True}]
    LM = wp('levels', 'test', 'asset_library_test', 'vehicle_test_lightmap.scenario_lightmap')
    ops += [{'op': 'copy', 'from': wp('levels', 'multi', 's3d_edge', 's3d_edge_faux_lightmap.scenario_lightmap'), 'to': LM, 'overwrite': True},
            {'op': 'clear', 'tag': LM, 'block': 'Block:per-vertex lightmap BSPs'},
            {'op': 'set', 'tag': T, 'field': 'new lightmaps', 'value': LM},
            {'op': 'add', 'tag': T, 'block': 'Block:vehicle palette', 'count': len(NEW_VEHICLES)},
            {'op': 'add', 'tag': T, 'block': 'Block:vehicles', 'count': len(NEW_VEHICLES)}]
    for i, (obj, pos, uid) in enumerate(NEW_VEHICLES):
        V = 'Block:vehicles[%d]/' % i
        ops += [{'op': 'set', 'tag': T, 'field': 'Block:vehicle palette[%d]/name' % i, 'value': obj},
                {'op': 'set', 'tag': T, 'field': V + 'type', 'value': str(i)},
                {'op': 'set', 'tag': T, 'field': V + 'Struct:object data[0]/position', 'value': '%s,%s,%s' % pos},
                {'op': 'set', 'tag': T, 'field': V + 'Struct:object data[0]/Struct:object id[0]/unique id', 'value': str(uid)},
                {'op': 'set', 'tag': T, 'field': V + 'Struct:object data[0]/Struct:object id[0]/type', 'value': 'vehicle'},
                {'op': 'set', 'tag': T, 'field': V + 'Struct:object data[0]/Struct:object id[0]/source', 'value': 'editor'},
                {'op': 'set', 'tag': T, 'field': V + 'Struct:multiplayer data[0]/owner team', 'value': 'neutral'},
                {'op': 'set', 'tag': T, 'field': V + 'Struct:multiplayer data[0]/quota maximum', 'value': '1'}]
    for b in ('Block:scripts', 'Block:globals', 'Block:source files', 'Block:hs syntax datums'):
        ops.append({'op': 'clear', 'tag': T, 'block': b})
    print(kit.edit(ops, 'vehicle_test_scenario'))


def build(platform='x64'):
    t = time.time()
    rc, out = kit.htool('build-cache-file', SCN, platform, log=W / ('build-%s.log' % platform), timeout=3600,
                        exe='tool_fast.exe' if platform == 'x64' else 'tool.exe')
    cache = kit.KIT / 'maps' / 'vehicle_test.map'
    errors = [l.strip() for l in out.splitlines() if re.search(r'\b(ERROR|FATAL|EXCEPTION)\b', l)]
    ours = [l.strip() for l in out.splitlines() if re.search(r'reach_falcon|reach_revenant', l, re.I)]
    rep = dict(platform=platform, returncode=rc, seconds=round(time.time() - t), cache=str(cache), exists=cache.exists(),
               bytes=cache.stat().st_size if cache.exists() else 0, sha256=kit.sha(cache) if cache.exists() else None,
               error_lines=errors[:80], lines_mentioning_assets=ours[:200])
    (W / ('build-report-%s.json' % platform)).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k not in ('error_lines', 'lines_mentioning_assets')}))
    print('ERRORS', len(errors)); print(chr(10).join(errors[:30]))
    print('ASSET LINES', len(ours)); print(chr(10).join(ours[:80]))


if __name__ == '__main__':
    {'scenario': scenario, 'build': lambda: build(*(sys.argv[2:3] or ['x64']))}[sys.argv[1]]()
