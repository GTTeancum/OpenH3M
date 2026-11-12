"""Translate the two ReXGlue-disassembled H4 marker pixel programs to private HLSL.

This deliberately rejects unsupported instructions instead of approximating them.
Generated shader code remains in ignored work/, never in the source tree.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'work/h4-forge-research/isolated/marker-shaders'


def source(value):
    value = re.sub(r'r_abs\[(\d+)\](\.[xyzw]+)?', lambda m: f'abs(r[{m[1]}]{m[2] or ""})', value)
    value = re.sub(r'\br(\d+)\b', r'r[\1]', value)
    return re.sub(r'\bc(\d+)\b', r'c[\1]', value)


def destination(value, result, fetch=False):
    match = re.fullmatch(r'(r\d+|oC0)(?:\.([xyzw_]+))?', value)
    if not match:
        raise ValueError(f'Unsupported destination {value}')
    register, mask = match.groups()
    register = 'color' if register == 'oC0' else source(register)
    mask = mask or 'xyzw'
    return [f'{register}.{"xyzw"[i]} = {result}.{component if fetch else "xyzw"[i]};'
            for i, component in enumerate(mask) if component != '_']


def instruction(text):
    text = text.strip()
    predicate = None
    if text.startswith(('(p0)', '(!p0)')):
        predicate, text = text.split(None, 1)
    operation, operands = text.split(None, 1)
    operands = [part.strip() for part in operands.split(',')]
    return predicate, operation, operands


def condition(predicate):
    return 'pred' if predicate == '(p0)' else '!pred'


def alu(vector, scalar):
    predicate, opcode, operands = instruction(vector)
    target, *args = operands
    args = list(map(source, args))
    saturated = opcode.endswith('_sat')
    opcode = opcode.removesuffix('_sat')
    a = args[0]
    if opcode == 'add': value = f'({a} + {args[1]})'
    elif opcode == 'mul': value = f'H4Multiply({a}, {args[1]})'
    elif opcode == 'max': value = f'max({a}, {args[1]})'
    elif opcode == 'mad': value = f'(H4Multiply({a}, {args[1]}) + {args[2]})'
    elif opcode in ('sgt', 'sge', 'seq'):
        operator = {'sgt': '>', 'sge': '>=', 'seq': '=='}[opcode]
        value = f'float4({a} {operator} {args[1]})'
    elif opcode == 'dp3': value = f'H4Dot({a}, {args[1]}, 3).xxxx'
    elif opcode == 'dp2add': value = f'(H4Dot({a}, {args[1]}, 2) + ({args[2]}).x).xxxx'
    elif opcode in ('cndgt', 'cndeq'):
        operator = '>' if opcode == 'cndgt' else '=='
        value = f'({a} {operator} 0 ? {args[1]} : {args[2]})'
    else: raise ValueError(f'Unsupported vector operation {opcode}')
    if saturated: value = f'saturate({value})'
    lines = ['{', f'float4 vectorResult = {value};']
    scalar_store = []
    if scalar:
        sp, sop, sopargs = instruction(scalar)
        if sp != predicate:
            raise ValueError('Different paired ALU predicates')
        scalar_target, *sargs = sopargs
        sargs = list(map(source, sargs))
        sat = sop.endswith('_sat')
        sop = sop.removesuffix('_sat')
        if sop != 'retain_prev':
            x = sargs[0]
            if sop in ('adds', 'muls', 'maxs'):
                first, second = f'({x}).x', f'({x}).y'
                expression = f'max({first},{second})' if sop == 'maxs' else f'({first} {"+" if sop == "adds" else "*"} {second})'
                if sop == 'muls': expression = f'H4MultiplyScalar({first},{second})'
            elif sop in ('addsc', 'mulsc', 'subsc'):
                expression = f'({x} {dict(addsc="+",mulsc="*",subsc="-")[sop]} {sargs[1]})'
                if sop == 'mulsc': expression = f'H4MultiplyScalar({x},{sargs[1]})'
            elif sop == 'adds_prev': expression = f'({x}+previousScalar)'
            elif sop == 'rcp': expression = f'(1.0/{x})'
            elif sop == 'frcs': expression = f'frac({x})'
            elif sop in ('sgts', 'sges'):
                expression = f'float({x} {">" if sop == "sgts" else ">="} 0)'
            elif sop in ('setp_eq', 'setp_ne'):
                lines.append(f'bool nextPredicate = ({x} {"==" if sop == "setp_eq" else "!="} 0);')
                expression = 'float(!nextPredicate)'
            else: raise ValueError(f'Unsupported scalar operation {sop}')
            lines.append(f'float scalarResult = {expression};')
            scalar_store.append('previousScalar = scalarResult;')
            scalar_store += destination(scalar_target, '(saturate(scalarResult)).xxxx' if sat else 'scalarResult.xxxx')
            if sop.startswith('setp_'): scalar_store.append('pred = nextPredicate;')
    stores = destination(target, 'vectorResult') + scalar_store
    if predicate:
        # Both ALU operations read pre-instruction registers/predicate and only
        # then commit. In particular scalar writes cannot affect vector inputs.
        lines += [f'if ({condition(predicate)}) {{'] + stores + ['}']
    else: lines += stores
    return lines + ['}']


def translate(text):
    blocks = []
    labels = {}
    pending_labels = []
    current_instruction = None
    for line in text.splitlines():
        label = re.search(r'\blabel (L\d+)', line)
        if label:
            pending_labels.append(label[1])
            continue
        cf = re.match(r'/\*\s*(\d+)\.(\d+)\s*\*/\s*(.*?)\s*(?://.*)?$', line)
        if cf:
            index = 2 * int(cf[1]) + int(cf[2])
            labels.update((name, index) for name in pending_labels)
            pending_labels.clear()
            blocks.append([index, cf[3].strip(), []])
            current_instruction = None
            continue
        op = re.match(r'/\*\s*\d+\s*\*/\s*(.*)', line)
        if op:
            current_instruction = [op[1].strip(), None]
            blocks[-1][2].append(current_instruction)
        elif line.strip().startswith('+'):
            current_instruction[1] = line.strip()[1:].strip()
        elif line.strip():
            if current_instruction is None or current_instruction[0] != 'serialize':
                raise ValueError(f'Unparsed disassembly line: {line}')
            current_instruction[0] = line.strip()
    lines = ['// Generated from original ReXGlue disassembly. Do not hand edit.',
             '// Xenos/D3D9 zero multiplication is defined even with an infinite reciprocal.',
             'float H4MultiplyScalar(float a,float b) { return (a==0 || b==0)?0:a*b; }',
             'float4 H4Multiply(float4 a,float4 b) { return (a==0 || b==0)?0:a*b; }',
             'float H4Dot(float4 a,float4 b,uint n) { float4 p=H4Multiply(a,b); float s=0; [unroll] for(uint i=0;i<n;++i)s+=p[i]; return s; }',
             'float4 H4MarkerPixel(float4 c[256], uint b[8], float4 inputs[8]) {',
             'float4 r[8]; [unroll] for (uint j=0;j<8;++j) r[j]=inputs[j];',
             'float4 color=0; float previousScalar=0; bool pred=false; uint pc=0;']
    for index, cf, instructions in blocks:
        lines += [f'if (pc == {index}) {{', f'pc={index+1};']
        if cf.startswith(('exec', 'cexec')):
            conditional = cf.startswith('cexec')
            if conditional:
                test = cf.split()[1]
                match = re.fullmatch(r'(!?)b(\d+)', test)
                if not match: raise ValueError(cf)
                bit = int(match[2])
                lines += [f'if ({"!" if match[1] else ""}((b[{bit//32}] & {1 << (bit%32)}u)!=0)) {{']
            for vector, scalar in instructions:
                pred, opcode, operands = instruction(vector)
                if opcode.startswith('tfetch'):
                    target, uv, sampler, *_ = operands
                    if pred or opcode not in ('tfetch2D', 'tfetch3D'):
                        raise ValueError(vector)
                    coords = source(uv)
                    if opcode == 'tfetch2D': coords = f'float3({coords},0)'
                    lines += ['{', f'float4 fetched = H4Fetch({int(sampler[2:])},{coords});']
                    lines += destination(target, 'fetched', fetch=True) + ['}']
                else: lines += alu(vector, scalar)
            if conditional: lines += ['}']
            if cf == 'exece': lines += ['return color;']
        elif cf.startswith(('cjmp', 'jmp', '(p0) jmp', '(!p0) jmp')):
            parts = cf.replace(',', '').split()
            jump = labels[parts[-1]]
            if jump <= index: raise ValueError('Unexpected loop in marker pixel program')
            if parts[0] == 'cjmp':
                match = re.fullmatch(r'(!?)b(\d+)', parts[1]); bit = int(match[2])
                test = f'{"!" if match[1] else ""}((b[{bit//32}] & {1 << (bit%32)}u)!=0)'
                lines += [f'if ({test}) pc={jump};']
            elif parts[0].startswith('('): lines += [f'if ({condition(parts[0])}) pc={jump};']
            else: lines += [f'pc={jump};']
        elif cf not in ('cnop', 'alloc colors'): raise ValueError(f'Unsupported control flow {cf}')
        lines += ['}']
    return '\n'.join(lines + ['return color;', '}']) + '\n'


if __name__ == '__main__':
    manifest = []
    for material in (331, 16):
        path = DIRECTORY / f'{material}-ps-0.ucode.txt'
        output = DIRECTORY / f'{material}-ps.generated.hlsl'
        output.write_text(translate(path.read_text()))
        manifest.append(dict(material=material, disassembly_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             output=output.name, output_sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
    (DIRECTORY / 'translated.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Translated both original marker pixel programs; GPU/reference validation remains required.')
