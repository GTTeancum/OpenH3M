"""Compose Halo 3 turret animation sources from the ORIGINAL Reach turret animations (TagTool ExtractAnimation from the
user's Xbox 360 Reach forge_halo.map), then compile with H3EK tool model-animations.

Reach turrets aim with "piece-wise" aim sweeps (a rest pose, a yaw sweep and pitch extremes, or a boundary path); Halo 3
aim overlays need a rectangular yaw x pitch grid (rows down->up, each row right->left; the layout the stock H3 Warthog
chaingun and Wraith mortar overlays use, read from their TagTool exports). Two derivations, both using only Reach frames:
  select   each grid cell is the Reach frame whose barrel direction is nearest that cell's yaw/pitch (side guns: their
           sweep already passes through every grid corner/edge point)
  compose  hinge turrets (chin gun, mortar): each cell = the Reach yaw-sweep bone rotation for that yaw combined with the
           Reach pitch-extreme bone rotation scaled to that pitch (single-axis hinges, so scaling is exact)
Frame 0 of an overlay file is the base pose (TagTool / H3 overlay convention); every other frame is one grid cell.
Usage: python turret_aim.py <chin|side_l|side_r|mortar|all>
"""
import json, math, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import kit
from turrets import T
from build import BS

SRC = kit.WORK / 'reach_anims'
# grid: right/left yaw per frame + counts, down/up pitch per frame + counts (H3 aiming screen fields)
GRID = {
 'chin':   dict(mode='compose', aim_bone='b_gun_pitch', axis=0, yaw_ext={90: 1, -90: 8}, pitch_ext={-90: 9, 90: 10},
                right=(45, 2), left=(45, 2), down=(45, 2), up=(45, 2), name='combat fixed aim_still_up'),
 'mortar': dict(mode='compose', aim_bone='b_barrel_center', axis=0,
                yaw_frames={45: 1, 90: 2, 135: 3, 180: 4, -180: 4, -135: 5, -90: 6, -45: 7}, pitch_ext={-90: 9, 90: 10},
                right=(45, 4), left=(45, 4), down=(45, 2), up=(45, 2), name='combat any aim_still_up'),
 'side_l': dict(mode='select', aim_bone='b_l_gun', axis=2, right=(90, 1), left=(90, 1), down=(30, 1), up=(60, 1), name='combat fixed aim_still_up'),
 'side_r': dict(mode='select', aim_bone='b_r_gun', axis=-2, right=(90, 1), left=(90, 1), down=(30, 1), up=(60, 1), name='combat fixed aim_still_up'),
}


def qmul(a, b):  # (w,x,y,z)
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2])
def qinv(q): return np.array([q[0], -q[1], -q[2], -q[3]])
def qpow(q, t):
    q = q if q[0] >= 0 else -q
    ang = 2 * math.acos(max(-1.0, min(1.0, q[0]))); s = math.sin(ang / 2)
    if s < 1e-8: return np.array([1.0, 0, 0, 0])
    ax = q[1:] / s; a = ang * t
    return np.concatenate([[math.cos(a / 2)], ax * math.sin(a / 2)])
