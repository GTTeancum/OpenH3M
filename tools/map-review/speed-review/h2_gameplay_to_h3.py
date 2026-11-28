"""Turn a Halo 2 multiplayer scenario's gameplay placements into stock Halo 3 ones in a Halo 3 Editing Kit scenario.

Reads the Halo 2 scenario XML (h2_export_xml.py) and writes TagEdit ops (.local/tombstone/tagedit, ManagedBlam) that add:
  * player starting locations + stock respawn points (objects\\multi\\spawning\\respawn_point) at each Halo 2 start
  * netgame equipment -> stock Halo 3 weapons / grenades / powerups (table below), Halo 2 spawn time kept
  * netgame flags -> stock Halo 3 game-mode objects: CTF flag spawn/return, oddball spawn, assault bomb spawn/goal,
    territories, teleporter sender/receiver (channel = Halo 2 identifier); each King of the Hill hill (Halo 2: a set of
    boundary points per hill) becomes one hill at the points' centre, radius covering them
  * Halo 2 scenery that is a stock multiplayer object (2-way teleporter, flag base) -> its stock Halo 3 counterpart
Teams: Halo 2 Alpha -> Halo 3 defender (red), Bravo -> attacker (blue), neutral -> neutral (as stock Zanzibar).
Gameplay objects are stock Halo 3 (binding asset policy); only positions and settings come from Halo 2.
Usage: h2_gameplay_to_h3.py <h2 scenario.xml> <h3 scenario tag, e.g. levels\\test\\beavercreek\\beavercreek.scenario> [--dry-run]
"""
import json, math, re, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')

H2_TO_H3_ITEM = {
    'battle_rifle': ('weapon', r'objects\weapons\rifle\battle_rifle\battle_rifle.weapon'),
    'smg': ('weapon', r'objects\weapons\rifle\smg\smg.weapon'),
    'magnum': ('weapon', r'objects\weapons\pistol\magnum\magnum.weapon'),
    'needler': ('weapon', r'objects\weapons\pistol\needler\needler.weapon'),
    'plasma_pistol': ('weapon', r'objects\weapons\pistol\plasma_pistol\plasma_pistol.weapon'),
    'plasma_rifle': ('weapon', r'objects\weapons\rifle\plasma_rifle\plasma_rifle.weapon'),
    'shotgun': ('weapon', r'objects\weapons\rifle\shotgun\shotgun.weapon'),
    'sniper_rifle': ('weapon', r'objects\weapons\rifle\sniper_rifle\sniper_rifle.weapon'),
    'rocket_launcher': ('weapon', r'objects\weapons\support_high\rocket_launcher\rocket_launcher.weapon'),
    'energy_sword': ('weapon', r'objects\weapons\melee\energy_blade\energy_blade.weapon'),
    'brute_shot': ('weapon', r'objects\weapons\support_low\brute_shot\brute_shot.weapon'),
    'beam_rifle': ('weapon', r'objects\weapons\rifle\beam_rifle\beam_rifle.weapon'),
    'carbine': ('weapon', r'objects\weapons\rifle\covenant_carbine\covenant_carbine.weapon'),
    'covenant_carbine': ('weapon', r'objects\weapons\rifle\covenant_carbine\covenant_carbine.weapon'),
    'frag_grenades': ('equipment', r'objects\weapons\grenade\frag_grenade\frag_grenade.equipment'),
    'plasma_grenades': ('equipment', r'objects\weapons\grenade\plasma_grenade\plasma_grenade.equipment'),
    'powerup_super_shield': ('equipment', r'objects\multi\powerups\powerup_blue\powerup_blue.equipment'),   # overshield
    'powerup_invisibility': ('equipment', r'objects\multi\powerups\powerup_yellow\powerup_yellow.equipment'),   # camo
}
FLAG_TO_H3 = {   # Halo 2 netgame flag type -> stock Halo 3 crate
    'CTF flag spawn': r'objects\multi\ctf\ctf_flag_spawn_point.crate',
    'CTF flag return': r'objects\multi\ctf\ctf_flag_return_area.crate',
    'Oddball spawn': r'objects\multi\oddball\oddball_ball_spawn_point.crate',
    'Assault bomb spawn': r'objects\multi\assault\assault_bomb_spawn_point.crate',
    'Assault bomb return': r'objects\multi\assault\assault_bomb_goal_area.crate',
    'Territories flag': r'objects\multi\territories\territory_static.crate',
    'Teleporter (src)': r'objects\multi\teleporter_sender\teleporter_sender.crate',
    'Teleporter (dest)': r'objects\multi\teleporter_reciever\teleporter_reciever.crate',
}
KOTH = r'objects\multi\koth\koth_hill_static.crate'
TWO_WAY = r'objects\multi\teleporter_2way\teleporter_2way.crate'
CHANNELS = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf', 'hotel', 'india', 'juliet']
SCENERY_TO_H3 = {   # Halo 2 multiplayer scenery -> stock Halo 3 crate. Empty for now: Halo 2's 2-way teleporter and flag base
}                   # scenery are only bases; Halo 3's sender/receiver and flag spawn objects carry their own models
RESPAWN = r'objects\multi\spawning\respawn_point.scenery'
TEAM = {'0': 'defender', '1': 'attacker'}


