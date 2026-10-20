"""Compare serialized BSP material constants/animations to their authored source."""
import argparse
import json
from cache_reader import Cache
from string_ids import StringTable
from material_importer import MaterialImporter
from tag_functions import convert_function


def verify(source, target, report):
    ss, ts = StringTable(source), StringTable(target)
    sb = next(t['offset'] for t in source.tags.values() if t['group'] == 'sbsp')
    db = next(t['offset'] for t in target.tags.values() if t['group'] == 'sbsp')
    source_rows, target_rows = source.block(sb + 0xd0, 36), target.block(db + 0xc0, 36)
    assert len(source_rows) == len(target_rows), 'BSP material slot count changed'
    wanted = {m['source']: m for m in report['materials'] if m.get('native_material_template')}
    seen, constants, animations = set(), 0, 0
    for sr, dr in zip(source_rows, target_rows):
        si = source.u(sr + 12) & 65535
        name = source.name(si)
        if name not in wanted or name in seen:
            continue
        seen.add(name)
        st, dt = source.tags[si], target.tags[target.u(dr + 12) & 65535]
        sp = source.block(st['offset'] + 40, 140)[0]
        dp = target.block(dt['offset'] + 40, 132)[0]
        sn = MaterialImporter.parameters(None, source, ss, sp)[1]
        dn = MaterialImporter.parameters(None, target, ts, dp)[1]
        sc, dc = source.block(sp + 28, 16), target.block(dp + 28, 16)
        for index, parameter in enumerate(dn):
            if parameter in sn:
                assert source.unpack('4I', sc[sn.index(parameter)]) == target.unpack('4I', dc[index]), (name, parameter)
                constants += 1
            elif wanted[name].get('disabled_extra_environment') and parameter.startswith('env_tint'):
                assert target.unpack('4f', dc[index]) == (0., 0., 0., 0.), 'Added reflection was not disabled'
        for parameter in set(sn) - set(dn):
            assert parameter == 'bump_detail_coefficient', (name, parameter)
            assert source.unpack('4f', sc[sn.index(parameter)]) == (1., 1., 1., 1.)
        sa, da = source.block(sp + 92, 36), target.block(dp + 92, 36)
        assert len(sa) == len(da), (name, 'Animation count changed')
        for a, b in zip(sa, da):
            assert source.u(a) == target.u(b), 'Animation type changed'
            assert source.unpack('I', a + 12) == target.unpack('I', b + 12), 'Animation period changed'
            for offset in (4, 8):
                assert ss.text(source.u(a + offset)) == ts.text(target.u(b + offset)), 'Animation input changed'
            size, ptr = source.u(a + 16), source.pointer(source.u(a + 28))
            converted = convert_function(bytes(source.data[ptr:ptr + size]))
            size, ptr = target.u(b + 16), target.pointer(target.u(b + 28))
            assert converted == target.data[ptr:ptr + size], 'Authored animation curve changed'
            animations += 1
    assert seen == set(wanted), 'Unverified native material'
    return {'materials': len(seen), 'float4_constants': constants, 'authored_animations': animations}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--map', required=True)
    p.add_argument('--report', required=True)
    a = p.parse_args()
    s, d = Cache(a.source, True), Cache(a.map)
    try:
        with open(a.report, encoding='utf-8') as stream:
            print(json.dumps(verify(s, d, json.load(stream))))
    finally:
        s.close()
        d.close()
