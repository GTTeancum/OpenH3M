"""Give an Assembly-validated Halo 3 layout the field names of the TagTool-generated Halo 3 layout, wherever the generated
layout has a field of the same kind at the same offset in the same block. The porter pairs Reach and Halo 3 fields by
name; the Reach layouts are generated from TagTool, so the Halo 3 side must use TagTool's names too. Offsets, sizes and
types stay Assembly's (validated against the 360 data).

  python rename_like_tagtool.py <generated Halo3 layout> <Assembly Halo3 layout, rewritten in place>
"""
import re
import sys
import xml.etree.ElementTree as ET


def fields(elem, prefix=''):
    """{(block path, offset): (tag, name)} for direct children of a plugin or tagblock element."""
    out = {}
    for ch in elem:
        off = ch.get('offset')
        if off is None or ch.get('name') is None:
            continue
        out[(prefix, int(off, 16))] = (ch.tag.lower(), ch.get('name'), ch)
    return out


def walk(gen, asm, path, renames):
    g = fields(gen, path); a = fields(asm, path)
    for key, (atag, aname, ael) in a.items():
        if key not in g:
            continue
        gtag, gname, gel = g[key]
        same_kind = (atag == gtag) or (atag != 'tagblock' and gtag != 'tagblock')
        if same_kind and aname != gname:
            renames.append((path, aname, gname))
            ael.set('name', gname)
        if atag == 'tagblock' and gtag == 'tagblock':
            walk(gel, ael, path + '/' + gname, renames)


def main(gen_path, asm_path):
    gen = ET.parse(gen_path).getroot(); tree = ET.parse(asm_path); asm = tree.getroot()
    renames = []
    walk(gen, asm, '', renames)
    tree.write(asm_path, encoding='utf-8', xml_declaration=True)
    for p, a, g in renames:
        print(f'{p or "/"}: {a} -> {g}')
    print(f'{len(renames)} fields renamed')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
