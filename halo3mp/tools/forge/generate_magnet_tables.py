"""Generate Spartan's per-piece magnet tables from the clean-room spec.

Input : tools/h4-forge/spec/06-magnet-placement-rules.md, section 7 (each magnet
        described as a feature of our own piece, in our coordinates).
Output: halo3mp/src/forge/forge_magnets.cpp (code tables; no data file).
Rows the parser cannot place unambiguously are reported and must be authored
by hand in OVERRIDES below.

Usage: python generate_magnet_tables.py <06-magnet-placement-rules.md> <forge_magnets.cpp> [palettes.json]

Tables are bound to the pieces in the installed maps by name: palettes.json
(from extract_palettes.py) lists each map's Forge palette, piece name ->
object definition. Spec pieces absent from a map stay in the source unbound.
"""
import json
import math
import re
import sys

SPEC, OUT = sys.argv[1], sys.argv[2]
PALETTES = sys.argv[3] if len(sys.argv) > 3 else None
MAPS = {'Gulch': 1730, 'Cove': 1731}
AX = {'X': 0, 'Y': 1, 'Z': 2}
NUM = r'(-?\d+(?:\.\d+)?)'

# Hand-authored rows keyed by (piece name, magnet number): (x, y, z), each with
# the reason. Empty unless the parser cannot read a row.
OVERRIDES = {}


def axis_vector(sign_axis):
    v = [0.0, 0.0, 0.0]
    v[AX[sign_axis[1]]] = 1.0 if sign_axis[0] == '+' else -1.0
    return v


def frame(text):
    m = re.match(r'faces ([+-][XYZ]), up ([+-][XYZ])$', text)
    if m:
        return axis_vector(m.group(1)), axis_vector(m.group(2))
    m = re.match(r'faces horizontal at ' + NUM + r' deg from \+X toward \+Y, up \+Z$', text)
    if m:
        a = math.radians(float(m.group(1)))
        return [math.cos(a), math.sin(a), 0.0], [0.0, 0.0, 1.0]
    m = re.match(r'faces \(' + NUM + ', ' + NUM + ', ' + NUM + r'\), up \(' + NUM + ', ' + NUM + ', ' +
                 NUM + r'\)$', text)
    if m:
        return [float(m.group(i)) for i in (1, 2, 3)], [float(m.group(i)) for i in (4, 5, 6)]
    raise ValueError('frame: ' + text)


def features(text):
    out = {}
    for m in re.finditer(r'\b([XYZ])=' + NUM + r' (?:plane|bbox extreme)', text):
        out.setdefault(m.group(1), float(m.group(2)))
    return out


def place(loc, feat, bounds):
    lo = {a: bounds[a][0] for a in 'XYZ'}
    hi = {a: bounds[a][1] for a in 'XYZ'}
    centre = {a: (lo[a] + hi[a]) / 2 for a in 'XYZ'}
    loc = re.sub(r'\*\*.*?\*\*', '', loc)
    loc = re.sub(r'\(on the construction planes[^)]*\)', '', loc).strip()
    p = {}

    def extreme(sign, a):
        if a in feat:
            return feat[a]
        return hi[a] if sign == '+' else lo[a]

    face = None
    m = re.search(r'the ([+-])([XY])-facing plane at \2=' + NUM, loc)
    if m:
        face = m.group(2)
        p[face] = float(m.group(3))
    if face is None:
        m = re.search(r'(?:^|of |; )([XY])=' + NUM + r', facing ([+-])\1, off any measured', loc)
        if m:
            face = m.group(1)
            p[face] = float(m.group(2))
    if face is None:
        m = re.search(r'the ([+-])([XY]) face', loc)
        if m:
            face = m.group(2)
            p[face] = extreme(m.group(1), face)
    if face is None:
        m = re.search(r'the ([XY]) centre plane', loc)
        if m:
            face = m.group(1)
            p[face] = centre[face]
    for m in re.finditer(r'\b([XY])=' + NUM + r' \(-?\d+% across', loc):
        p.setdefault(m.group(1), float(m.group(2)))
    for m in re.finditer(r'on the measured ([XY])=' + NUM + ' plane', loc):
        p.setdefault(m.group(1), float(m.group(2)))
    for m in re.finditer(r'at the ([+-])([XY]) extreme', loc):
        p.setdefault(m.group(2), extreme(m.group(1), m.group(2)))
    m = re.search(r'(top|bottom) corner at the ([+-])([XY]) end', loc)
    if m:
        p.setdefault(m.group(3), extreme(m.group(2), m.group(3)))
    if 'centred in X' in loc:
        p.setdefault('X', centre['X'])
    if 'centred in Y' in loc:
        p.setdefault('Y', centre['Y'])
    for a in 'XY':
        if a not in p and ('centred across it' in loc or loc.startswith('middle of')):
            p[a] = centre[a]
    zfeat = feat.get('Z')
    if re.search(r'top face', loc):
        p['Z'] = zfeat if zfeat is not None else hi['Z']
    elif re.search(r'bottom face', loc):
        p['Z'] = zfeat if zfeat is not None else lo['Z']
    else:
        m = re.search(r'at (?:the level of the horizontal surface )?' + NUM + ' above the base', loc)
        if m:
            p['Z'] = lo['Z'] + float(m.group(1))
        elif re.search(r'\btop edge\b|at top\b|top corner', loc):
            p['Z'] = zfeat if zfeat is not None else hi['Z']
        elif re.search(r'\bbottom edge\b|at bottom\b|bottom corner', loc):
            p['Z'] = zfeat if zfeat is not None else lo['Z']
        elif 'mid-height' in loc:
            p['Z'] = zfeat if zfeat is not None else centre['Z']
    missing = [a for a in 'XYZ' if a not in p]
    if missing:
        raise ValueError('cannot place %s: %s' % (missing, loc))
    return [p['X'], p['Y'], p['Z']]


