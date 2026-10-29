"""Encode process-local scripted steps as exclusive H3IR controller states."""
import struct


def encode(steps):
    buttons = dict(UP=1, DOWN=2, LEFT=4, RIGHT=8, START=16, BACK=32,
                   LB=256, RB=512, A=4096, B=8192, X=16384, Y=32768)
    axes = {'LSLEFT': (0, -30000), 'LSRIGHT': (0, 30000),
            'LSDOWN': (1, -30000), 'LSUP': (1, 30000),
            'RSSLOWRIGHT': (2, 14000), 'RSLEFT': (2, -30000), 'RSRIGHT': (2, 30000),
            'RSDOWN': (3, -30000), 'RSUP': (3, 30000),
            'LT': (4, 255), 'RT': (5, 255)}
    parsed = []
    times = {0}
    for step in steps:
        at, action = step.split(':')
        name, duration = action.split('+')
        start, end = int(at), int(at) + int(duration)
        if name not in buttons and name not in axes:
            raise ValueError('Unsupported replay action: ' + name)
        parsed.append((start, end, name))
        times.update((start, end))
    frames = []
    for at in sorted(times):
        mask, values = 0, [0] * 6
        for start, end, name in parsed:
            if start <= at < end:
                if name in buttons:
                    mask |= buttons[name]
                else:
                    index, value = axes[name]
                    values[index] = value
        frames.append(struct.pack('<IHhhhhBB', at, mask, *values))
    return b'H3IR' + struct.pack('<I', len(frames)) + b''.join(frames)