def blocks(xml, name):
    a = xml.find('\t<block name="%s">' % name)
    if a < 0: return []
    b = xml.index('\n\t</block>', a)
    return re.findall(r'<element index="\d+"[^>]*>(.*?)</element>', xml[a:b], re.S)


def field(el, name):
    m = re.search(r'<(?:field|tag_reference) name="%s" type="[^"]*">(.*?)</(?:field|tag_reference)>' % re.escape(name), el, re.S)
    return m.group(1).strip() if m else None


def index(el, typ):
    m = re.search(r'<block_index name="[^"]*" type="%s" index="(-?\d+)"' % re.escape(typ), el)
    return int(m.group(1)) if m else -1


def main():
    xml = open(sys.argv[1], encoding='latin-1').read(); T = sys.argv[2]; dry = '--dry-run' in sys.argv
    ops = []; pal = {}; count = {}; uid = [3000]
    def palette(kind, tag):
        key = (kind, tag)
        if key not in pal:
            i = sum(1 for k in pal if k[0] == kind); pal[key] = i
            ops.append({'op': 'add', 'tag': T, 'block': 'Block:%s palette' % kind, 'count': 1})
            ops.append({'op': 'set', 'tag': T, 'field': 'Block:%s palette[%d]/name' % (kind, i), 'value': tag})
        return pal[key]
    def place(kind, tag, pos, yaw=0.0, team='neutral', spawn_time=0, order=0, radius=None, channel=None, otype=None):
        blk = {'scenery': 'scenery', 'crate': 'crates', 'weapon': 'weapons', 'equipment': 'equipment'}[kind]
        p = palette(kind, tag); i = count.get(blk, 0); count[blk] = i + 1; uid[0] += 1
        b = 'Block:%s[%d]/' % (blk, i); o = b + 'Struct:object data[0]/'; m = b + 'Struct:multiplayer data[0]/'
        ops.append({'op': 'add', 'tag': T, 'block': 'Block:' + blk, 'count': 1})
        ops.extend([{'op': 'set', 'tag': T, 'field': b + 'type', 'value': str(p)},
                {'op': 'set', 'tag': T, 'field': o + 'position', 'value': '%.6f,%.6f,%.6f' % pos},
                {'op': 'set', 'tag': T, 'field': o + 'rotation', 'value': '%.4f,0,0' % yaw},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/unique id', 'value': str(uid[0])},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/origin bsp index', 'value': '0'},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/type', 'value': otype or kind.replace('crate', 'crate')},
                {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/source', 'value': 'editor'},
                {'op': 'set', 'tag': T, 'field': m + 'owner team', 'value': team},
                {'op': 'set', 'tag': T, 'field': m + 'spawn order', 'value': str(order)}])
        if spawn_time: ops.append({'op': 'set', 'tag': T, 'field': m + 'spawn time', 'value': str(spawn_time)})
        if radius is not None: ops.append({'op': 'set', 'tag': T, 'field': m + 'boundary width or radius', 'value': '%.3f' % radius})
        if channel is not None: ops.append({'op': 'set', 'tag': T, 'field': m + 'teleporter channel', 'value': channel})
    report = {}
    def tally(k): report[k] = report.get(k, 0) + 1
    def P(text): return tuple(float(v) for v in text.split(','))

    # starting locations + respawn points
    seen = set()
    for el in blocks(xml, 'player starting locations'):
        pos, facing = field(el, 'position'), field(el, 'facing')
        if (pos, facing) in seen: continue
        seen.add((pos, facing)); i = len(seen) - 1
        ops.append({'op': 'add', 'tag': T, 'block': 'Block:player starting locations', 'count': 1})
        ops.append({'op': 'set', 'tag': T, 'field': 'Block:player starting locations[%d]/position' % i, 'value': pos})
        ops.append({'op': 'set', 'tag': T, 'field': 'Block:player starting locations[%d]/facing' % i, 'value': facing})
        place('scenery', RESPAWN, P(pos), float(facing)); tally('respawn points')
    # weapons / grenades / powerups
    for el in blocks(xml, 'netgame equipment'):
        item = (field(el, 'item/vehicle collection') or field(el, 'item collection') or '').split('\\')[-1]
        if not item:
            m = re.search(r'type="tag reference">([^<]*)<', el); item = (m.group(1) if m else '').split('\\')[-1]
        item = item.split(',')[-1].strip()
        if item not in H2_TO_H3_ITEM: tally('equipment without a stock mapping: ' + item); continue
        kind, tag = H2_TO_H3_ITEM[item]
        ori = (field(el, 'orientation') or '0,0,0').split(',')
        st = int(float(field(el, 'spawn time (in seconds, 0 = default)') or 0))
        place(kind, tag, P(field(el, 'position')), float(ori[0]), spawn_time=st); tally(item)
    # game-mode flags
    hills = {}
    # Halo 2 two-way pads: a 2way_teleporter scenery with a sender flag on it and a receiver flag beside it. The
    # pads are linked by the flags' identifiers. Each pad becomes ONE stock Halo 3 two-way teleporter at the Halo 2 pad's
    # own position (user, 2026-11-26), facing the receiver flag's facing, i.e. Halo 2's exit direction; linked pads share a channel. Separate
    # Halo 3 sender + receiver crates 0.75 units apart overlap visually and bounce arrivals back (Beaver Creek, 2026-11-26).
    sc_pal_all = [field(e, 'name') for e in blocks(xml, 'scenery palette')]
    pads = [P(field(e, 'position')) for e in blocks(xml, 'scenery')
            if 0 <= index(e, 'type') < len(sc_pal_all) and (sc_pal_all[index(e, 'type')] or '').endswith('2way_teleporter')]
    tflags = [(typ, P(field(el, 'position')), float(field(el, 'facing') or 0), int(field(el, 'identifier') or 0))
              for el in blocks(xml, 'netgame flags') for typ in [(field(el, 'type') or '').split(',', 1)[-1]]
              if typ.startswith('Teleporter')]
    def pad_of(pos): return next((k for k, q in enumerate(pads) if math.hypot(pos[0] - q[0], pos[1] - q[1]) < 1.5), None)
    two_way = {}   # pad index -> (sender position, exit facing, channel identifier)
    if pads and all(pad_of(p) is not None for _, p, _, _ in tflags):
        exits = {pad_of(p): f for t, p, f, _ in tflags if t == 'Teleporter (dest)'}
        links = {}
        for t, p, f, i in tflags:
            links.setdefault(i, {})[t] = pad_of(p)
        group = {}
        for i, l in sorted(links.items()):
            a, b = l.get('Teleporter (src)'), l.get('Teleporter (dest)')
            if a is None or b is None: continue
            g = group.get(a, group.get(b, len(set(group.values()))))
            group[a] = group[b] = g
        for t, p, f, i in tflags:
            if t == 'Teleporter (src)' and pad_of(p) in group:
                two_way[pad_of(p)] = (pads[pad_of(p)], exits.get(pad_of(p), f), group[pad_of(p)])
    for k, (p, f, g) in sorted(two_way.items()):
        place('crate', TWO_WAY, p, f, channel=CHANNELS[g % 10]); tally('Halo 2 two-way pad -> stock two-way teleporter')
    for el in blocks(xml, 'netgame flags'):
        typ = (field(el, 'type') or '').split(',', 1)[-1]; pos = P(field(el, 'position'))
        team = TEAM.get((field(el, 'team designator') or '').split(',')[0], 'neutral'); ident = int(field(el, 'identifier') or 0)
        if typ.startswith('Teleporter') and pad_of(pos) in two_way: continue
        if typ.startswith('King Hill'): hills.setdefault(int(typ.split()[-1]), []).append(pos); continue
        if typ not in FLAG_TO_H3: tally('flag type without a stock mapping: ' + typ); continue
        tag = FLAG_TO_H3[typ]
        chan = CHANNELS[ident % 10] if typ.startswith('Teleporter') else None
        place('crate', tag, pos, float(field(el, 'facing') or 0), team=team, order=ident if typ == 'Territories flag' else 0,
              radius=2.0 if typ == 'Territories flag' else None, channel=chan); tally(typ)
    for h, pts in sorted(hills.items()):
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts); cz = min(p[2] for p in pts)
        r = max(math.hypot(p[0] - cx, p[1] - cy) for p in pts)
        place('crate', KOTH, (cx, cy, cz), order=h, radius=max(1.5, r)); tally('King of the Hill hill (%d points)' % len(pts))
    # stock multiplayer scenery
    sc_pal = [field(e, 'name') for e in blocks(xml, 'scenery palette')]
    for el in blocks(xml, 'scenery'):
        t = index(el, 'type'); name = sc_pal[t] if 0 <= t < len(sc_pal) else None
        if name in SCENERY_TO_H3:
            rot = (field(el, 'rotation') or '0,0,0').split(',')
            place('crate', SCENERY_TO_H3[name], P(field(el, 'position')), float(rot[0])); tally(name.split('\\')[-1])
    print(json.dumps(report, indent=1))
    if dry: print(len(ops), 'ops (dry run)'); return
    import te
    for k in range(0, len(ops), 400): te.edit(ops[k:k + 400], timeout=1200)
    print('applied', len(ops), 'ops')


main()
