"""Reach scenario (HREK tool export-tag-to-xml) -> stock Halo 3 gameplay in an H3EK scenario, through TagEdit
(official ManagedBlam). Like tools/map-review/speed-review/h2_gameplay_to_h3.py for Halo 2.

Now: scenario type multiplayer, a sky, Reach initial spawn points -> player starting locations, Reach respawn points
(visible and invisible) -> stock Halo 3 respawn point scenery. Weapons/equipment/game-mode objects: not yet.
Usage: reach_gameplay_to_h3.py <reach scenario.xml> <h3 scenario tag path> <h3 sky scenery> [--dry-run]"""
import json, re, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')

RESPAWN = r'objects\multi\spawning\respawn_point.scenery'
TEAM = {'neutral': 'neutral', 'red': 'defender', 'blue': 'attacker'}


def block(xml, name):
    s = xml.index('\n    <field name="%s" value=' % name)
    e = xml.find('\n    <field name=', s + 10)
    return re.findall(r'\n    <element index="\d+"[^>]*>(.*?)\n    </element>', xml[s:e], re.S)


def field(el, name):
    m = re.search(r'<field name="%s" value="([^"]*)"' % re.escape(name), el)
    return m.group(1) if m else None


def main():
    xml = open(sys.argv[1], encoding='utf-8', errors='replace').read(); T = sys.argv[2]; sky = sys.argv[3]
    ops = [{'op': 'set', 'tag': T, 'field': 'type', 'value': 'multiplayer'}]
    ops += [{'op': 'clear', 'tag': T, 'block': 'Block:skies'}, {'op': 'add', 'tag': T, 'block': 'Block:skies', 'count': 1},
            {'op': 'set', 'tag': T, 'field': 'Block:skies[0]/sky', 'value': sky}]
    pal_names = [field(e, 'name') for e in block(xml, 'scenery palette')]
    starts, respawns = [], []
    for el in block(xml, 'scenery'):
        kind = field(el, 'type'); pos = field(el, 'position'); yaw = float(field(el, 'rotation').split(',')[0])
        team = TEAM.get(field(el, 'owner team') or 'neutral', 'neutral')
        if kind == 'initial_spawn_point': starts.append((pos, yaw))
        if kind in ('respawn_point', 'respawn_point_invisible'): respawns.append((pos, yaw, team))
    ops.append({'op': 'clear', 'tag': T, 'block': 'Block:player starting locations'})
    for i, (pos, yaw) in enumerate(starts):
        ops += [{'op': 'add', 'tag': T, 'block': 'Block:player starting locations', 'count': 1},
                {'op': 'set', 'tag': T, 'field': 'Block:player starting locations[%d]/position' % i, 'value': pos},
                {'op': 'set', 'tag': T, 'field': 'Block:player starting locations[%d]/facing' % i, 'value': '%.4f' % yaw}]
    ops += [{'op': 'clear', 'tag': T, 'block': 'Block:scenery'}, {'op': 'clear', 'tag': T, 'block': 'Block:scenery palette'},
            {'op': 'add', 'tag': T, 'block': 'Block:scenery palette', 'count': 1},
            {'op': 'set', 'tag': T, 'field': 'Block:scenery palette[0]/name', 'value': RESPAWN}]
    for i, (pos, yaw, team) in enumerate(respawns):
        b = 'Block:scenery[%d]/' % i; o = b + 'Struct:object data[0]/'; m = b + 'Struct:multiplayer data[0]/'
        ops += [{'op': 'add', 'tag': T, 'block': 'Block:scenery', 'count': 1},
                {'op': 'set', 'tag': T, 'field': b + 'type', 'value': '0'},
                {'op': 'set', 'tag': T, 'field': o + 'position', 'value': pos},
                {'op': 'set', 'tag': T, 'field': o + 'rotation', 'value': '%.4f,0,0' % yaw},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/unique id', 'value': str(5000 + i)},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/origin bsp index', 'value': '0'},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/type', 'value': 'scenery'},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/source', 'value': 'editor'},
                {'op': 'set', 'tag': T, 'field': m + 'owner team', 'value': team}]
    print(json.dumps(dict(starts=len(starts), respawns=len(respawns), palette=pal_names)))
    if '--dry-run' in sys.argv: print(len(ops), 'ops'); return
    import te
    for k in range(0, len(ops), 400): te.edit(ops[k:k + 400], timeout=1200)
    print('applied', len(ops), 'ops')


main()
