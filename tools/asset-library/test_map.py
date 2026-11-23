"""Throwaway test map: copy of stock Sandbox (Halo 3 Forge map) with palette entries pointed at the asset-library objects.

  python test_map.py scenario   create/refresh levels\\test\\asset_library_test\\asset_library_test.scenario
  python test_map.py build      tool_fast build-cache-file ... x64 (hidden desktop), report + reference check
Nothing here touches an installed map; the cache is written to .local/asset-kit-h3/maps.
"""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit

BS = chr(92)
def wp(*p): return BS.join(p)
SCN = wp('levels', 'test', 'asset_library_test', 'asset_library_test')
SRC = wp('levels', 'dlc', 'sandbox', 'sandbox.scenario')
W = kit.WORK / 'test_map'; W.mkdir(parents=True, exist_ok=True)
# palette swaps: (block, index in stock construct palette, stock object it replaces, new object)
SWAPS = [
    ('weapon palette', 1, wp('objects', 'weapons', 'rifle', 'battle_rifle', 'battle_rifle.weapon'), wp('objects', 'weapons', 'rifle', 'reach_dmr', 'reach_dmr.weapon')),
    ('weapon palette', 12, wp('objects', 'weapons', 'pistol', 'needler', 'needler.weapon'), wp('objects', 'weapons', 'pistol', 'ce_magnum', 'ce_magnum.weapon')),
    ('vehicle palette', 0, wp('objects', 'vehicles', 'warthog', 'warthog.vehicle'), wp('objects', 'vehicles', 'reach_falcon', 'reach_falcon.vehicle')),
    ('vehicle palette', 2, wp('objects', 'vehicles', 'mongoose', 'mongoose.vehicle'), wp('objects', 'vehicles', 'reach_revenant', 'reach_revenant.vehicle')),
]
NEW_VEHICLES = []  # Sandbox already places warthogs and mongooses on its main floor
EXTRA = json.loads((W / 'extra_swaps.json').read_text()) if (W / 'extra_swaps.json').exists() else []


def scenario():
    stock = kit.dump(SRC).read_text().splitlines()
    ops = [{'op': 'copy', 'from': SRC, 'to': SCN + '.scenario', 'overwrite': True}]
    for block, idx, old, new in SWAPS + [tuple(x) for x in EXTRA]:
        line = next(l for l in stock if l.startswith('Block:%s[%d]/name\t' % (block, idx)))
        assert line.split('\t')[2] == old, (block, idx, line)
        ops.append({'op': 'set', 'tag': SCN + '.scenario', 'field': 'Block:%s[%d]/name' % (block, idx), 'value': new})
    # Stock zanzibar_faux_lightmap lists a per-vertex lightmap BSP tag that is not in the H3EK tag set (null in the
    # built map). Use a test-only copy without that row; the stock lightmap tag is untouched.
    LM = wp('levels', 'test', 'asset_library_test', 'asset_library_test_lightmap.scenario_lightmap')
    ops += [{'op': 'copy', 'from': wp('levels', 'dlc', 'sandbox', 'sandbox_faux_lightmap.scenario_lightmap'), 'to': LM, 'overwrite': True},
            {'op': 'clear', 'tag': LM, 'block': 'Block:per-vertex lightmap BSPs'},
            {'op': 'set', 'tag': SCN + '.scenario', 'field': 'new lightmaps', 'value': LM}]
    if NEW_VEHICLES:
        ops += [{'op': 'add', 'tag': SCN + '.scenario', 'block': 'Block:vehicle palette', 'count': len(NEW_VEHICLES)},
                {'op': 'add', 'tag': SCN + '.scenario', 'block': 'Block:vehicles', 'count': len(NEW_VEHICLES)}]
    for i, (obj, pos, uid) in enumerate(NEW_VEHICLES):
        V = 'Block:vehicles[%d]/' % i
        ops += [{'op': 'set', 'tag': SCN + '.scenario', 'field': 'Block:vehicle palette[%d]/name' % i, 'value': obj},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'type', 'value': str(i)},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'Struct:object data[0]/position', 'value': '%s,%s,%s' % pos},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'Struct:object data[0]/Struct:object id[0]/unique id', 'value': str(uid)},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'Struct:object data[0]/Struct:object id[0]/type', 'value': 'vehicle'},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'Struct:object data[0]/Struct:object id[0]/source', 'value': 'editor'},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'Struct:multiplayer data[0]/owner team', 'value': 'neutral'},
                {'op': 'set', 'tag': SCN + '.scenario', 'field': V + 'Struct:multiplayer data[0]/quota maximum', 'value': '1'}]
    # No scripts in the throwaway test map (the converter only stages audited script scenarios; Zanzibar's scripts
    # drive its gate/wheel only). Stock zanzibar.scenario is untouched.
    # Sandbox stores its object blocks in separate scenario resource tags; at build time those are copied over the
    # scenario's own blocks, which silently undid the palette swaps (and left the new objects out of every zone).
    # The test copy keeps its object data in the scenario itself.
    ops.append({'op': 'clear', 'tag': SCN + '.scenario', 'block': 'Block:scenario resources'})
    for b in ('Block:scripts', 'Block:globals', 'Block:source files', 'Block:hs syntax datums'):
        ops.append({'op': 'clear', 'tag': SCN + '.scenario', 'block': b})
    print(kit.edit(ops, 'test_scenario'))
    placed = {}
    for block, idx, old, new in SWAPS + [tuple(x) for x in EXTRA]:
        placements = block.replace(' palette', 's')
        placed[new] = sum(1 for l in stock if l.startswith('Block:%s[' % placements) and '/type\t' in l and l.endswith('\t%d' % idx))
    print('PLACEMENTS', placed)


def build():
    t = time.time()
    platform = sys.argv[2] if len(sys.argv) > 2 else 'pc'
    rc, out = kit.htool('build-cache-file', SCN, platform, log=W / ('build-%s.log' % platform), timeout=3600, exe='tool_fast.exe')
    cache = kit.KIT / 'maps' / 'asset_library_test.map'
    errors = [l.strip() for l in out.splitlines() if re.search(r'\b(ERROR|FATAL|EXCEPTION)\b', l)]
    ours = [l.strip() for l in out.splitlines() if re.search(r'ce_magnum|reach_dmr|reach_falcon|reach_revenant', l, re.I)]
    rep = dict(returncode=rc, seconds=round(time.time() - t), cache=str(cache), exists=cache.exists(),
               bytes=cache.stat().st_size if cache.exists() else 0, sha256=kit.sha(cache) if cache.exists() else None,
               error_lines=errors[:80], lines_mentioning_assets=ours[:120])
    (W / 'build-report.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k not in ('error_lines', 'lines_mentioning_assets')}))
    print('ERRORS', len(errors)); print('\n'.join(errors[:30]))
    print('ASSET LINES', len(ours)); print('\n'.join(ours[:40]))


if __name__ == '__main__':
    {'scenario': scenario, 'build': build}[sys.argv[1]]()
