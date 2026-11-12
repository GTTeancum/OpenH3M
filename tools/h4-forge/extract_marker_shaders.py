"""Extract retail H4 marker shader microcode using Assembly's runtime layouts.

All private inputs and outputs stay in the repository. No cache is modified.
"""
import contextlib
import hashlib
import io
import json
import struct
import xml.etree.ElementTree as ET

with contextlib.redirect_stdout(io.StringIO()):
    import audit_marker_visual as cache

reference = cache.RESEARCH / 'reference'
layouts = {n.get('for'): n for n in ET.parse(reference / 'H4_Layouts_Shaders.xml').getroot()}
schema = ET.parse(reference / 'Halo4-mtsb.xml').getroot()
out = cache.RESEARCH / 'isolated/marker-shaders'
out.mkdir(exist_ok=True)


def value(layout, name, base):
    node = next(n for n in layouts[layout] if n.get('name') == name)
    return cache.u(base + int(node.get('offset'), 0))


report = []
for material in (16, 331):
    at = cache.tags[material]['offset']
    bank_datum = cache.u(at + 0x30)
    bank = cache.tags[bank_datum & 65535]
    assert bank['group'] == 'mtsb' and bank['salt'] == bank_datum >> 16
    for kind, block_offset in [('vs', 0x34), ('ps', 0x40)]:
        assert cache.u(at + block_offset) == 1
        entry = cache.offset(cache.u(at + block_offset + 4))
        if kind == 'vs':
            count = cache.u(entry)
            entries = cache.offset(cache.u(entry + 4))
            indices = [(i, cache.u(entries + i * 8 + 4)) for i in range(count)]
        else:
            indices = [(0, cache.u(entry + 4))]
        name = 'vertex' if kind == 'vs' else 'pixel'
        node = next(n for n in schema if n.get('name') == f'Compiled {name.title()} Shaders')
        block = bank['offset'] + int(node.get('offset'), 0)
        for vertex_type, index in indices:
            if index == 0xffffffff:
                continue
            assert index < cache.u(block)
            shader = cache.offset(cache.u(block + 4)) + index * int(node.get('elementSize'), 0)
            runtime = next(n for n in node if n.tag == 'shader')
            header = cache.offset(cache.u(shader + int(runtime.get('offset'), 0)))
            layout = name + ' shader info'
            debug = header + int(layouts[layout].get('size'), 0)
            assert value('shader debug info', 'magic', debug) >> 16 == 0x102a
            size = value('shader debug info', 'shader data size', debug)
            code_info = debug + value('shader debug info', 'code info offset', debug)
            constant_size = value('code info', 'constant data size', code_info)
            code_size = value('code info', 'code data size', code_info)
            assert 0 < code_size <= size <= 1024 * 1024
            assert constant_size + code_size <= size and code_size % 12 == 0
            payload = cache.offset(value(layout, 'shader data address', header))
            code = cache.data[payload + constant_size:payload + constant_size + code_size]
            assert len(code) == code_size
            stem = f'{material}-{kind}-{vertex_type}'
            (out / (stem + '.ucode')).write_bytes(code)
            constants = cache.data[payload:payload + constant_size]
            (out / (stem + '.constants')).write_bytes(constants)
            report.append(dict(material=material, material_name=cache.tags[material]['name'],
                kind=kind, vertex_type=vertex_type, shader_index=index, file=stem + '.ucode',
                source_file_offset=payload + constant_size,
                code_size=code_size, code_sha256=hashlib.sha256(code).hexdigest(),
                constant_words=[hex(x) for x in struct.unpack('>' + 'I' * (len(constants)//4), constants)]))

(out / 'extracted.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
for item in report:
    print(item['file'], item['code_size'], item['code_sha256'])
