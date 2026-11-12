"""Translate compiled MCC H3 expression records without rebuilding their graph.

Callers must validate roots/handles, preserve scenario index tables and relocate
script strings alongside this payload. This module does not publish a cache.
HsSyntaxNode layout/flags: TagTool ce2dc6ac13072b160752af618ea1dc143e2727ac.
"""
import struct


def convert_expressions(records, strings, source_defs, target_defs, script_names,
                        global_names, relocate_tag, relocate_string_id):
    def table(defs, section, key='opcode'):
        return {(int(x.get(key), 0) if key == 'opcode' else x.get(key)): x
                for x in defs.find(section)}
    st, tt = table(source_defs, 'valueTypes'), table(target_defs, 'valueTypes', 'name')
    sf, tf = table(source_defs, 'functions'), table(target_defs, 'functions', 'name')
    sg, tg = table(source_defs, 'globals'), table(target_defs, 'globals', 'name')
    nodes = [struct.unpack('<4H3I2h', row) for row in records]
    script_children = {node[6] & 0xffff for node in nodes if node[0] and node[3] == 10}
    output, changes = bytearray(), []

    def text(offset):
        if not 0 <= offset < len(strings) or strings.find(b'\0', offset) < 0:
            raise ValueError(f'Invalid script string offset {offset}')
        return strings[offset:strings.index(b'\0', offset)].decode('ascii')

    def value_type(opcode):
        src = st.get(opcode)
        dst = tt.get(src.get('name')) if src is not None else None
        if dst is None or src.get('size') != dst.get('size'):
            raise ValueError(f'Unsupported script value type {opcode}')
        return src, int(dst.get('opcode'), 0)

    def function(opcode):
        src = sf.get(opcode)
        dst = tf.get(src.get('name')) if src is not None else None
        if (dst is None or src.get('returnType') != dst.get('returnType')
                or [dict(x.attrib) for x in src] != [dict(x.attrib) for x in dst]):
            raise ValueError(f'Unsupported script function {opcode}')
        return int(dst.get('opcode'), 0)

    for index, (salt, opcode, kind, flags, nxt, string_at, data, line, unknown) in enumerate(nodes):
        raw = records[index]
        if not salt:
            if raw != bytes(2) + b'\xba' * 22:
                raise ValueError(f'Unexpected unallocated expression {index}')
            output.extend(raw)
            continue
        _, target_kind = value_type(kind)
        target_opcode, payload = opcode, raw[16:20]
        if flags == 8:
            target_opcode = function(opcode)
            payload = struct.pack('>I', data)
        elif flags == 10:
            if opcode >= len(script_names):
                raise ValueError(f'Invalid script call {opcode}')
            payload = struct.pack('>I', data)
        elif flags in (13, 29):
            if opcode != 0xffff:
                _, target_opcode = value_type(opcode)
            if flags == 13:
                if data & 0x8000:
                    src = sg.get(data & 0x7fff)
                    dst = tg.get(src.get('name')) if src is not None else None
                    if (data >> 16 != 0xffff or dst is None or src.get('type') != dst.get('type')
                            or src.get('name') != text(string_at)):
                        raise ValueError(f'Unsupported external global at expression {index}')
                    data = 0xffff8000 | int(dst.get('opcode'), 0)
                elif data >= len(global_names) or global_names[data] != text(string_at):
                    raise ValueError(f'Invalid scenario global at expression {index}')
            payload = struct.pack('>I', data)
        elif flags == 9 and kind == 2:
            if index in script_children:
                if opcode >= len(script_names) or script_names[opcode] != text(string_at):
                    raise ValueError(f'Invalid script name at expression {index}')
            else:
                target_opcode = function(opcode)
                if sf[opcode].get('name') != text(string_at):
                    raise ValueError(f'Function name/opcode mismatch at expression {index}')
            payload = struct.pack('>I', data)
        elif flags == 9:
            # Opcode is the literal's stored type; kind can be its cast result.
            literal, target_opcode = value_type(opcode)
            size, name = int(literal.get('size')), literal.get('name')
            if size not in (0, 1, 2, 4):
                raise ValueError(f'Unsupported literal width {size}')
            if literal.get('tag'):
                data = relocate_tag(data, literal.get('tag')) if data != 0xffffffff else data
                payload = struct.pack('>I', data)
            elif name in ('string_id', 'ai_line'):
                payload = struct.pack('>I', relocate_string_id(data))
            elif name == 'string':
                if data != string_at:
                    raise ValueError(f'String literal does not use string-table offset at {index}')
                # Literal messages may contain legacy code-page characters;
                # keep their bytes rather than interpreting them as identifiers.
                if not 0 <= data < len(strings) or strings.find(b'\0', data) < 0:
                    raise ValueError(f'Invalid string literal offset at {index}')
                payload = struct.pack('>I', data)
            else:
                payload = payload[:size][::-1] + payload[size:]
        else:
            raise ValueError(f'Unsupported script expression flags {flags} at {index}')
        output.extend(struct.pack('>4H2I', salt, target_opcode, target_kind, flags, nxt, string_at)
                      + payload + struct.pack('>2h', line, unknown))
        if target_opcode != opcode:
            changes.append(dict(index=index, source_opcode=opcode, target_opcode=target_opcode))
    return bytes(output), changes
