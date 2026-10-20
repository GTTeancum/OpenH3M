"""Prepare and launch the converted map with confined, bounded diagnostic output."""
import argparse
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
import struct
import subprocess
import time

from build_scenario_checkpoint import file_hash, output_path, resource_salt
from cache_reader import Cache


def preflight(path, xex):
    with path.open('rb') as stream:
        header = bytearray(stream.read(0x3000))
    if len(header) != 0x3000:
        raise ValueError('Truncated map header')
    u = lambda at: struct.unpack_from('>I', header, at)[0]
    if u(8) != path.stat().st_size or u(0x2e8) + u(0x18) != 0xbfc00000:
        raise ValueError('Cache file size or tag memory boundary mismatch')
    stored = bytes(header[0x330:0x344])
    for start, length in ((0x320, 4), (0x328, 8), (0x330, 0x13c), (0x1c, 0x100),
                          (0x144, 8), (0x16c, 0x20), (0x49c, 0x10)):
        header[start:start + length] = bytes(length)
    if hashlib.sha1(resource_salt(xex) + header).digest() != stored:
        raise ValueError('Cache header authentication hash mismatch')
    cache = Cache(str(path))
    try:
        if sum(t['group'] == 'scnr' for t in cache.tags.values()) != 1:
            raise ValueError('Expected one scenario')
        return {'map': str(path), 'sha256': file_hash(path), 'tags': len(cache.tags),
                'header_hash': 'pass', 'tag_memory': 'pass'}
    finally:
        cache.close()


def prepare(project, game, converted, slot='lockout'):
    # Fresh deployment only: never overwrite the accepted candidate or a stock
    # hardlink. Links avoid duplicating large private assets in the repository.
    if game.exists():
        raise ValueError('Game directory already exists; choose a fresh --game path')
    inputs = [(converted, Path('maps') / (slot + '.map'))]
    for name in ('default.xex', 'WaveShell-Xbox.dll', 'WavesLibDLL.dll',
                 'maps/mainmenu.map', 'maps/shared.map'):
        path = project / name
        if not path.is_file():
            raise ValueError(f'Missing original disc input: {path}')
        inputs.append((path, Path(name)))
    for name in ('bink', 'waves', 'maps/fonts', 'maps/images', 'maps/info'):
        folder = project / name
        if folder.exists():
            for path in folder.rglob('*'):
                if path.is_file():
                    if not path.resolve().is_relative_to(project):
                        raise ValueError(f'Disc asset leaves project: {path}')
                    inputs.append((path, path.relative_to(project)))
    # Hardlinks require one volume. Validate before creating the layout.
    if any(path.resolve().drive.casefold() != game.drive.casefold() for path, _ in inputs):
        raise ValueError('Deployment inputs must share the project volume')
    for source, relative in inputs:
        target = output_path(game / relative, project)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
    return len(inputs)


def run(args, project, game, run_root, state):
    exe = args.exe.resolve(strict=True)
    existing = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {exe.name}', '/FO', 'CSV', '/NH'],
                              capture_output=True, text=True, check=True, timeout=15)
    if any(row and row[0].casefold() == exe.name.casefold() for row in csv.reader(existing.stdout.splitlines())):
        raise ValueError('Close the existing runtime before launching')
    env = os.environ.copy()
    for name in ('temp', 'profile', 'cache'):
        output_path(run_root / name, project).mkdir(exist_ok=True)
    cache_root = output_path(args.cache_root, project) if args.cache_root else run_root / 'cache'
    user_root = output_path(args.user_root, project) if args.user_root else run_root
    cache_root.mkdir(parents=True, exist_ok=True)
    user_root.mkdir(parents=True, exist_ok=True)
    if args.shader_cache_seed is not None:
        seed = output_path(args.shader_cache_seed, project).resolve(strict=True)
        shutil.copytree(seed, cache_root / 'shaders', dirs_exist_ok=True)
        state['shader_cache_seed'] = str(seed)
    profile_root = user_root / 'profile' if args.user_root else run_root / 'profile'
    profile_root.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(run_root / 'temp'), TMP=str(run_root / 'temp'),
               LOCALAPPDATA=str(profile_root), APPDATA=str(profile_root))
    command = [str(exe), f'--game_data_root={game}', f'--user_data_root={user_root}',
               f'--cache_root={cache_root}', f'--log_file={run_root / "runtime.log"}']
    state.update(executable=str(exe), executable_sha256=file_hash(exe), watchdog_seconds=args.seconds)
    if args.all_maps:
        print('Available maps: Blackout = Warlock; Last Resort = Resuscitation.', flush=True)
    print('Select Custom Games > ' + ('Blackout' if args.slot == 'lockout' else 'Last Resort') + ' > Slayer.', flush=True)
    print(f'Logs: {run_root}; watchdog: {args.seconds} seconds', flush=True)
    with (run_root / 'console.log').open('wb') as log:
        child = subprocess.Popen(command, cwd=run_root, env=env, stdout=log, stderr=log,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        state['pid'] = child.pid
        try:
            state['exit_code'] = child.wait(timeout=args.seconds)
            state['status'] = 'exited' if child.returncode == 0 else 'runtime_failed'
        except subprocess.TimeoutExpired:
            state['status'] = 'watchdog'
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
    # Keep a compact failure excerpt beside the full native log; no screenshots.
    excerpts = []
    for name in ('runtime.log', 'console.log'):
        path = run_root / name
        if path.exists():
            with path.open('rb') as stream:
                stream.seek(max(0, path.stat().st_size - 65536))
                lines = stream.read().decode('utf-8', errors='replace').splitlines()
            excerpts.extend(f'{name}: {line}' for line in lines
                            if any(word in line.lower() for word in ('error', 'fail', 'fatal', 'exception')))
    state['failure_excerpt'] = excerpts[-100:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'run'))
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--slot', choices=('lockout', 'zanzibar'), default='lockout')
    parser.add_argument('--map', type=Path)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--shader-cache-seed', type=Path)
    parser.add_argument('--cache-root', type=Path)
    parser.add_argument('--user-root', type=Path)
    parser.add_argument('--all-maps', action='store_true')
    parser.add_argument('--seconds', type=int, default=180)
    args = parser.parse_args()
    project = args.project.resolve(strict=True)
    game = output_path(args.game, project)
    if not 1 <= args.seconds <= 3600:
        parser.error('--seconds must be between 1 and 3600')
    run_root = output_path(project / '.local/warlock-runs' / (time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}'), project)
    run_root.mkdir(parents=True)
    state = {'action': args.action, 'status': 'starting', 'game': str(game)}
    try:
        if args.action == 'prepare':
            if args.map is None:
                raise ValueError('prepare requires --map')
            converted = output_path(args.map, project)
            state['preflight'] = preflight(converted, project / 'default.xex')
            state['linked_files'] = prepare(project, game, converted, args.slot)
            state['status'] = 'prepared'
        else:
            state['preflight'] = preflight(output_path(game / 'maps' / (args.slot + '.map'), project), project / 'default.xex')
            if args.all_maps:
                state['maps'] = {slot: preflight(output_path(game / 'maps' / (slot + '.map'), project), project / 'default.xex')
                                 for slot in ('lockout', 'zanzibar')}
            state['status'] = 'checked'
            if args.action == 'run':
                if args.exe is None:
                    raise ValueError('run requires --exe')
                run(args, project, game, run_root, state)
    except Exception as error:
        state.update(status='failed', error=str(error))
        raise
    finally:
        (run_root / 'result.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
        print(f'Report: {run_root / "result.json"}', flush=True)
    if state['status'] == 'runtime_failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
