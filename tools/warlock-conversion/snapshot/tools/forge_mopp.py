"""Read reachable MOPP terminals with branch-local offsets.

Control-flow semantics: TagTool/Havok/HavokMoppUtil.cs (GetAllKeysRecursive).
Unknown opcodes and conflicting execution states fail closed.
"""

def terminals(code):
    pending = [(0, 0)]
    seen = set()
    result = []
    def uint(at, size):
        if at < 0 or at + size > len(code):
            raise ValueError('Truncated MOPP operand')
        return int.from_bytes(code[at:at+size], 'big')
    while pending:
        at, base = pending.pop()
        while True:
            if not 0 <= at < len(code):
                raise ValueError('MOPP branch outside code')
            state = (at, base)
            if state in seen:
                break
            seen.add(state)
            op = code[at]
            if op == 0:
                break
            if 0x30 <= op <= 0x53:
                key = op - 0x30 if op < 0x50 else uint(at+1, op-0x4f)
                result.append((at, base, key + base))
                break
            if 1 <= op <= 4:
                at += 4
            elif 5 <= op <= 7:
                size = op-4
                at += 1+size+uint(at+1, size)
            elif op in (9, 10, 11):
                size = {9:1,10:2,11:4}[op]
                value = uint(at+1, size)
                base = value if op == 11 else base + value
                at += size+1
            elif 0x10 <= op <= 0x1c or 0x20 <= op <= 0x22:
                size = 4 if op < 0x20 else 3
                pending.append((at+size+uint(at+size-1, 1), base))
                at += size
            elif 0x23 <= op <= 0x25:
                pending.append((at+7+uint(at+5,2), base))
                at += 7+uint(at+3,2)
            elif 0x26 <= op <= 0x2b:
                at += 3 if op <= 0x28 else 7
            elif 0x60 <= op <= 0x6b:
                at += 1 + (1 << ((op-0x60)//4))
            else:
                raise ValueError(f'Unsupported MOPP operation {op:#x} at {at}')
    return result


def remap_surfaces(code, surface_map, source_surface_count, instance_count):
    """Retain authored spatial tests, remove cut faces, and relocate branches.

    Forge World's 0x08..0x0d key classes partition the surface table: classes
    0x08..0x0c share one subset, 0x0d covers its complement. Class 0x10 indexes
    instances, which this conversion retains. Verify that contract per input.
    Absolute terminal bases avoid invalidating compact relative encodings.
    """
    reached = terminals(code)
    classes = {}
    keys_at = {}
    for at, _, key in reached:
        kind, index = key >> 26, key & 0x3ffffff
        classes.setdefault(kind, set()).add(index)
        if at in keys_at and keys_at[at] != key:
            raise ValueError('Shared MOPP terminal has conflicting keys')
        keys_at[at] = key
        if kind not in range(8, 14) and kind != 16:
            raise ValueError(f'Unknown Forge BSP shape class {kind}')
        if index >= (instance_count if kind == 16 else source_surface_count):
            raise ValueError('Forge BSP shape key outside its table')
    if any(classes.get(k) != classes.get(8) for k in range(9,13)):
        raise ValueError('Forge BSP surface shape classes disagree')
    if classes.get(8,set()) & classes.get(13,set()) or (classes.get(8,set()) | classes.get(13,set())) != set(range(source_surface_count)):
        raise ValueError('Forge BSP keys do not partition the surface table')
    lengths = {0:0, **dict.fromkeys(range(1,5),3),5:1,6:2,7:3,9:1,10:2,11:4,
               **dict.fromkeys(range(0x10,0x1d),3),**dict.fromkeys(range(0x20,0x23),2),
               **dict.fromkeys(range(0x23,0x26),6),**dict.fromkeys(range(0x26,0x29),2),
               **dict.fromkeys(range(0x29,0x2c),6),**dict.fromkeys(range(0x30,0x50),0),
               **{0x50+i:i+1 for i in range(4)},**dict.fromkeys(range(0x60,0x64),1),
               **dict.fromkeys(range(0x64,0x68),2),**dict.fromkeys(range(0x68,0x6c),4)}
    nodes, locations, size, at = [], {}, 0, 0
    expected = []
    def uint(at, n):
        return int.from_bytes(code[at:at+n], 'big')
    while at < len(code):
        op = code[at]
        n = lengths.get(op)
        if n is None or at+1+n > len(code):
            raise ValueError(f'Unsupported relocation opcode {op:#x}')
        raw = code[at:at+n+1]
        targets = None
        if 0x30 <= op <= 0x53:
            key = keys_at.get(at)
            raw = b'\0'
            if key is not None:
                kind, index = key >> 26, key & 0x3ffffff
                if kind == 16 or index in surface_map:
                    mapped = key if kind == 16 else (kind << 26) | surface_map[index]
                    raw = b'\x0b' + mapped.to_bytes(4,'big') + b'\x30'
                    expected.append(mapped)
        elif 5 <= op <= 7:
            targets = [at+n+1+uint(at+1,n)]
            raw = b'\x07\0\0\0'
        elif 0x10 <= op <= 0x1c or 0x20 <= op <= 0x22:
            targets = [at+n+1,at+n+1+code[at+n]]
            raw = raw[:-1]+b'\x04'+b'\x07\0\0\0'*2
        elif 0x23 <= op <= 0x25:
            targets = [at+7+uint(at+3,2), at+7+uint(at+5,2)]
            raw = raw[:3]+b'\0\0\0\x04'+b'\x07\0\0\0'*2
        nodes.append((at,raw,targets))
        locations[at] = size
        size += len(raw)
        at += n+1
    out = bytearray()
    for old, raw, targets in nodes:
        start = len(out)
        out.extend(raw)
        if targets:
            stub = start if len(targets)==1 else start+len(raw)-8
            for target in targets:
                if target not in locations:
                    raise ValueError('MOPP jump does not land on an instruction')
                delta = locations[target]-(stub+4)
                if not 0 <= delta < (1<<24):
                    raise ValueError('Relocated MOPP jump exceeds 24 bits')
                out[stub+1:stub+4] = delta.to_bytes(3,'big')
                stub += 4
    actual = [key for _,_,key in terminals(out)]
    if sorted(actual) != sorted(expected):
        raise ValueError('Relocated MOPP terminals differ from intended keys')
    return bytes(out)
