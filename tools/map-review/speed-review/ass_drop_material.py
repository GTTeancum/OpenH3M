"""Remove every triangle that uses the given material indices from a Halo 3 ASS source (object triangle
counts updated, all other lines verbatim). Used for materials the editing kit cannot load (they render
nothing and break the lighting bake). Usage: ass_drop_material.py <in.ass> <out.ass> <material index>..."""
import sys
src, out, drop = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3:]}
L = open(src, encoding='utf-8', errors='surrogateescape').read().split('\n')
res = []; removed = 0; i = 0; n = len(L)
in_objects = False
while i < n:
    line = L[i]
    if line.startswith(';### OBJECTS'): in_objects = True
    if line.startswith(';### INSTANCES'): in_objects = False
    # a triangle-count line is a bare integer followed by triangle lines "m\t\ta\tb\tc"
    if in_objects and line.strip().isdigit() and i + 1 < n and len(L[i + 1].split('\t')) == 5 and L[i + 1].split('\t')[1] == '':
        count = int(line); tris = L[i + 1:i + 1 + count]
        assert all(len(t.split('\t')) == 5 for t in tris), i
        keep = [t for t in tris if int(t.split('\t')[0]) not in drop]
        removed += count - len(keep)
        res.append(str(len(keep))); res.extend(keep); i += 1 + count; continue
    res.append(line); i += 1
open(out, 'w', encoding='utf-8', errors='surrogateescape', newline='\n').write('\n'.join(res))
print('removed triangles:', removed)
