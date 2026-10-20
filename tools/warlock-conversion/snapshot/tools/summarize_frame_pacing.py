"""Summarize native frame-counter timing; flag lost samples instead of hiding them."""
import argparse
import csv
import json
from pathlib import Path
import statistics


def summarize(run):
    rows = [r for r in csv.DictReader((run / 'guest-frames.csv').open()) if float(r['seconds']) >= 125]
    if not rows or all(abs(float(r['seconds']) * 1000 - round(float(r['seconds']) * 1000)) < .001 for r in rows):
        raise ValueError('Missing or quantized timestamps; require high-resolution counter capture')
    intervals, skipped = [], 0
    for a, b in zip(rows, rows[1:]):
        delta = int(b['guest_frame_count']) - int(a['guest_frame_count'])
        if delta != 1:
            skipped += max(1, delta - 1)
            continue
        intervals.append(1000 * (float(b['seconds']) - float(a['seconds'])))
    if len(intervals) < 100:
        raise ValueError('Insufficient native frame samples')
    ordered = sorted(intervals)
    def percentile(q): return round(ordered[round((len(ordered) - 1) * q)], 3)
    state = json.loads((run / 'run.json').read_text())
    report = {'run': str(run), 'mode': state['mode'], 'stock': state.get('stock', False),
            'map_sha256': state['map_sha256'], 'metric': 'new guest-output frames, not host presents',
            'measurement_start_seconds': 125, 'scene_verified_by_this_tool': False,
            'intervals': len(intervals), 'skipped_frames': skipped,
            'mean_ms': round(statistics.mean(intervals), 3),
            'stdev_ms': round(statistics.pstdev(intervals), 3),
            'p05_ms': percentile(.05), 'p50_ms': percentile(.5),
            'p95_ms': percentile(.95), 'p99_ms': percentile(.99),
            'under_25_ms': sum(x < 25 for x in intervals),
            'over_41_667_ms': sum(x > 41.667 for x in intervals),
            'max_observation_poll_gap_ms': round(max(float(r['poll_gap_ms']) for r in rows), 3),
            'caution': 'Scene and simulation speed require separate verification. Polling introduces timing uncertainty up to the observation gap. Display cadence is separate.'}

    vpath = run / 'gpu-progress.csv'
    if not vpath.exists(): vpath = run / 'vblank.csv'  # Legacy mislabeled discovery trace.
    if vpath.exists():
        vr = [r for r in csv.DictReader(vpath.open()) if float(r['seconds']) >= 125]
        vd = [1000 * (float(b['seconds']) - float(a['seconds']))
              for a, b in zip(vr, vr[1:]) if int(b.get('gpu_progress_count', b.get('vblank_count'))) - int(a.get('gpu_progress_count', a.get('vblank_count'))) == 1]
        if len(vd) < 100: raise ValueError('Insufficient GPU progress samples')
        ordered_v = sorted(vd)
        report['gpu_progress'] = {
            'metric': 'combined vblank AND frame-swap increments; not pure vblank timing',
            'intervals': len(vd), 'mean_ms': round(statistics.mean(vd), 3),
            'stdev_ms': round(statistics.pstdev(vd), 3),
            'p05_ms': round(ordered_v[round((len(vd)-1)*.05)], 3),
            'p95_ms': round(ordered_v[round((len(vd)-1)*.95)], 3),
            'non_single_counter_deltas': sum(int(b.get('gpu_progress_count', b.get('vblank_count')))-int(a.get('gpu_progress_count', a.get('vblank_count'))) != 1 for a,b in zip(vr,vr[1:])),
            'max_observation_poll_gap_ms': round(max(float(r['poll_gap_ms']) for r in vr),3)}
    gvpath = run / 'guest-vblank.csv'
    if gvpath.exists():
        gr = [r for r in csv.DictReader(gvpath.open()) if float(r['seconds']) >= 125]
        gd = [1000 * (float(b['seconds']) - float(a['seconds']))
              for a,b in zip(gr,gr[1:]) if int(b['guest_vblank_count'])-int(a['guest_vblank_count']) == 1]
        if len(gd) < 100: raise ValueError('Insufficient guest vblank samples')
        ordered_g = sorted(gd)
        report['guest_vblank'] = {
            'metric': 'guest device+0x4094, incremented by source-0 vblank handler',
            'intervals': len(gd), 'mean_ms': round(statistics.mean(gd),3),
            'stdev_ms': round(statistics.pstdev(gd),3),
            'p05_ms': round(ordered_g[round((len(gd)-1)*.05)],3),
            'p95_ms': round(ordered_g[round((len(gd)-1)*.95)],3),
            'non_single_counter_deltas': sum(int(b['guest_vblank_count'])-int(a['guest_vblank_count'])!=1 for a,b in zip(gr,gr[1:])),
            'max_observation_poll_gap_ms': round(max(float(r['poll_gap_ms']) for r in gr),3)}
    return report



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = summarize(args.run)
    (args.run / 'native-summary.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
