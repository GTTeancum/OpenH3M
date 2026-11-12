"""Extract the original near/far ALU block, retaining original paired writes.

The test microprogram adds control-flow scheduling only. Plasma ALUs 48 and
250..254, or ray ALUs 45 and 244..248, are copied verbatim from the retail code.
This verifies the fade block, not the rest of the particle vertex program.
"""
import hashlib
import json
import re
import struct
from translate_marker_materials import DIRECTORY, alu

import sys
material = int(sys.argv[1]) if len(sys.argv)>1 else 331
assert material in (331, 16)
code = (DIRECTORY/f'{material}-vs-3.ucode').read_bytes()
text = (DIRECTORY/f'{material}-vs-3.ucode.txt').read_text()
ops = {}
current = None
for line in text.splitlines():
    match = re.match(r'/\*\s*(\d+)\s*\*/\s*(.*)', line)
    if match:
        current = int(match[1]); ops[current] = [match[2].strip(), None]
    elif line.strip().startswith('+') and current is not None:
        ops[current][1] = line.strip()[1:].strip()

# The CF exec-end starts at ALU 1, executes six ALUs, then exits. The unused
# second CF is NOP. The original predicate setup uses c247.w=0, r3.x=1.
first = 250 if material == 331 else 244
indices = [48 if material == 331 else 45, *range(first, first+5)]
fragment = struct.pack('>3I', 1 | (6 << 12), 2 << 12, 0)
fragment += b''.join(code[i*12:(i+1)*12] for i in indices)
(DIRECTORY/f'{material}-fade-block.ucode').write_bytes(fragment)
lines = [
    '// Generated original H4 vertex fade instructions. Do not hand edit.',
    'float H4MultiplyScalar(float a,float b) {return (a==0||b==0)?0:a*b;}',
    'float4 H4Multiply(float4 a,float4 b) {return (a==0||b==0)?0:a*b;}',
    'float4 H4MarkerPixel(float4 c[256],uint b[8],float4 inputs[8]) {',
    'float4 r[16];[unroll]for(uint i=0;i<16;++i)r[i]=0;',
    '[unroll]for(uint j=0;j<8;++j)r[j]=inputs[j];',
    'float previousScalar=0;bool pred=true;']
for index in indices[1:]:
    vector, scalar = ops[index]
    if index == first:
        assert scalar is None and 'subsc ' in vector
        scalar = vector;vector = '(p0) max r0._, c0, c0'
    lines.append(f'// Original ALU {index}')
    lines.extend(alu(vector, scalar))
lines += ['return r[4];', '}']
output = DIRECTORY/f'{material}-fade-block.generated.hlsl'
output.write_text('\n'.join(lines)+'\n')
(DIRECTORY/f'{material}-fade-block-extraction.json').write_text(json.dumps(dict(
    original_vertex_sha256=hashlib.sha256(code).hexdigest(), original_indices=indices,
    fragment_sha256=hashlib.sha256(fragment).hexdigest(),
    hlsl_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
    limitations='Original fade ALU only; supplied camera-axis depth and constants. Original visibility/particle lifecycle not executed by this fragment.'), indent=2)+'\n')
print('Extracted original marker fade block for ReXGlue/HLSL comparison')
