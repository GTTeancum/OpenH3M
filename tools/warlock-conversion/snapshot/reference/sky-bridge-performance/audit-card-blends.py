"""Compare actual BSP material bindings and all source/target lightmap parts."""
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0, 'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache

source = Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map', True)
target = Cache('work/sky-bridge/zanzibar-29.map')
try:
    sbsp = source.tags[10471]['offset']
    source_materials = source.block(sbsp + 208, 36)
    tbsp, = [v['offset'] for v in target.tags.values() if v['group'] == 'sbsp'
             and target.u(v['offset'] + 192) == len(source_materials)]
    target_materials = target.block(tbsp + 192, 36)
    source_root, = [v['offset'] for v in source.tags.values() if v['group'] == 'Lbsp']
    target_root, = [row for v in target.tags.values() if v['group'] == 'sLdT'
                    for row in target.block(v['offset'] + 4, 0x1b4) if target.u(row + 0x134)]
    source_meshes = source.block(source_root + 0x134, 0x4c)
    target_meshes = target.block(target_root + 0x134, 0x4c)
    assert len(source_meshes) == len(target_meshes)
    usage = collections.defaultdict(list)
    checked = 0
    for mi, (sm, tm) in enumerate(zip(source_meshes, target_meshes)):
        sp, tp = source.block(sm, 16), target.block(tm, 16)
        assert len(sp) == len(tp)
        for pi, (a, b) in enumerate(zip(sp, tp)):
            values = source.unpack('hhHHhHBBH', a)
            assert values == target.unpack('hhHHhHBBH', b), (mi, pi)
            usage[values[0]].append(dict(mesh=mi, part=pi, part_type=values[6], flags=values[7]))
            checked += 1
    mismatches = {}
    for slot, (a, b) in enumerate(zip(source_materials, target_materials)):
        if not usage[slot]:
            continue
        sid, tid = source.u(a + 12) & 65535, target.u(b + 12) & 65535
        sp, = source.block(source.tags[sid]['offset'] + 40, 140)
        tp, = target.block(target.tags[tid]['offset'] + 40, 132)
        sb, tb = source.u(sp + 104), target.u(tp + 104)
        if sb == tb:
            continue
        entry = mismatches.setdefault(sid, dict(name=source.name(sid), source_id=sid,
            target_id=tid, source_blend=sb, target_blend=tb, parts=[],
            source_template=source.name(source.u(sp + 12) & 65535),
            target_template=target.name(target.u(tp + 12) & 65535)))
        entry['parts'].extend(usage[slot])
    report = dict(meshes_checked=len(source_meshes), exact_part_records=checked,
        mismatches=list(mismatches.values()),
        limitation='Material mismatches are established; screenshot-to-mesh assignment and visible correction remain unproven.')
    out = Path('work/sky-bridge/card-blend-audit.json')
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(meshes=len(source_meshes), exact_parts=checked,
                         mismatched_materials=len(mismatches),
                         affected_parts=sum(len(v['parts']) for v in mismatches.values())), indent=2))
finally:
    source.close()
    target.close()
