"""Extract uncapped native frame counts; visual review remains a separate gate."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('before', type=Path)
parser.add_argument('after', type=Path)
parser.add_argument('output', type=Path)


def read_run(path):
    path = path.resolve(strict=True)
    assert path.is_relative_to(ROOT)
    command = json.loads((path / 'launch-command.json').read_text())
    assert '--fpsunlock' in command
    logs = sorted(path.glob('trace-runtime.*.log'), key=lambda p:int(p.name.split('.')[-2]), reverse=True)
    text = '\n'.join(p.read_text(errors='replace') for p in logs + [path/'trace-runtime.log'])
    assert 'Developer FPS unlock command line: true' in text
    pattern = (r'RESULT map=zanzibar point=(\d+) frames=(\d+) '
               r'seconds=([\d.]+) fps=([\d.]+) valid=(\w+) camera=([^\r\n]+)')
    samples = []
    for point, frames, seconds, fps, valid, camera in re.findall(pattern, text):
        assert valid == 'true', 'Invalid camera position is not an FPS result'
        samples.append(dict(point=int(point), frames=int(frames), seconds=float(seconds),
                            fps=float(fps), camera=[float(v) for v in camera.split(',')]))
    assert [s['point'] for s in samples] == [1, 2, 3], 'Three complete views required'
    events = [json.loads(line) for line in (path/'loading-trace.jsonl').read_text().splitlines()]
    input_map = next(row for row in events if row.get('event')=='input_map')
    executable = Path(command[0])
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(trace=str(path), samples=samples, map_sha256=input_map['sha256'],
                exe_sha256=sha(executable), command=command)


if __name__ == '__main__':
    args = parser.parse_args()
    before, after = read_run(args.before), read_run(args.after)
    assert before['exe_sha256'] == after['exe_sha256']
    output = args.output.resolve()
    assert output.is_relative_to(ROOT)
    comparison = [dict(point=b['point'], before_fps=b['fps'], after_fps=a['fps'],
                       gain_percent=(a['fps']/b['fps']-1)*100)
                  for b, a in zip(before['samples'], after['samples'])]
    result = dict(before=before, after=after, comparison=comparison,
                  measurement='Native guest-output frames / wall-clock seconds; --fpsunlock; no timing changes',
                  visual_review='Must be recorded separately after inspecting every spawn capture',
                  limitations='Fixed-view PC samples, not worst-case gameplay or Xbox 360 predictions')
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(comparison, indent=2))
