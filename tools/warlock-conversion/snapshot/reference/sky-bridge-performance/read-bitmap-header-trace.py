"""Check native bitmap construction/relocation events and saved GPU fetch headers."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

ref = Path(__file__).resolve().parent
repo = ref.parents[4]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('run', type=Path)
run = p.parse_args().run.resolve()
run.relative_to(repo/'work/sky-bridge')
groups = defaultdict(dict)
for raw in csv.DictReader((run/'bitmap-headers.csv').open()):
    row = {k: int(v) if k != 'event' else v for k,v in raw.items()}
    events = groups[row['sequence']]
    assert row['event'] not in events
    events[row['event']] = row
results = []
for sequence, events in groups.items():
    a, b = events['header_constructed'], events['interop_complete']
    expected = {'header_constructed', 'addresses_applied', 'interop_complete'}
    if not a['split']:
        expected.add('offset_applied')
    assert events.keys() == expected
    assert all(a[k] == b[k] for k in a if k not in ('event', 'arg4', 'arg5') and not k.startswith('word'))
    # Native relocation changes only the two address fields, preserving all
    # other texture-header bits. Compare before later material sampler setup.
    for i in range(13):
        mask = 0xfff if i in (8, 12) else 0xffffffff
        assert a[f'word{i}'] & mask == b[f'word{i}'] & mask
    address_event = events['addresses_applied']
    base_offset, mip_offset = a['word8'] & 0xfffff000, a['word12'] & 0xfffff000
    actual_base, actual_mip = b['word8'] & 0xfffff000, b['word12'] & 0xfffff000
    assert actual_base == (base_offset + address_event['arg4']) & 0xfffff000
    assert actual_mip == (mip_offset + address_event['arg5']) & 0xfffff000
    results.append({'sequence': sequence, 'dimensions': [a['width'], a['height']],
        'levels': a['levels'], 'split': bool(a['split']),
        'primary_bytes': a['primary_bytes'], 'secondary_bytes': a['secondary_bytes'],
        'primary_address': hex(a['primary_address']), 'secondary_address': hex(a['secondary_address']),
        'constructed_base_offset': hex(base_offset), 'constructed_mip_offset': hex(mip_offset),
        'address_arguments': [hex(address_event['arg4']), hex(address_event['arg5'])],
        'relocated_base': hex(actual_base), 'relocated_mip': hex(actual_mip),
        'min_lod': b['word11']>>2&15, 'max_lod': b['word11']>>6&15,
        'packed': bool(b['word12']>>11&1), 'events': list(events)})
screen = [r for r in results if r['dimensions']==[128,16] and r['levels']==8]
assert len(screen) == 1
screen, = screen
bindings = json.loads((run/'screen-binding-analysis.json').read_text())
states = [s for s in bindings['states'] if s['tag']==9772]
assert len(states) == 2 and {s['slot'] for s in states} == {0,2}
for s in states:
    assert int(s['base_address'],16) == int(screen['relocated_base'],16)&0x1ffff000
    assert int(s['mip_address'],16) == int(screen['relocated_mip'],16)&0x1ffff000
    assert (s['min_lod'],s['max_lod'],s['packed_mips']) == (screen['min_lod'],screen['max_lod'],screen['packed'])
result = {'records': len(results), 'events': sum(len(e) for e in groups.values()),
    'screen': screen, 'gpu_bindings_match_native_header': True,
    'other_small_texture_headers': [r for r in results if r['dimensions'] != [128,16] and min(r['dimensions'])<=16],
    'source_functions': {'82298970':'bitmap interop: choose generic offset or explicit addresses from descriptor byte47',
        '822987A8':'construct native header from descriptor, optional min LOD for absent secondary data',
        '826085A8':'generic relocation supplies no mip base when constructed mip offset is zero',
        '82097828':'apply explicit base and mip addresses when header contains multiple levels'},
    'trace_sha256': hashlib.sha256((run/'bitmap-headers.csv').read_bytes()).hexdigest(),
    'limitation':'Native header construction, relocation and subsequent GPU fetch identity only; no visual or performance verdict.'}
(run/'bitmap-header-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'records':len(results),'screen':screen,'gpu_bindings_match_native_header':True}))
