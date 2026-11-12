"""Record original event handlers and producers; not runtime parity evidence."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'work/h4-forge-research'
LOCATIONS = {
    '82451680': 238, '82451750': 236, '82451800': 255,
    '822EF3D8': 102, '822D5908': 155, '825FECE0': 255,
    '823E7DD0': 167, '8244CAC8': 193, '8278CF20': 200,
    '82714570': 43,
    '825FFCE8': 81, '82600478': 148, '825FEDB0': 257,
    '821D6EE0': 94, '82603D88': 157,
}
records = {}
for address, number in LOCATIONS.items():
    path = RESEARCH / f'generated/halo4_recomp.{number}.cpp'
    text = path.read_text(encoding='utf-8')
    marker = f'DEFINE_REX_FUNC(sub_{address}) {{'
    start = text.index(marker)
    body = (marker + text[start + len(marker):].split('DEFINE_REX_FUNC(', 1)[0]).strip()
    records[address] = {
        'file': path.name, 'line': text.count('\n', 0, start) + 1,
        'sha256': hashlib.sha256(body.encode()).hexdigest(),
        'calls': re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)', body),
    }
image = (RESEARCH / 'h4-image.bin').read_bytes()
source_path_address = 0x8213A370
offset = source_path_address - 0x82000000
source_path = image[offset:image.index(b'\0', offset)].decode('ascii')
assert source_path.endswith('render\\forge_light_baker.cpp')
(RESEARCH / 'isolated/full-re-remaining-events.json').write_text(
    json.dumps({
        'scope': 'Static handler and producer provenance; no executed interaction proof.',
        'functions': records,
        'light_baker_source_path': {'address': hex(source_path_address), 'value': source_path},
        'open': ['Event 19 configuration names and property bindings',
                 'Light-baker render passes, atlas adapters and H3 implementation',
                 'Device action mapping and other duplicate producers',
                 'Native event replication and save persistence'],
    }, indent=2) + '\n', encoding='utf-8')
print(f'Recorded {len(records)} original event/producer functions.')
