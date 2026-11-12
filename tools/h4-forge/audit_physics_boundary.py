"""Trace the H4 target-controller versus current H3 pose-write boundary."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
functions = {}
for game, address, number in [
    ('h4', '82452930', 2), ('h4', '8249B418', 222),
    ('h4', '82C01FB8', 239), ('h4', '82C023E8', 34),
    ('h3', '822837C8', 104), ('h3', '8232E8B8', 80), ('h3', '8232E698', 81),
    ('h3', '82629000', 4),
    ('h3', '82651968', 65), ('h3', '8265FD48', 46),
    ('h4', '82CD55F0', 93), ('h4', '82CD40A8', 158),
]:
    directory, prefix = ('work/h4-forge-research/generated', 'halo4') if game == 'h4' else ('halo3mp/generated/default', 'halo3mp')
    path = ROOT / directory / f'{prefix}_recomp.{number}.cpp'
    text = path.read_text(encoding='utf-8')
    marker = f'DEFINE_REX_FUNC(sub_{address}) {{'
    start = text.index(marker)
    body = (marker + text[start + len(marker):].split('DEFINE_REX_FUNC(', 1)[0]).strip()
    functions[f'{game}:{address}'] = {
        'file': str(path.relative_to(ROOT)), 'line': text.count('\n', 0, start) + 1,
        'sha256': hashlib.sha256(body.encode()).hexdigest(),
        'calls': re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)', body),
    }
path = ROOT / 'halo3mp/src/advanced_forge.cpp'
report = {
    'scope': 'Static integration boundary; no native collision or physics parity claim.',
    'functions': functions,
    'current_adapter_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'open': ['H3 equivalent of H4 physics target controller',
             'Indirect motion callbacks and collision-world behavior',
             'Per-mode held/release sequences and parented objects',
             'Native snap/detach/regrab tests'],
}
(ROOT / 'work/h4-forge-research/isolated/full-re-physics-boundary.json').write_text(
    json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(f'Recorded {len(functions)} original H4/H3 functions and current adapter hash.')
