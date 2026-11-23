"""Stage the original Reach vehicle animations (TagTool ExtractAnimation from the user's Xbox 360 Reach forge_halo.map)
as H3 animation source files, named/typed after the working Forge World H3 port, then compile with tool model-animations.

Only two derived files are produced: 'vehicle closing' (frame order of Reach open_close reversed) and the engine
lift-aim overlays exported earlier from Blender (stock H3 hornet tilt transferred to the Falcon pivots).
Usage: python stage_animations.py <falcon|revenant>
"""
import re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit

BS = chr(92)
SRC = kit.WORK / 'reach_anims'
PLAN = {
 'falcon': (BS.join(['objects', 'vehicles', 'reach_falcon']), 'falcon', [
    ('any idle.JMM', 'any idle.JMM', False),
    ('vehicle hover.JMO', 'vehicle hover.JMA', False),
    ('vehicle landing_gear.JMO', 'vehicle landing_gear.JMA', False),
    ('vehicle rotate_props.JMO', 'vehicle rotate_props.JMA', False),
    ('vehicle open_close.JMO', 'vehicle opening.JMM', False),
    ('vehicle open_close.JMO', 'vehicle closing.JMM', True)],
    ['any any l_lift_aim.JMO', 'any any r_lift_aim.JMO']),
 'revenant': (BS.join(['objects', 'vehicles', 'reach_revenant']), 'revenant', [
    ('any idle.JMM', 'any idle.JMM', False),
    ('vehicle steering.JMO', 'vehicle steering.JMO', False),
    ('vehicle acceleration.JMO', 'vehicle acceleration.JMO', False)], []),
}

def reverse_frames(text):
    """Reverse frame order in a version-16392 animation exchange file (header and node list unchanged)."""
    lines = text.splitlines(); vals = [i for i, l in enumerate(lines) if l.strip()]
    frames = int(lines[vals[1]]); actors = int(lines[vals[3]]); n = int(lines[vals[4 + actors]])
    start = vals[4 + actors + 2 + 3 * n]
    body = [lines[i] for i in vals if i >= start]
    assert len(body) == frames * n * 3, (len(body), frames, n)
    per = n * 3
    chunks = [body[k * per:(k + 1) * per] for k in range(frames)]
    return '\n'.join(lines[:start] + [l for c in reversed(chunks) for l in c]) + '\n'

def main(v):
    root, src, files, keep = PLAN[v]
    d = kit.DATA / root / 'animations'; d.mkdir(parents=True, exist_ok=True)
    for p in d.iterdir():
        if p.name not in keep: p.unlink()
    for s, t, rev in files:
        text = (SRC / src / s).read_text(encoding='utf-8', errors='replace')
        (d / t).write_text(reverse_frames(text) if rev else text, encoding='utf-8')
    print('STAGED', sorted(p.name for p in d.iterdir()))
    rc, out = kit.htool('model-animations', root, log=kit.WORK / ('reach_' + v) / 'compile-model-animations.log', timeout=900)
    msgs = [l.strip() for l in out.replace(chr(13), chr(10)).splitlines() if re.search(r'ERROR|WARNING|import|checksum|node', l, re.I) and '%' not in l]
    print('model-animations rc', rc); print('\n'.join(msgs[:40]))

if __name__ == '__main__':
    main(sys.argv[1])
