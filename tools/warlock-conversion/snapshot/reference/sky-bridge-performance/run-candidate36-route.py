"""Bounded private movement timing with exact installed candidate36 binaries.

No images, host input, pose override, GPU probes, or shared installation writes.
Observer samples establish the extent of movement; they do not accept visuals.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='New private directory name, candidate36-route-NN')
    options = parser.parse_args()
    import re
    if not re.fullmatch(r'candidate36-route-\d{2}', options.name):
        parser.error('Use candidate36-route-NN')
    reference = Path(__file__).resolve().parent
    repo = reference.parents[4]
    if Path.cwd().resolve() != repo:
        raise SystemExit('Run with the repository as the working directory')
    record = json.loads((reference / 'candidate36-install-result.json').read_text())
    installed = Path(record['target']).resolve(strict=True)
    installed.relative_to(repo)
    payload = repo / 'work/sky-bridge/payload-36'
    for path in (installed, payload / 'sky_bridge.map'):
        if sha(path) != record['sha256']:
            raise SystemExit('Candidate36 map changed: ' + str(path))
    sources = {Path(name): digest for name, digest in record['runtime_hashes'].items()}
    for path, digest in sources.items():
        if sha(path) != digest:
            raise SystemExit('Installed runtime changed: ' + str(path))
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe',
                              '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True)
    if '"openh3m.exe"' in listing.stdout.lower():
        raise SystemExit('A game is already running')
    run = repo / 'work/sky-bridge' / options.name
    run.mkdir()  # Never reuse or overwrite existing evidence.
    (run / 'runtime').mkdir()
    for path, digest in sources.items():
        destination = run / 'runtime' / path.name
        shutil.copy2(path, destination)
        if sha(destination) != digest:
            raise SystemExit('Copied runtime hash mismatch')
    cache_seed = repo / 'work/sky-bridge/reproduction-29/cache'
    shutil.copytree(cache_seed, run / 'cache')
    hashes = {p.name: h for p, h in sources.items()}
    (run / 'runtime-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith('OPENH3M_SKY_')}
    env.update(TEMP=str(repo / '.local/build-temp'), TMP=str(repo / '.local/build-temp'),
               PYTHONDONTWRITEBYTECODE='1')
    (repo / '.local/build-temp').mkdir(exist_ok=True)
    # Retain the historical turn/walk durations but start after native loading
    # and early enough to finish inside the process watchdog. The replay clock
    # begins later than the process and presentation clocks. Observer samples
    # and actual input log timestamps establish coverage, not this schedule.
    route = ('110000:RSRIGHT+1600,114000:LSUP+1500,122000:LSUP+2000,'
             '128000:LSRIGHT+2000,134000:LSDOWN+2000')
    command = [sys.executable, '-B', str(reference / 'trace-route-observer.py'),
               '--project', 'C:/X360/ISOs/H3M', '--game', 'C:/X360/ISOs/H3M',
               '--exe', str(run / 'runtime/OpenH3M.exe'),
               '--expected-exe-sha256', hashes['OpenH3M.exe'],
               '--dlc-payload', str(payload), '--slot', 'zanzibar', '--dlc-map', 'sky_bridge',
               '--cache-root', str(run / 'cache'), '--exclusive-input', '--quiet-timing',
               '--seconds', '180', '--timing-diagnostics', '--sample-observer',
               '--inspection-input', route, '--profile-seed',
               str(repo / 'work/dlc/installed-corrections/4D5307E6/profile/User')]
    initial = dict(map_sha256=record['sha256'], runtime_hashes=hashes,
                   cache_seed=str(cache_seed.relative_to(repo)),
                   initial_cache={str(p.relative_to(cache_seed)): sha(p)
                                  for p in cache_seed.rglob('*') if p.is_file()},
                   command=command, watchdog_seconds=180, captures=False,
                   host_input=False, pose_override=False, gpu_probes=False,
                   purpose='Measure short-route movement and presentation pacing; no visual acceptance',
                   observer_reader='TLS+0x2cc/+0x110',
                   tool_hashes={p.name: sha(p) for p in (Path(__file__), reference / 'trace-route-observer.py',
                               repo / 'tools/warlock-conversion/snapshot/tools/trace_loading.py')})
    (run / 'preparation.json').write_text(json.dumps(initial, indent=2) + '\n')
    traces = repo / '.local/loading-traces'
    previous = set(traces.iterdir())
    print('Prepared ' + str(run), flush=True)
    with (run / 'runner.log').open('w') as output:
        result = subprocess.run(command, cwd=repo, env=env, stdout=output, stderr=subprocess.STDOUT)
    matches = []
    for trace in set(traces.iterdir()) - previous:
        launch = trace / 'launch-command.json'
        if launch.is_file() and json.loads(launch.read_text())[0] == str(run / 'runtime/OpenH3M.exe'):
            matches.append(trace)
    unchanged = {str(p): sha(p) == h for p, h in sources.items()}
    unchanged[str(installed)] = sha(installed) == record['sha256']
    report = dict(returncode=result.returncode, traces=[str(p.relative_to(repo)) for p in matches],
                  shared_unchanged=unchanged)
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if result.returncode or len(matches) != 1 or not all(unchanged.values()):
        raise SystemExit('Run incomplete or preservation check failed; inspect runner.log')


if __name__ == '__main__':
    main()
