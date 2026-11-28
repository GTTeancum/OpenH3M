"""Halo 2 sound scenery (ambient loops placed in the level) -> stock Halo 3 sound scenery in a Halo 3 Editing Kit
scenario, at the Halo 2 positions (TagEdit, .local/tombstone/tagedit). Halo 2 sounds have no Halo 3 copy; each type is
mapped to the stock Halo 3 sound scenery closest in kind (table below; binding asset policy: stock Halo 3 assets).
Run once per scenario (it appends). Usage: h2_sound_scenery_to_h3.py <h2 scenario.xml> <h3 scenario tag> [--dry-run]
"""
import json, re, sys
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\.local\tombstone\tagedit')

H2_TO_H3 = {
    # Beaver Creek's creek: Valhalla's creek rapids loop (stock Halo 3 multiplayer)
    'running_water': r'sound\levels\riverworld\sound_scenery\riverworld_rapids\riverworld_rapids.sound_scenery',
    # Elongation (2026-11-26): belts -> Longshore's conveyor loop; Bungie's computer sounds ship in Halo 3 under the
    # same names (020_base, bunkerworld); computer5 has no copy -> Guardian's computer beeps
    'elongation_belts': r'sound\levels\dlc\docks\sound_scenery\conveyor_under_floor\conveyor_under_floor.sound_scenery',
    'computer1': r'sound\levels\020_base\sound_scenery\computer1\computer1.sound_scenery',
    'computer2': r'sound\levels\020_base\sound_scenery\computer2\computer2.sound_scenery',
    'computer3': r'sound\levels\020_base\sound_scenery\computer3\computer3.sound_scenery',
    'computer4': r'sound\levels\020_base\sound_scenery\computer4\computer4.sound_scenery',
    'computer5': r'sound\levels\deadlock\sound_scenery\computer_beeps\computer_beeps.sound_scenery',
    'computer6': r'sound\levels\dlc\bunkerworld\sound_scenery\computer6\computer6.sound_scenery',
}


def blocks(xml, name):
    a = xml.find('\t<block name="%s">' % name)
    if a < 0: return []
    b = xml.index('\n\t</block>', a)
    return re.findall(r'<element index="\d+"[^>]*>(.*?)</element>', xml[a:b], re.S)


def field(el, name):
    m = re.search(r'<(?:field|tag_reference) name="%s" type="[^"]*">(.*?)</(?:field|tag_reference)>' % re.escape(name), el, re.S)
    return m.group(1).strip() if m else None


def main():
    xml = open(sys.argv[1], encoding='latin-1').read(); T = sys.argv[2]; dry = '--dry-run' in sys.argv
    pal_names = [field(e, 'name') or '' for e in blocks(xml, 'sound scenery palette')]
    ops = []; pal = {}; n = 0; uid = 5000; report = {}
    for el in blocks(xml, 'sound scenery'):
        m = re.search(r'<block_index name="[^"]*" type="type" index="(-?\d+)"', el) or re.search(r'index="(-?\d+)"', el)
        t = int(m.group(1)) if m else -1
        h2 = pal_names[t].split('\\')[-1] if 0 <= t < len(pal_names) else '?'
        if h2 not in H2_TO_H3: report['no stock mapping: ' + h2] = report.get('no stock mapping: ' + h2, 0) + 1; continue
        tag = H2_TO_H3[h2]
        if tag not in pal:
            pal[tag] = len(pal)
            ops.append({'op': 'add', 'tag': T, 'block': 'Block:sound scenery palette', 'count': 1})
            ops.append({'op': 'set', 'tag': T, 'field': 'Block:sound scenery palette[%d]/name' % pal[tag], 'value': tag})
        b = 'Block:sound scenery[%d]/' % n; o = b + 'Struct:object data[0]/'; uid += 1
        ops.append({'op': 'add', 'tag': T, 'block': 'Block:sound scenery', 'count': 1})
        ops.extend([{'op': 'set', 'tag': T, 'field': b + 'type', 'value': str(pal[tag])},
                    {'op': 'set', 'tag': T, 'field': o + 'position', 'value': field(el, 'position')},
                    {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/unique id', 'value': str(uid)},
                    {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/origin bsp index', 'value': '0'},
                    {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/type', 'value': 'sound_scenery'},
                    {'op': 'set', 'tag': T, 'field': o + 'Struct:object id[0]/source', 'value': 'editor'}])
        n += 1; report[h2] = report.get(h2, 0) + 1
    print(json.dumps(report, indent=1))
    if dry: print(len(ops), 'ops (dry run)'); return
    import te
    te.edit(ops, timeout=1200)
    print('applied', len(ops), 'ops')


main()
