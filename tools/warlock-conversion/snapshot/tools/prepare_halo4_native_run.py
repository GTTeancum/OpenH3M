"""Reuse the established private native test layout for a Haven candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from warlock_handoff import preflight, prepare

ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', type=int, required=True)
number = parser.parse_args().candidate
assert number > 0
run = ROOT / 'work/halo4-to-h3/haven' / ('native-run-' + str(number))
assert not run.exists(), 'Preserve prior run output'
seed = ROOT / 'work/sky-bridge/reproduction-61'
hashes = json.loads((seed / 'runtime-hashes.json').read_text(encoding='utf-8-sig'))
names = ['OpenH3M.exe', 'rexruntime.dll', 'rexgpu-xenos.dll', 'halo3mp_l360.dll',
         'halo3mp_q10.dll', 'halo3mp_waveshell-xbox.dll', 'halo3mp_waveslibdll.dll']
for name in names:
    assert hashlib.sha256((seed / 'runtime' / name).read_bytes()).hexdigest() == hashes[name], name
candidate = ROOT / '.local/haven' / ('candidate' + str(number)) / 'zanzibar.map'
disc = Path('C:/X360/ISOs/H3M')
proof = preflight(candidate, disc / 'default.xex')
run.mkdir()
for name in ('runtime', 'cache', 'temp', 'profile'):
    (run / name).mkdir()
for name in names:
    shutil.copyfile(seed / 'runtime' / name, run / 'runtime' / name)
proof['linked_files'] = prepare(disc, run / 'game', candidate, slot='zanzibar')
settings = {'game_data_root': run / 'game', 'user_data_root': run / 'profile',
            'cache_root': run / 'cache', 'log_file': run / 'bootstrap-runtime.log'}
lines = []
for line in (seed / 'runtime/OpenH3M.bootstrap.toml').read_text().splitlines():
    key = line.split('=', 1)[0].strip()
    if key in settings:
        line = key + ' = ' + json.dumps(settings[key].as_posix())
    lines.append(line)
(run / 'runtime/OpenH3M.bootstrap.toml').write_text('\n'.join(lines) + '\n')
shutil.copytree(seed / 'cache/shaders', run / 'cache/shaders')
proof.update(runtime_hashes={n: hashes[n] for n in names},
             source_policy='Read-only disc hardlinks; never edit linked files. All writable output is repository-local.',
             game=str(run / 'game'), shader_cache_seed=str(seed / 'cache/shaders'))
(run / 'preparation.json').write_text(json.dumps(proof, indent=2) + '\n')
print('PREPARED', run)
