"""Join the last blend-register PM4 writes to byte-attributed model draws."""
import argparse
import array
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]


def analyze(run):
    run = run.resolve()
    run.relative_to(REPO/'work/sky-bridge')
    spec = importlib.util.spec_from_file_location('models', REF/'trace-model-draws.py')
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    calls = {c['sequence']:c for c in json.loads((run/'model-draw-calls.json').read_text())['calls']}
    registers = array.array('I', [0])*0x5003
    groups = {}
    evidence = []
    count = 0
    for kind, raw in model.packets(run/'draws.bin'):
        if kind == 1:
            sequence, frame, ns, vs, ps, *_ = struct.unpack('<11Q', raw)
            witness = None
        elif kind == 2:
            for i, v in struct.iter_unpack('<II', raw):
                registers[i] = v
        elif kind == 10:
            witness = struct.unpack('<82Q', raw)
            assert witness[:2] == (sequence, frame)
        elif kind == 5:
            assert witness is not None
            count += 1
            writes = [witness[18+i*16:34+i*16] for i in range(4)]
            assert writes[0][0] and writes[0][1] == registers[0x2201]
            call = calls[sequence]
            if call['candidates'] not in ([dict(owner=10177,mesh=0,part=0)],
                                          [dict(owner=10177,mesh=0,part=1)]):
                continue
            key = call['candidates'][0]['part'], ps, writes[0][1], writes[0][5]
            g = groups.setdefault(key, dict(part=key[0], ps=ps, blend=hex(key[2]),
                last_write_packet_header=hex(key[3]), draws=0, frames=[], examples=[]))
            g['draws'] += 1
            g['frames'].append(frame)
            row = dict(sequence=sequence, frame=frame, part=key[0], ps=ps,
                blend=hex(registers[0x2201]), draw_packet=[hex(v) for v in witness[2:18]],
                blend_writes=[dict(write_sequence=w[0], value=hex(w[1]),
                    packet_physical_address=hex(w[2]), remaining_bytes=w[3],
                    prefix_words=[hex(v) for v in w[5:5+w[4]]]) for w in writes])
            if len(g['examples']) < 2:
                g['examples'].append(row)
            if ps == 2673597551499054088:
                evidence.append(row)
    assert count == len(calls)
    result = dict(run=str(run.relative_to(REPO)), witnessed_draws=count,
        all_latest_writes_match_draw_register=True, groups=list(groups.values()),
        fabric_dynamic_draws=evidence,
        input_sha256=hashlib.sha256((run/'draws.bin').read_bytes()).hexdigest(),
        limitations=['Packet provenance identifies GPU-consumed commands, not their guest CPU caller.',
                     'Only four latest blend writes and eight words of each packet are retained.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'command-witness-analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(witnessed_draws=count, groups=[{k:v for k,v in g.items()
        if k not in ('examples', 'frames')} for g in groups.values()]), indent=2))
    if evidence:
        print(json.dumps(evidence[0], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    analyze(parser.parse_args().run)
