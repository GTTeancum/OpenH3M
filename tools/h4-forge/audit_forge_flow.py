"""Index original H4 Forge callers without treating reachability as RE coverage."""
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'work/h4-forge-research/generated'
OUT = ROOT / 'work/h4-forge-research/isolated/full-re-callgraph.json'
SEEDS = ['sub_8244EED8', 'sub_82582178', 'sub_82582250', 'sub_82582AD0',
         'sub_82582610', 'sub_825826B0', 'sub_825812D0', 'sub_824500A8',
         'sub_82685EE0', 'sub_82685F38', 'sub_8268AE80', 'sub_8268B410',
         'sub_8268C340', 'sub_82449ED8', 'sub_82450E10', 'sub_82451250',
         'sub_82451500', 'sub_82452738', 'sub_822562A8', 'sub_82A26BE8']
functions = {}
callers = {}
field_references = []
dispatch_body = ''
for path in sorted(SOURCE.glob('halo4_recomp.*.cpp')):
    text = path.read_text()
    starts = list(re.finditer(r'^DEFINE_REX_FUNC\((\w+)\) \{', text, re.M))
    line = 1
    prior = 0
    for i, match in enumerate(starts):
        end = starts[i+1].start() if i+1 < len(starts) else len(text)
        body = text[match.start():end].strip()
        line += text.count('\n', prior, match.start())
        prior = match.start()
        name = match[1]
        if name == 'sub_824500A8':
            dispatch_body = body
        calls = sorted(set(re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)', body)))
        functions[name] = dict(file=path.name, line=line, calls=calls,
                               indirect='REX_CALL_INDIRECT' in body,
                               sha256=hashlib.sha256(body.encode()).hexdigest())
        for callee in calls:
            callers.setdefault(callee, []).append(name)
        refs = re.findall(r'// ([a-z]+ [^\n]*\b(?:1348|1352|1356)\(r\d+\))', body)
        if refs:
            field_references.append(dict(function=name, file=path.name, line=line,
                                         references=refs))

selected = set(SEEDS)
for _ in range(2):
    selected |= {caller for name in selected for caller in callers.get(name, [])}
report = dict(scope='Two caller levels around known roots; NOT complete Forge discovery or verification.',
              function_count=len(functions), seeds=SEEDS,
              functions={name:dict(functions[name],callers=sorted(callers.get(name,[])))
                         for name in sorted(selected) if name in functions},
              unresolved_seeds=sorted(set(SEEDS)-functions.keys()),
              unit_field_candidates=field_references)
# Cross-check every generated dispatch arm against the original decoded image,
# not merely against another generated listing. Event names still need tracing.
image = (ROOT/'work/h4-forge-research/h4-image.bin').read_bytes()
cases = re.findall(r'case (\d+):\s*goto loc_([0-9A-F]+);', dispatch_body)
assert len(cases) == 21
# Follow branch edges rather than slicing between table labels: shared tails can
# sit after a return or outside an arm's textual span (notably events 16/18).
instructions = []
labels = {}
for line in dispatch_body.splitlines():
    label = re.fullmatch(r'loc_([0-9A-F]+):', line.strip())
    if label:
        labels[int(label[1], 16)] = len(instructions)
    elif line.strip().startswith('// '):
        instructions.append(line.strip()[3:])

def reachable_calls(address):
    pending = [labels[address]]
    visited = set()
    calls = set()
    while pending:
        index = pending.pop()
        if index in visited or index >= len(instructions):
            continue
        visited.add(index)
        instruction = instructions[index]
        op = instruction.split()[0]
        target = re.search(r'0x([0-9a-f]+)$', instruction)
        target = int(target[1], 16) if target else None
        if op == 'bl':
            name = f'sub_{target:08X}'
            if name in functions:
                calls.add(name)
        elif op in ('blr', 'bctr'):
            continue
        elif op.startswith('b') and op != 'bctrl':
            if target in labels:
                pending.append(labels[target])
            if op == 'b':
                continue
        pending.append(index + 1)
    return sorted(calls)

dispatch = []
for number, label in cases:
    event = int(number)
    address = int(label, 16)
    original = struct.unpack_from('>I', image, 0x82450128-0x82000000+event*4)[0]
    assert original == address, (event, hex(original), hex(address))
    dispatch.append(dict(event=event, entry=hex(address),
                         direct_calls=reachable_calls(address),
                         meaning='unresolved unless separately documented'))
assert dispatch[18]['direct_calls'] == [], 'No-op event must not inherit unreachable calls'
assert 'sub_825826B0' in dispatch[16]['direct_calls'], 'Both visibility branches must remain reachable'
report['event_dispatch'] = dict(function='sub_824500A8', type_offset='0x108',
                                table='0x82450128', original_table_verified=True, cases=dispatch)
OUT.write_text(json.dumps(report,indent=2)+'\n')
print(f'Indexed {len(functions)} original functions; retained {len(report["functions"])} caller candidates.')
for name in SEEDS:
    print(name, 'callers:', ', '.join(sorted(callers.get(name, []))))
print('Offset matches are only candidates: register base identity must be traced before naming a field.')
print('Verified all 21 Forge event dispatch table entries against original image bytes.')