def fl(v):
    if abs(v) < 1e-9:
        v = 0.0
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s + ('.f' if '.' not in s else 'f')


def vec(v):
    return '{' + ', '.join(fl(x) for x in v) + '}'


def tokens(name):
    words = re.findall(r'[a-z0-9]+', name.lower())
    return frozenset(w for w in words if w not in ('ff', 'forge'))


def main():
    palettes = json.load(open(PALETTES)) if PALETTES else {}
    text = open(SPEC, encoding='utf8').read()
    body = text.split('## 7. Exact per-piece magnet sets', 1)[1]
    body = body.split('## User decision, 2026-11-26', 1)[0]
    pieces = re.split(r'\n#### ', body)[1:]
    out_pieces, problems, total, unbound = [], [], 0, []
    for chunk in pieces:
        head = chunk.split('\n', 1)[0]
        m = re.match(r'(.*) \((.*), (\d+) magnets?\)$', head)
        name, kind, count = m.group(1), m.group(2), int(m.group(3))
        em = re.search(r'^Entries: (.*?)\. Our bounds X ' + NUM + r'\.\.' + NUM + ', Y ' + NUM + r'\.\.' + NUM +
                       ', Z ' + NUM + r'\.\.' + NUM, chunk, re.M)
        entries = [(MAPS[k], int(v, 16)) for k, v in re.findall(r'(Gulch|Cove) (0x[0-9A-F]+)', em.group(1))]
        bounds = {'X': (float(em.group(2)), float(em.group(3))), 'Y': (float(em.group(4)), float(em.group(5))),
                  'Z': (float(em.group(6)), float(em.group(7)))}
        rows = []
        for line in chunk.splitlines():
            if not re.match(r'^\| \d+ \|', line):
                continue
            cols = [c.strip() for c in line.strip().strip('|').split('|')]
            n = int(cols[0])
            f, u = frame(cols[2])
            try:
                pos = OVERRIDES.get((name, n)) or place(cols[1], features(cols[3]), bounds)
            except ValueError as e:
                problems.append('%s #%d: %s' % (name, n, e))
                pos = None
            rows.append((n, pos, f, u))
        if len(rows) != count:
            problems.append('%s: %d rows, header says %d' % (name, len(rows), count))
        total += len(rows)
        out_pieces.append((name, kind, entries, rows))
    if problems:
        print('\n'.join(problems))
        sys.exit(1)
    lines = ['// Generated by halo3mp/tools/forge/generate_magnet_tables.py from',
             '// tools/h4-forge/spec/06-magnet-placement-rules.md section 7. Do not edit by hand:',
             '// change the generator (or its OVERRIDES) and regenerate.',
             "// Positions are in each piece's own frame (Z up); order is the spec order.",
             '// Bound by piece name to the Forge palettes of the installed maps (tools/forge/palettes.json).',
             '#include "forge_core.h"', '', 'namespace forge {', 'namespace {']
    tables = []
    for i, (name, kind, entries, rows) in enumerate(out_pieces):
        lines.append('// %s (%s, %d magnets)' % (name, kind, len(rows)))
        lines.append('constexpr MagnetDef kPiece%d[] = {' % i)
        for n, pos, f, u in rows:
            lines.append('    {%s, %s, %s},  // %d' % (vec(pos), vec(f), vec(u), n))
        lines.append('};')
        bound = []
        for mp, pal in sorted(palettes.items()):
            for pname, tag in pal['pieces'].items():
                if tokens(pname) == tokens(name):
                    bound.append((int(mp), tag, pname))
        if not palettes:
            bound = [(mp, tag, '') for mp, tag in entries]
        for mp, tag, pname in bound:
            tables.append('    {%d, 0x%08X, "%s", kPiece%d, %d},  // %s' % (mp, tag, name.replace('"', ''), i, len(rows), pname))
        if palettes and not bound:
            unbound.append(name)
    lines += ['}  // namespace', '', 'constexpr MagnetTable kTables[] = {'] + tables + ['};', '',
              'const MagnetTable* FindMagnets(uint32_t map, uint32_t tag) {',
              '  if (!AdvancedForgeMap(map)) return nullptr;',
              '  for (const auto& t : kTables)',
              '    if (t.map == map && t.tag == tag) return &t;',
              '  return nullptr;', '}', '',
              '// User decision 2026-11-26: Forge Gulch (1730) and Force Cove (1731) only.',
              'bool AdvancedForgeMap(uint32_t map) { return map == 1730 || map == 1731; }', '',
              '}  // namespace forge', '']
    open(OUT, 'w', encoding='utf8', newline='\n').write('\n'.join(lines))
    print('pieces %d, bound entries %d, magnets %d' % (len(out_pieces), len(tables), total))
    if unbound:
        print('not in the installed maps (%d): %s' % (len(unbound), ', '.join(unbound)))


main()
