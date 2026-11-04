"""Decode bounded native material/blend witnesses; no cross-run frame joins."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]


def analyze(run):
    run = run.resolve()
    run.relative_to(REPO/'work/sky-bridge')
    path = run/'native-blend.bin'
    data = path.read_bytes()
    header = struct.unpack_from('<8I', data)
    assert header[:4] == (0x424c5953, 1, 288, 100000)
    assert 32 <= len(data) <= 32+288*100000 and (len(data)-32) % 288 == 0
    frequency = header[4] | header[5] << 32
    rows = list(struct.iter_unpack('<72I', data[32:]))
    assert rows and [r[1] for r in rows] == list(range(1, len(rows)+1))
    t0 = min(r[2] | r[3] << 32 for r in rows)
    events = collections.Counter()
    groups = {}
    material_groups = {}
    stacks = collections.defaultdict(list)
    incomplete = []
    pairs = []
    for row in rows:
        event, sequence = row[:2]
        events[event] += 1
        assert event in range(1, 9)
        thread = row[4]
        if event % 2:
            stacks[thread].append(row)
        elif not stacks[thread] or stacks[thread][-1][0] != event-1:
            incomplete.append(sequence)
        else:
            before = stacks[thread].pop()
            pairs.append((before, row))
        if event == 1:
            key = row[22], row[23], row[24], row[34], row[35], row[33]
            g = material_groups.setdefault(key, dict(material_pointer=hex(row[22]),
                post_pointer=hex(row[23]), stage=row[24], template=hex(row[34]),
                post_mode=row[35], material_flags=hex(row[33]), count=0,
                post_words=[hex(v) for v in row[38:71]]))
            g['count'] += 1
    for before, after in pairs:
        key = (before[0], before[6], before[22], before[23], before[24],
               before[9] if before[0] != 1 else None,
               before[28], after[28], before[32], before[34], before[35])
        g = groups.setdefault(key, dict(event=before[0], caller=hex(before[6]),
            material_pointer=hex(before[22]), post_pointer=hex(before[23]),
            stage=before[24], argument=key[5], template=hex(before[34]),
            post_mode=before[35], bypass=before[32], before_blend=hex(before[28]),
            after_blend=hex(after[28]), count=0, frames=[], examples=[]))
        g['count'] += 1
        g['frames'].append(before[5])
        if len(g['examples']) < 2:
            g['examples'].append(dict(sequence=before[1], frame=before[5],
                seconds=((before[2] | before[3] << 32)-t0)/frequency,
                before=list(before), after=list(after)))
    flushes = [dict(sequence=b[1], frame=b[5], caller=hex(b[6]),
        base_register=hex(b[10]), source=hex(b[11]),
        mask=hex(b[9] | b[71] << 32),
        command_begin=hex(b[33]+4), command_end=hex(a[33]+4),
        device_blend=hex(b[28]), source_words=[hex(v) for v in b[38:71]])
        for b,a in pairs if b[0] == 7]
    report = dict(run=str(run.relative_to(REPO)), rows=len(rows), events=dict(events),
        seconds=(max(r[2] | r[3] << 32 for r in rows)-t0)/frequency,
        native_frame_range=[min(r[5] for r in rows), max(r[5] for r in rows)],
        state_read_failures=sum(not r[37] for r in rows),
        material_read_failures=sum(r[0] == 1 and not r[26] for r in rows),
        paired_calls=len(pairs), unpaired_exits=incomplete,
        unfinished_entries=[r[1] for stack in stacks.values() for r in stack],
        row_cap_reached=len(rows) == 100000,
        materials=list(material_groups.values()), groups=list(groups.values()), flushes=flushes,
        input_sha256=hashlib.sha256(data).hexdigest(),
        limitations=[
            'Native frame counter is a hook invocation counter, not the GPU trace frame ID.',
            'Guest calls can precede GPU execution; no exact CPU/GPU time join is inferred.',
            'Record limit can split the final call pair; unfinished calls are explicit.',
            'This trace reads state and preserves original call arguments/results.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'native-blend-analysis.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in
                     ('materials','groups','flushes','credit','limitations')}))
    selected = [g for g in report['groups'] if g['event'] in (3, 5) and
                int(g['template'], 16) & 65535 == 225]
    print(json.dumps([{k:v for k,v in g.items() if k not in ('examples','frames')}
                      for g in selected], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    analyze(parser.parse_args().run)
