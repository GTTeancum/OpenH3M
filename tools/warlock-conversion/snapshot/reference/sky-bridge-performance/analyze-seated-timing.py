"""Separate startup-inclusive timing from the logged, reproduced seated view."""
import argparse
import datetime
import json
import re
import statistics
from pathlib import Path


def stamp(line):
    return datetime.datetime.strptime(line[1:24], '%Y-%m-%d %H:%M:%S.%f').timestamp()*1000


def analyze(logdir, run):
    repo = Path(__file__).resolve().parents[5]
    logdir.resolve().relative_to(repo)
    run.resolve().relative_to(repo/'work/sky-bridge')
    config = json.loads((run/'recording-configuration.json').read_text(encoding='utf-8-sig'))
    assert config['timing_only'] and config['native_observer']
    assert not any(config[k] for k in ('draw_trace','pixel_probe','header_trace','stage_probe',
        'guest_region','swapchain_region','presented_probe','all_draw_trace'))
    assert not any((run/f).exists() for f in ('draws.bin','pixels.csv','presented.csv',
        'stages.csv','region.csv','swapchain-region.csv','bitmap-headers.csv'))
    observer = json.loads((run/'native-observer-comparison.json').read_text())
    assert observer['same_result'] and observer['same_command']
    lines = sorted(line for path in logdir.glob('*runtime*.log')
                   for line in path.read_text(errors='replace').splitlines())
    first_seated = next(line for line in lines if '[sky-repro] view seated=true' in line)
    marker = stamp(first_seated)
    origins, points = [], []
    for line in lines:
        if '[host-present]' not in line:
            continue
        values = dict(re.findall(r'(\w+)=([\w.\-]+)', line))
        elapsed, frame = float(values['elapsed_ms']), int(values['guest_painted'])
        origins.append(stamp(line)-elapsed)
        if not points or frame != points[-1][1]:
            if points:
                assert frame > points[-1][1] and elapsed > points[-1][0]
            points.append((elapsed, frame))
    origin = statistics.median(origins)
    seated_ms = marker-origin
    selected = [p for p in points if p[0] >= seated_ms]
    assert len(selected) >= 300, 'Need at least ten seconds of seated timing'
    gaps = [b[0]-a[0] for a,b in zip(selected,selected[1:])]
    assert all(b[1] == a[1]+1 for a,b in zip(selected,selected[1:])), 'Unobserved guest frames'
    sorted_gaps = sorted(gaps)
    result = dict(candidate=config['candidate'], run=str(run), logdir=str(logdir),
        first_seated_log=first_seated, first_seated_present_elapsed_ms=seated_ms,
        log_clock_origin_spread_ms=max(origins)-min(origins),
        start_ms=selected[0][0], end_ms=selected[-1][0], frames=len(selected),
        fps=(len(selected)-1)*1000/(selected[-1][0]-selected[0][0]),
        median_ms=statistics.median(gaps), p95_ms=sorted_gaps[int(.95*(len(gaps)-1))],
        maximum_ms=max(gaps), over_50ms=sum(g>50 for g in gaps),
        startup_inclusive=json.loads((logdir/'pacing-windows.json').read_text())['windows'],
        observer=observer,
        limitations=['The first logged seated marker gives a conservative start; no earlier interval is relabeled as seated.',
            'Startup-inclusive results remain included, including the load/placement stall.',
            'Original GPU/runtime DLLs, replay executable and one bounded native snapshot remain in use.',
            'This is a stationary view comparison with timing logs, not full traversal, visual acceptance or a production performance guarantee.'])
    (run/'seated-timing.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('startup_inclusive','limitations','observer')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('logdir',type=Path)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    analyze(args.logdir,args.run)
