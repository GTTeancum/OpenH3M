"""Summarize actual native sample windows, preserving rejected measurements."""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
rows = []
for suffix, names in [('', ['Exterior wall (height check failed)', 'Terminal 02 interior', 'Terminal 01 interior']),
                      ('-second', ['Exterior wall retry', 'Outdoor courtyard', 'Interior doorway looking outdoors'])]:
    folder = ROOT / ('.local/map-benchmarks/sky-bridge-manual-20261111' + suffix)
    runtime = (folder/'runtime.log').read_text(errors='replace')
    samples = []
    for line in (folder/'gpu-usage.jsonl').read_text().splitlines():
        record = json.loads(line)
        try:
            sample = json.loads(record['sample'])
            stamp = dt.datetime.fromisoformat(sample['utc'].replace('Z','+00:00')).timestamp()
            samples.append((stamp, sample['engines']))
        except (ValueError, KeyError):
            continue
    for line in runtime.splitlines():
        match = re.search(r'RESULT map=sky_bridge point=(\d+) frames=(\d+) seconds=([\d.]+) fps=([\d.]+) valid=(\w+) camera=(.*)',line)
        if not match:
            continue
        point = int(match[1]); seconds = float(match[3])
        end = dt.datetime.fromisoformat(line[1:24]).timestamp()
        window = [engines for stamp, engines in samples if end-seconds <= stamp <= end]
        totals = [sum(e['percent'] for e in engines if e['instance'].endswith('engtype_3d')) for engines in window]
        apps = {e['process'] for engines in window for e in engines if e['instance'].endswith('engtype_3d')}
        gpu = {app: sum(sum(e['percent'] for e in engines if e['process']==app and e['instance'].endswith('engtype_3d')) for engines in window)/len(window) for app in apps} if window else {}
        capture = folder/f'spawn-{point}.png'
        rows.append(dict(view=names[point-1],fps=float(match[4]),frames=int(match[2]),seconds=seconds,
                         valid=match[5]=='true',camera=match[6],capture=str(capture),
                         capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),gpu_samples=len(window),
                         gpu_3d_mean=sum(totals)/len(totals) if totals else None,gpu_3d_by_process=gpu))
out = ROOT/'.local/map-benchmarks/sky-bridge-manual-20261111/results.json'
out.write_text(json.dumps(dict(method='Uncapped new guest-output frames over 30 seconds per view. Concurrent GPU load retained. GPU means use sampled 3D-engine utilization; not whole-GPU or isolated-map utilization. Rejected positions remain recorded.',results=rows),indent=2))
print(json.dumps(rows,indent=2))
valid = [r for r in rows if r['valid']]
if len(valid) == 5:
    report = ['# Sky Bridge unlocked FPS — 2026-11-11', '',
              'Five distinct views, 30 seconds each, using `--fpsunlock`. Simulation timing unchanged. User loaded the map; the native benchmark positioned the player and captured each view. All five accepted captures were individually inspected. The initial exterior-height failure is excluded and retained in results.json.', '',
              '| View | FPS | Sampled total GPU 3D usage |', '|---|---:|---:|']
    report += [f"| {r['view']} | {r['fps']:.2f} | {r['gpu_3d_mean']:.1f}% |" for r in valid]
    report += ['', 'GPU figures are means of 2–3 Windows 3D-engine samples within each actual measurement window, including other applications. Xemu and XboxPcApp remained running. These are shared-load observations, not isolated performance estimates. Video-codec usage is not included. No Xbox 360 hardware result is implied.', '',
               'Native benchmark position checks passed for all five accepted samples. Installed maps and runtime binaries were not modified. The game remains open with benchmark control released.', '']
    for r in valid:
        report += [f"![{r['view']}]({Path(r['capture']).as_posix()})", '']
    (ROOT/'tools/map-review/SKY-BRIDGE-FPS-20261111.md').write_text('\n'.join(report),encoding='utf8')
