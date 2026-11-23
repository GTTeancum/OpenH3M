"""Summarize which nodes move in a JMA/JMM/JMO (version 16392) and by how much, per frame vs frame 0.

Reads the plain-text animation exchange format written by TagTool/General-101; read-only inspection.
"""
import math, sys

def load(path):
    t = [l.strip() for l in open(path, encoding='utf-8', errors='replace') if l.strip()]
    i = 0
    ver = int(t[i]); i += 1
    frames = int(t[i]); i += 1; fps = t[i]; i += 1
    actors = int(t[i]); i += 1 + actors
    n = int(t[i]); i += 1; i += 1  # checksum
    names = []
    for _ in range(n):
        names.append(t[i]); i += 3
    data = []
    for f in range(frames):
        row = []
        for _ in range(n):
            tr = list(map(float, t[i].split())); q = list(map(float, t[i + 1].split())); s = float(t[i + 2]); i += 3
            row.append((tr, q, s))
        data.append(row)
    return names, data

def qangle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))

if __name__ == '__main__':
    names, data = load(sys.argv[1])
    print('frames', len(data), 'nodes', len(names))
    for ni, nm in enumerate(names):
        rot = [qangle(data[0][ni][1], data[f][ni][1]) for f in range(len(data))]
        mov = [math.dist(data[0][ni][0], data[f][ni][0]) for f in range(len(data))]
        if max(rot) > 0.01 or max(mov) > 0.01:
            print('  %-20s rot(deg) %s  move(jms) max %.2f' % (nm, [round(r, 1) for r in rot], max(mov)))
