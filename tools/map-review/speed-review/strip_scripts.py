"""Remove whole top-level HaloScript forms whose script name contains any given word, and any call to those
scripts (including mp_wake_script / wake of them). Usage: strip_scripts.py <in.hsc> <out.hsc> <word>..."""
import re, sys
src, out, words = sys.argv[1], sys.argv[2], [w.lower() for w in sys.argv[3:]]
text = open(src, encoding='latin-1').read()

def forms(t):
    depth = 0; start = None; i = 0; res = []
    while i < len(t):
        ch = t[i]
        if ch == ';':
            while i < len(t) and t[i] != '\n': i += 1
            continue
        if ch == '"':
            i += 1
            while i < len(t) and t[i] != '"': i += 1
        elif ch == '(':
            if depth == 0: start = i
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0: res.append((start, i + 1))
        i += 1
    assert depth == 0, 'unbalanced parentheses'
    return res

removed = []; keep = []; last = 0
for a, b in forms(text):
    head = text[a:b].split('\n', 1)[0]
    m = re.match(r'\(script\s+\w+\s+(?:\w+\s+)?\(?(\w+)', head)
    name = m.group(1) if m else ''
    if any(w in name.lower() for w in words):
        removed.append(name); keep.append(text[last:a]); last = b
keep.append(text[last:]); text = ''.join(keep)
names = set(n.lower() for n in removed)
lines = []
for line in text.split('\n'):
    toks = re.findall(r'[\w]+', line.lower())
    if toks and any(t in names for t in toks) and line.strip().startswith('('):
        continue
    lines.append(line)
text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines))
open(out, 'w', encoding='latin-1', newline='\n').write(text)
print('removed scripts:', removed)
left = [w for w in words if w in text.lower()]
print('remaining mentions of', words, ':', left)
