"""Join actual movement, native coordinates and painted-frame timing by clock."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import struct


def timestamp(line):
    return datetime.strptime(line[1:24], '%Y-%m-%d %H:%M:%S.%f').timestamp()


def fields(line):
    return dict(re.findall(r'(\w+)=([\w.\-]+)', line))


def window(points, start, end):
    selected = [p for p in points if start <= p['wall_time'] <= end]
    if len(selected) < 2:
        return dict(status='insufficient samples', frames=len(selected))
    gaps = [b['elapsed_ms'] - a['elapsed_ms'] for a, b in zip(selected, selected[1:])]
    skipped = sum(max(0, b['frame'] - a['frame'] - 1) for a, b in zip(selected, selected[1:]))
    ordered = sorted(gaps)
    return dict(frames=len(selected), span_seconds=(selected[-1]['elapsed_ms']-selected[0]['elapsed_ms'])/1000,
                first_elapsed_ms=selected[0]['elapsed_ms'], last_elapsed_ms=selected[-1]['elapsed_ms'],
                fps=(selected[-1]['frame']-selected[0]['frame'])*1000 /
                    (selected[-1]['elapsed_ms']-selected[0]['elapsed_ms']),
                median_ms=statistics.median(gaps), p95_ms=ordered[int(.95*(len(ordered)-1))],
                maximum_ms=max(gaps), over_50ms=sum(x>50 for x in gaps),
                skipped_frame_numbers=skipped,
                interval_scope='Distinct guest_painted transitions; repeated host presents excluded')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    options = parser.parse_args()
    ref = Path(__file__).resolve().parent
    repo = ref.parents[4]
    run = options.run.resolve(strict=True)
    run.relative_to(repo / 'work/sky-bridge')
    result = json.loads((run / 'result.json').read_text())
    if result['returncode'] or len(result['traces']) != 1:
        raise SystemExit('Run did not complete normally under the watchdog')
    log = repo / result['traces'][0]
    preparation = json.loads((run / 'preparation.json').read_text())
    command = preparation['command']
    requested = command[command.index('--inspection-input')+1].split(',')
    if '--walk-check' in command:
        requested = ['120000:RSRIGHT+1600', '124000:LSUP+1500'] + requested
    clock = json.loads((log/'launch-clock.json').read_text())
    lines = sorted(line for path in log.glob('*runtime*.log')
                   for line in path.read_text(errors='replace').splitlines())
    points, inputs = [], []
    for line in lines:
        if '[host-present]' in line:
            f = fields(line)
            point = dict(wall_time=timestamp(line), elapsed_ms=float(f['elapsed_ms']),
                         frame=int(f['guest_painted']))
            if not points or point['frame'] != points[-1]['frame']:
                if points and (point['frame'] < points[-1]['frame'] or point['elapsed_ms'] <= points[-1]['elapsed_ms']):
                    raise ValueError('Nonmonotonic presentation trace')
                points.append(point)
        if '[input-replay]' in line:
            f = fields(line)
            if 't' not in f:  # Initial enabled/loaded message, not an input edge.
                continue
            inputs.append(dict(wall_time=timestamp(line), replay_ms=int(f['t'].removesuffix('ms')),
                               state={k:int(f[k]) for k in ('buttons','lx','ly','rx','ry','lt','rt')}))
    if not points:
        raise SystemExit('No painted-frame timing')
    steps=[]
    for step in requested:
        start, button, duration = re.fullmatch(r'(\d+):([A-Z]+)\+(\d+)', step).groups()
        start, duration = int(start), int(duration)
        begin = next((r for r in inputs if 0 <= r['replay_ms']-start < 100), None)
        end = next((r for r in inputs if 0 <= r['replay_ms']-start-duration < 100), None)
        steps.append(dict(request=step, begin=begin, end=end, completed=bool(begin and end)))
    began = [s['begin']['wall_time'] for s in steps if s['begin']]
    ended = [s['end']['wall_time'] for s in steps if s['end']]
    if not began or not ended:
        raise SystemExit('No completed movement interval')
    route_start, route_end = min(began), max(ended)+2
    events = [json.loads(line) for line in (log/'loading-trace.jsonl').read_text().splitlines()]
    observations = [r for r in events if r['event']=='observer_position'
                    and route_start-clock['wall_time']-1 <= r['seconds'] <= route_end-clock['wall_time']+1]
    for r in observations:
        if not all(math.isfinite(x) for x in r['position']+r['forward']):
            raise ValueError('Nonfinite camera')
        if not .99 < math.sqrt(sum(x*x for x in r['forward'])) < 1.01:
            raise ValueError('Invalid camera basis')
        bsp, cluster, leaf = struct.unpack('>BBH',bytes.fromhex(r['location']))
        r['decoded_location']=dict(bsp=bsp,cluster=cluster,leaf=leaf)
    if len(observations)<2:
        raise SystemExit('Insufficient observer coverage')
    distance = sum(math.dist(a['position'],b['position']) for a,b in zip(observations,observations[1:]))
    offsets = [(p['wall_time']-clock['wall_time'])*1000-p['elapsed_ms'] for p in points]
    offset = statistics.median(offsets)
    report=dict(run=str(run.relative_to(repo)), logdir=str(log.relative_to(repo)),
        runtime_hashes=preparation['runtime_hashes'], map_sha256=preparation['map_sha256'],
        observer_reader=preparation['observer_reader'],
        clocks=dict(present_epoch_after_process_launch_ms=offset,
                    alignment_spread_ms=max(offsets)-min(offsets),
                    note='Input replay, process watchdog and host presentation have separate epochs. Route boundaries use actual logged input timestamps.'),
        requested_steps=steps, all_requested_steps_completed=all(s['completed'] for s in steps),
        timing_covers_route=points[0]['wall_time']<=route_start and points[-1]['wall_time']>=route_end,
        route_window=window(points,route_start,route_end),
        startup_inclusive_window=window(points,clock['wall_time']+(110000+offset)/1000,
                                               clock['wall_time']+(155000+offset)/1000),
        observation_count=len(observations), sampled_path_length_world_units=distance,
        first_position=observations[0]['position'], last_position=observations[-1]['position'],
        positions_min=[min(r['position'][j] for r in observations) for j in range(3)],
        positions_max=[max(r['position'][j] for r in observations) for j in range(3)],
        clusters=sorted(set(r['decoded_location']['cluster'] for r in observations)),
        observer_sample_errors=sum(r['event']=='observer_sample_error' for r in events),
        legacy_alias_matches_all=all(r['legacy_alias_matches'] for r in observations),
        native_hash_summary=next(r for r in events if r['event']=='hash_summary'),
        watchdog=next(r for r in events if r['event']=='watchdog'), shared_unchanged=result['shared_unchanged'],
        visual_acceptance=False, captures=0, audio_acceptance=False,
        limitation='Coordinates prove only this short sampled path. No full-map traversal, visual or audio acceptance; 1 Hz path length is a sampled lower bound. Startup outliers are retained separately from the movement window.')
    if not all(result['shared_unchanged'].values()):
        raise ValueError('Shared preservation failed')
    (run/'route-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('all_requested_steps_completed','timing_covers_route',
        'route_window','startup_inclusive_window','sampled_path_length_world_units','clusters','observer_sample_errors')},indent=2))


if __name__=='__main__':
    main()
