"""Compare authored sky animation functions with serialized retail output."""
import argparse
import json
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable
from tag_functions import convert_function

SKY = r"levels\multi\forge_halo\sky_halo\sky_halo"


def records(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from records(child)
    elif isinstance(value, list):
        for child in value:
            yield from records(child)


def audit(source_path, candidate_path, build_report):
    source, target = Cache(source_path, True), Cache(candidate_path)
    try:
        si = next(k for k, t in source.tags.items() if t['group'] == 'mode' and source.name(k) == SKY)
        matches = [r for r in records(build_report) if r.get('source') == SKY and r.get('group') == 'mode']
        if len(matches) != 1:
            raise ValueError('Expected one imported sky model')
        ti = int(matches[0]['datum'], 16) & 65535
        sm = source.block(source.tags[si]['offset']+0x48, 36)
        tm = target.block(target.tags[ti]['offset']+0x48, 36)
        if len(sm) != len(tm):
            raise ValueError('Sky material counts differ')
        ss, ts = StringTable(source), StringTable(target)
        result = []
        for sr, tr in zip(sm, tm):
            sk, tk = source.u(sr+12)&65535, target.u(tr+12)&65535
            sp = source.block(source.tags[sk]['offset']+40, 140)[0]
            tp = target.block(target.tags[tk]['offset']+40, 132)[0]
            sa, ta = source.block(sp+92, 36), target.block(tp+92, 36)
            if len(sa) != len(ta):
                raise ValueError('Animation count differs: '+source.name(sk))
            for a, b in zip(sa, ta):
                sv, tv = source.unpack('IIIf', a), target.unpack('IIIf', b)
                if (sv[0], ss.text(sv[1]), ss.text(sv[2]), sv[3]) != (tv[0], ts.text(tv[1]), ts.text(tv[2]), tv[3]):
                    raise ValueError('Animation semantics differ: '+source.name(sk))
                ap, bp = source.pointer(source.u(a+28)), target.pointer(target.u(b+28))
                raw = bytes(source.data[ap:ap+source.u(a+16)])
                actual = bytes(target.data[bp:bp+target.u(b+16)])
                if convert_function(raw) != actual:
                    raise ValueError('Animation function differs: '+source.name(sk))
            if not sa and any(target.u(tp+o) for o in (56,68,80,92)):
                raise ValueError('Unanimated source inherited donor routing')
            result.append({'material': source.name(sk), 'authored_functions':len(sa), 'candidate_functions':len(ta)})
        return result
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','candidate','build-report','report'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    result = audit(args.source, args.candidate, json.loads(args.build_report.read_text()))
    args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps({'materials':len(result),'authored_functions':sum(r['authored_functions'] for r in result)}))