def qmat(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


class Anim:
    """Version-16392 animation exchange file (as written by TagTool / the General-101 exporter)."""
    def __init__(self, path):
        self.lines = [l.strip() for l in open(path, encoding='utf-8', errors='replace') if l.strip()]
        t = self.lines; i = 1; frames = int(t[i]); i += 2; actors = int(t[i]); i += 1 + actors; n = int(t[i]); i += 2
        self.names, child, sib = [], [], []
        for _ in range(n): self.names.append(t[i]); child.append(int(t[i + 1])); sib.append(int(t[i + 2])); i += 3
        self.header = t[:i]; self.parent = [-1] * n
        for p in range(n):
            c = child[p]
            while c != -1: self.parent[c] = p; c = sib[c]
        self.frames = []  # per frame: list of (translation, quaternion (w,x,y,z) as stored, scale)
        for _ in range(frames):
            row = []
            for _ in range(n):
                tr = np.array(list(map(float, t[i].split()))); q = list(map(float, t[i + 1].split())); s = float(t[i + 2]); i += 3
                row.append((tr, np.array([q[3], q[0], q[1], q[2]]), s))
            self.frames.append(row)

    def world_dir(self, f, bone, axis):
        def local(k):
            tr, q, s = self.frames[f][k]; m = np.eye(4); m[:3, :3] = qmat(qinv(q)); m[:3, 3] = tr; return m  # stored quats are conjugated
        k = self.names.index(bone); m = local(k); p = self.parent[k]
        while p != -1: m = local(p) @ m; p = self.parent[p]
        d = m[:3, abs(axis)] * (-1 if axis < 0 else 1)  # negative axis: the mirrored right side gun points down -Z
        return math.degrees(math.atan2(d[1], d[0])), math.degrees(math.asin(max(-1, min(1, d[2]))))

    def write(self, path, rows):
        out = list(self.header); out[1] = str(len(rows))
        for row in rows:
            for tr, q, s in row:
                out += ['%.6f\t%.6f\t%.6f' % tuple(tr), '%.6f\t%.6f\t%.6f\t%.6f' % (q[1], q[2], q[3], q[0]), '%.6f' % s]
        Path(path).write_text('\n'.join(out) + '\n', encoding='utf-8')


def cells(g):
    (rs, rc), (ls, lc), (ds, dc), (us, uc) = g['right'], g['left'], g['down'], g['up']
    yaws = [-rs * k for k in range(rc, 0, -1)] + [0] + [ls * k for k in range(1, lc + 1)]
    pitches = [-ds * k for k in range(dc, 0, -1)] + [0] + [us * k for k in range(1, uc + 1)]
    return [(y, p) for p in pitches for y in yaws]


def compose(a, g, yaw, pitch):
    base = a.frames[0]; row = []
    def delta(fr, k):  # stored-quaternion delta of bone k from the base pose
        return qmul(a.frames[fr][k][1], qinv(base[k][1]))
    if 'yaw_frames' in g:
        yf = g['yaw_frames'].get(yaw) if yaw else None; yt = 1.0
    else:
        yf = g['yaw_ext'][90 if yaw > 0 else -90] if yaw else None; yt = abs(yaw) / 90.0
    pf = g['pitch_ext'][90 if pitch > 0 else -90] if pitch else None; pt = abs(pitch) / 90.0
    for k in range(len(a.names)):
        tr, q, s = base[k]
        if yf is not None: q = qmul(qpow(delta(yf, k), yt), q); tr = tr + yt * (a.frames[yf][k][0] - base[k][0])
        if pf is not None: q = qmul(qpow(delta(pf, k), pt), q); tr = tr + pt * (a.frames[pf][k][0] - base[k][0])
        row.append((tr, q / np.linalg.norm(q), s))
    return row


def build(t):
    c = T[t]; g = GRID[t]; src = SRC / c['src']; out = kit.DATA / c['root'] / 'animations'; out.mkdir(parents=True, exist_ok=True)
    for p in out.iterdir(): p.unlink()
    aim = Anim(src / 'vehicle aiming.JMO'); report = dict(turret=t, mode=g['mode'], grid=[], source=str(src / 'vehicle aiming.JMO'))
    y0, _ = aim.world_dir(0, g['aim_bone'], g['axis'])
    rows = [aim.frames[0]]
    for yaw, pitch in cells(g):
        if g['mode'] == 'select':
            best = min(range(len(aim.frames)), key=lambda f: (((aim.world_dir(f, g['aim_bone'], g['axis'])[0] - y0 - yaw + 180) % 360 - 180) ** 2
                                                              + (aim.world_dir(f, g['aim_bone'], g['axis'])[1] - pitch) ** 2) if (yaw or pitch) else 0)
            got = aim.world_dir(best, g['aim_bone'], g['axis'])
            report['grid'].append(dict(cell=[yaw, pitch], reach_frame=best, reach_dir=[round((got[0] - y0 + 180) % 360 - 180, 1), round(got[1], 1)]))
            rows.append(aim.frames[best])
        else:
            rows.append(compose(aim, g, yaw, pitch)); report['grid'].append(dict(cell=[yaw, pitch]))
    aim.write(out / (g['name'] + '.JMO'), rows)
    # base pose: Reach rest pose of the aim set (side guns: deployed; Reach's stowed idle and deploy animation are not used)
    idle = Anim(src / 'any idle.JMM') if t in ('chin', 'mortar') else aim
    idle.write(out / 'any idle.JMM', idle.frames if t in ('chin', 'mortar') else [aim.frames[0], aim.frames[0]])
    if t == 'mortar':
        fire = Anim(src / 'combat fire_1.JMO'); fire.write(out / 'combat fixed gun fire_1.JMO', fire.frames)  # stock wraith mortar label
    (kit.WORK / 'turrets' / c['src'] / 'aim-grid.json').write_text(json.dumps(report, indent=1))
    rc, txt = kit.htool('model-animations', c['root'], log=kit.WORK / 'turrets' / c['src'] / 'compile-model-animations.log', timeout=900)
    jm = c['root'] + BS + c['name'] + '.model_animation_graph'; dump = kit.dump(jm).read_text().splitlines()
    idx = next(int(l.split('animations[')[1].split(']')[0]) for l in dump if l.startswith('Struct:definitions[0]/Block:animations[') and l.endswith('	' + g['name'].replace(' ', ':')))
    A = 'Struct:definitions[0]/Block:blend screens'; S = A + '[0]/Struct:aiming screen[0]/'
    ops = [{'op': 'clear', 'tag': jm, 'block': A}, {'op': 'add', 'tag': jm, 'block': A},
           {'op': 'set', 'tag': jm, 'field': A + '[0]/label', 'value': 'aiming'}]
    for f, v in (('right yaw per frame', g['right'][0]), ('right frame count', g['right'][1]), ('left yaw per frame', g['left'][0]),
                 ('left frame count', g['left'][1]), ('down pitch per frame', g['down'][0]), ('down pitch frame count', g['down'][1]),
                 ('up pitch per frame', g['up'][0]), ('up pitch frame count', g['up'][1])):
        ops.append({'op': 'set', 'tag': jm, 'field': S + f, 'value': str(v)})
    ops.append({'op': 'set', 'tag': jm, 'field': 'Struct:definitions[0]/Block:animations[%d]/blend screen' % idx, 'value': '0'})
    kit.edit(ops, t + '_blend_screen')
    print(t, 'model-animations rc', rc, [l.strip() for l in txt.splitlines() if 'ERROR' in l or 'WARNING' in l][:10])
    print(' grid', [(d['cell'], d.get('reach_frame'), d.get('reach_dir')) for d in report['grid']])


if __name__ == '__main__':
    for t in (list(GRID) if sys.argv[1] == 'all' else [sys.argv[1]]): build(t)
