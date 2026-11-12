"""Select installed maps and authored spawn points for native FPS measurements.

Examples: --list; --map chillout; --map sky_bridge --spawn 2; --all.
Map selection uses the existing process-local native menu route, never OS input.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from dlc_menu_route import menu_route
from script_input_replay import encode

INSTALL = Path('C:/X360/ISOs/H3M')
SETTINGS = tomllib.loads((INSTALL / 'OpenH3M.bootstrap.toml').read_text())
CONTENT = Path(SETTINGS['user_data_root'])
OUTPUT = ROOT / '.local/map-benchmarks'


def select_spawns(candidates, start_index=0):
    unique = []
    for p in candidates:
        if all(math.isfinite(v) for v in (*p['position'], p['yaw'])) and all(
                math.dist(p['position'], q['position']) > 1 for q in unique):
            unique.append(p)
    if len(unique) < 3:
        raise ValueError(f'Only {len(unique)} distinct authored starts found')
    selected = [unique[start_index % len(unique)]]
    while len(selected) < 3:
        selected.append(max((p for p in unique if p not in selected),
            key=lambda p: min(math.dist(p['position'], q['position']) for q in selected)))
    return selected, len(unique)


def spawn_points(path, start_index=0, multiplayer_only=False):
    cache = Cache(path)
    try:
        scenario = next(t['offset'] for t in cache.tags.values() if t['group'] == 'scnr')
        candidates = []
        for index, at in enumerate(cache.block(scenario + 0x254, 0x18)):
            xyz = cache.unpack('3f', at)
            yaw = cache.unpack('f', at + 12)[0]
            if not multiplayer_only:
                candidates.append(dict(source='player_start', index=index, position=xyz, yaw=yaw))
        for block, palette, stride in ((0xBC, 0xC8, 0xB4), (0x5E8, 0x5F4, 0xB0)):
            palette_names = [cache.name(cache.u(at + 12) & 65535) or ''
                             for at in cache.block(scenario + palette, 0x30)]
            for index, at in enumerate(cache.block(scenario + block, stride)):
                entry = cache.unpack('h', at)[0]
                if not 0 <= entry < len(palette_names):
                    continue
                name = palette_names[entry]
                if not any(s in name.lower() for s in ('respawn_point', 'initial_spawn_point', 'starting_point')):
                    continue
                xyz = cache.unpack('3f', at + 8)
                yaw = cache.unpack('f', at + 20)[0]
                candidates.append(dict(source=name, index=index, position=xyz, yaw=yaw))
        # Empty Forge canvases ship one start. These additional benchmark-only
        # positions are provisional until native collision settles the player
        # and camera checks plus captures confirm each location. No cache edit.
        if path.stem in ('forge_gulch', 'forge_island') and candidates:
            first = candidates[0]
            if all(math.dist(p['position'], first['position']) <= 1 for p in candidates):
                x, y, z = first['position']
                # Force Cove's east offset respawns the player at the original
                # marker. Retry the midpoint between two proven north/south
                # ground positions; native validation remains mandatory.
                offsets = ((0, 2), (0, 4)) if path.stem == 'forge_island' else ((4, 0), (0, 4))
                for index, (dx, dy) in enumerate(offsets, 1):
                    candidates.append(dict(source='provisional_offset_from_authored_start',
                        index=index, position=(x+dx, y+dy, z), yaw=first['yaw']))
        return select_spawns(candidates, start_index)
    finally:
        cache.close()


def inventory(start_index=0, multiplayer_only=False):
    rows = {}
    metadata = list((INSTALL / 'maps/info').glob('*.mapinfo')) + list(CONTENT.rglob('*.mapinfo'))
    for info in metadata:
        data = info.read_bytes()
        if data[0x30:0x34] != b'levl' or not struct.unpack_from('>I', data, 0x40)[0] & 0x40:
            continue
        name = data[0x1044:0x1144].split(b'\0')[0].decode('ascii')
        title = data[0x44:0x84].decode('utf-16-be').split('\0')[0]
        cache = info.parent / (name + '.map')
        if not cache.exists():
            cache = INSTALL / 'maps' / (name + '.map')
        row = dict(name=name, title=title, path=str(cache), metadata=str(info),
                   map_id=struct.unpack_from('>I', data, 0x3C)[0])
        try:
            row['spawns'], row['available_spawns'] = spawn_points(cache, start_index, multiplayer_only)
        except Exception as error:
            row['error'] = str(error)
        rows[name] = row
    bases = {r['map_id']: r for r in rows.values()}
    variants = []
    for saved in CONTENT.glob('*/4D5307E6/00000001/usermap*/sandbox.map'):
        data = saved.read_bytes()
        at = data.find(b'mapv')
        if at < 0:
            continue
        body = data[at+16:at+16+0xE090]
        if len(body) != 0xE090 or struct.unpack_from('>H', body, 0xF8)[0] != 12:
            continue
        base = bases.get(struct.unpack_from('>I', body, 0x100)[0])
        if base is None:
            continue
        title = body[8:40].decode('utf-16-be').split('\0')[0]
        row = dict(name=base['name'] + ':' + title.lower().replace(' ', '_'),
                   base_map=base['name'], title=title, variant=title,
                   path=base['path'], saved_layout=str(saved), map_id=base['map_id'])
        cache = Cache(Path(base['path']))
        try:
            candidates = []
            count = struct.unpack_from('>H', body, 0xFC)[0]
            for index in range(count):
                pos = 0x130 + index*84
                flags = struct.unpack_from('>H', body, pos)[0]
                quota = struct.unpack_from('>i', body, pos+12)[0]
                if not flags & 1 or flags & 8 or not 0 <= quota < 256:
                    continue
                datum = struct.unpack_from('>I', body, 0xD34C+quota*12)[0]
                name = cache.name(datum & 65535) or ''
                if not any(s in name.lower() for s in ('respawn_point', 'initial_spawn_point', 'starting_point')):
                    continue
                xyz = struct.unpack_from('>3f', body, pos+16)
                forward = struct.unpack_from('>3f', body, pos+28)
                candidates.append(dict(source=name, index=index, position=xyz,
                                       yaw=math.atan2(forward[1], forward[0])))
            row['spawns'], row['available_spawns'] = select_spawns(candidates, start_index)
        except Exception as error:
            row['error'] = str(error)
        finally:
            cache.close()
        variants.append(row)
    for row in variants:
        siblings = sorted((r['variant'] for r in variants if r['base_map'] == row['base_map']), key=str.casefold)
        row['variant_menu_index'] = siblings.index(row['variant']) + 1
        rows[row['name']] = row
    return sorted(rows.values(), key=lambda x: x['title'].casefold())


def parse_results(run):
    path = run / 'runtime.log'
    if not path.exists():
        return []
    results = []
    for line in path.read_text(errors='replace').splitlines():
        m = re.search(r'RESULT map=(\S+) point=(\d+) frames=(\d+) seconds=([\d.]+) fps=([\d.]+) valid=(\w+) camera=(.*)', line)
        if m:
            results.append(dict(map=m[1], point=int(m[2]), frames=int(m[3]), seconds=float(m[4]),
                                fps=float(m[5]), position_valid=m[6] == 'true', camera=m[7],
                                screenshot=str(run / f'spawn-{m[2]}.png')))
    return results


def run_map(row, batch, args):
    run = batch / row['name'].replace(':', '-')
    run.mkdir(parents=True, exist_ok=False)
    if 'error' in row:
        report = dict(map=row['name'], status='inventory_failed', error=row['error'], results=[])
        (run / 'result.json').write_text(json.dumps(report, indent=2))
        return report
    chosen = row['spawns'] if args.spawn == 'all' else [row['spawns'][int(args.spawn)-1]]
    points = run / 'points.txt'
    points.write_text(''.join(' '.join(str(v) for v in (*p['position'], p['yaw'])) + '\n' for p in chosen))
    base_map = row.get('base_map', row['name'])
    direction, steps = menu_route(INSTALL / 'maps/info', (CONTENT,), None, base_map)
    script = ['45000:DOWN+50', '46000:A+50', '55000:UP+50', '56000:A+50']
    script += [f'{58000+n*700}:{direction}+50' for n in range(steps)]
    confirm = max(70000, 58000 + steps*700 + 500)
    delay = confirm - 70000
    script += [f'{confirm}:A+50']
    variant_steps = row.get('variant_menu_index', 0)
    script += [f'{confirm+1000+n*500}:DOWN+50' for n in range(variant_steps)]
    delay += max(0, variant_steps*500-500)
    script += [f'{72000+delay}:A+50', f'{74000+delay}:DOWN+50', f'{95000+delay}:A+50']
    replay = run / 'input.h3ir'
    replay.write_bytes(encode(script))
    settings = dict(SETTINGS)
    settings.update(fpsunlock=True, log_file=str(run / 'runtime.log'), log_max_file_size_mb=50,
                    halo3mp_benchmark_map=base_map, halo3mp_benchmark_points=str(points),
                    halo3mp_benchmark_seconds=args.seconds, halo3mp_dev_unlock_test=False,
                    halo3mp_capture_guest_output_times_ms=str((args.watchdog-10)*1000),
                    halo3mp_capture_guest_output_after_ms=0,
                    halo3mp_capture_guest_output_path=str(run/'watchdog.png'),
                    halo3mp_log_fps=True, input_state_replay=str(replay), keyboard_controller=False,
                    input_script_button_state=True, input_script_keystrokes=False,
                    input_script='', halo3mp_smoke_route='spawn-fps-benchmark')
    if row.get('variant'):
        settings['halo3mp_benchmark_variant'] = row['variant']
    for directory in ('temp', 'profile'):
        (run / directory).mkdir()
    env = dict(os.environ, TEMP=str(run/'temp'), TMP=str(run/'temp'),
               APPDATA=str(run/'profile'), LOCALAPPDATA=str(run/'profile'))
    command = [str(args.exe)] + [('--fpsunlock' if k == 'fpsunlock' and v else
        f'--{k}={str(v).lower() if isinstance(v, bool) else v}') for k,v in settings.items()]
    started = time.monotonic()
    print(f'START {row["title"]}: {run}', flush=True)
    with (run / 'console.log').open('wb') as console:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=console, stderr=console)
        (run / 'run.json').write_text(json.dumps(dict(pid=process.pid, command=command, map=row,
                    chosen_spawns=chosen, executable_sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest()), indent=2))
        try:
            while process.poll() is None and time.monotonic() - started < args.watchdog:
                time.sleep(2)
                log = run / 'runtime.log'
                if log.exists():
                    text = log.read_text(errors='replace')
                    if '[map-benchmark] COMPLETE' in text or '[map-benchmark] FAILED' in text:
                        break
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    results = parse_results(run)
    if args.spawn != 'all':
        for result in results:
            result['native_point'] = result['point']
            result['point'] = int(args.spawn)
    good = len(results) == len(chosen) and all(r['position_valid'] and Path(r['screenshot']).is_file() for r in results)
    report = dict(map=row['name'], title=row['title'], status='needs_visual_review' if good else 'failed',
                  results=results, elapsed_seconds=time.monotonic()-started, exit_code=process.returncode)
    if not good:
        log = run/'runtime.log'
        text = log.read_text(errors='replace') if log.exists() else ''
        failures = [line for line in text.splitlines() if '[map-benchmark] FAILED' in line]
        report['failure'] = failures[-1] if failures else (
            'Missing results or invalid native position; see runtime.log and any watchdog capture')
    (run / 'result.json').write_text(json.dumps(report, indent=2))
    print(f'END {row["title"]}: {report["status"]} {[r["fps"] for r in results]}', flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list', action='store_true')
    p.add_argument('--map', action='append', help='Internal installed map name; repeat to select several')
    p.add_argument('--all', action='store_true')
    p.add_argument('--spawn', choices=['all', '1', '2', '3'], default='all')
    p.add_argument('--start-index', type=int, default=0, help='Choose a different authored starting candidate, then select two spatially separated points')
    p.add_argument('--multiplayer-starts-only', action='store_true', help='Exclude scenario initial player positions; use placed multiplayer spawn markers')
    p.add_argument('--seconds', type=int, default=10)
    p.add_argument('--watchdog', type=int, default=210)
    p.add_argument('--exe', type=Path, default=INSTALL / 'OpenH3M.exe')
    args = p.parse_args()
    if not 5 <= args.seconds <= 60 or not 60 <= args.watchdog <= 420:
        p.error('Use 5-60 seconds per point and a 60-420 second watchdog')
    if args.start_index < 0:
        p.error('--start-index must be nonnegative')
    rows = inventory(args.start_index, args.multiplayer_starts_only)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'inventory.json').write_text(json.dumps(rows, indent=2))
    if args.list:
        for row in rows:
            kind = 'candidate positions (includes provisional offsets)' if any(
                p['source'].startswith('provisional_') for p in row.get('spawns', [])) else 'authored spawns'
            print(f'{row["name"]:24} {row["title"]:24} {row.get("error", str(row.get("available_spawns"))+" "+kind)}')
        print(f'{len(rows)} installed multiplayer maps/layouts')
        return
    selected = rows if args.all else [row for row in rows if row['name'] in (args.map or [])]
    if not selected or any(name not in {r['name'] for r in rows} for name in (args.map or [])):
        p.error('Select installed names with --map NAME or use --all; --list shows names')
    running = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(f'"{name}"' in running for name in ('openh3m.exe', 'halo3mp.exe')):
        p.error('Close the running game before starting this benchmark')
    batch = OUTPUT / time.strftime('%Y%m%d-%H%M%S')
    batch.mkdir()
    (batch/'inventory.json').write_text(json.dumps(rows, indent=2))
    if (OUTPUT/'machine.json').exists():
        (batch/'machine.json').write_bytes((OUTPUT/'machine.json').read_bytes())
    reports = []
    for row in selected:
        reports.append(run_map(row, batch, args))
        (batch/'results.json').write_text(json.dumps(reports, indent=2))
    with (batch/'results.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['map', 'spawn', 'FPS', 'seconds', 'position_valid', 'status'])
        for report in reports:
            for r in report['results']:
                writer.writerow([report['title'], r['point'], r['fps'], r['seconds'], r['position_valid'], report['status']])
    print(batch, flush=True)


if __name__ == '__main__':
    main()
