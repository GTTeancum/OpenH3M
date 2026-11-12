"""Resolve the exact linked IssueDraw entry from its COFF symbol and relocations."""
import hashlib
import json
import struct
from pathlib import Path
import pefile

ROOT=Path(__file__).resolve().parents[2]
obj=ROOT/'work/rexglue-sdk/out/pacing-release/src/graphics/CMakeFiles/rexgpu-xenos.dir/d3d12/command_processor.cpp.obj'
dll=ROOT/'work/rexglue-sdk/out/win-amd64/rexgpu-xenos.dll'
b=obj.read_bytes()
machine,nsections,_,symbols,nsyms,opt,_=struct.unpack_from('<HHIIIHH',b)
if machine!=0x8664:raise ValueError('Expected AMD64 COFF object')
strings=symbols+nsyms*18
def name(at):
    raw=b[at:at+8]
    if raw[:4]==b'\0'*4:
        start=strings+struct.unpack_from('<I',raw,4)[0]
        return b[start:b.index(b'\0',start)].decode()
    return raw.split(b'\0')[0].decode()
found=[]
i=0
while i<nsyms:
    at=symbols+i*18
    if name(at).startswith('?IssueDraw@D3D12CommandProcessor@'):
        found.append(struct.unpack_from('<Ih',b,at+8))
    i+=1+b[at+17]
if len(found)!=1:raise ValueError('Expected one exact IssueDraw COFF symbol')
value,section=found[0]
s=20+opt+(section-1)*40
size,raw,relocs=struct.unpack_from('<III',b,s+16)
nrelocs=struct.unpack_from('<H',b,s+32)[0]
pattern=b[raw+value:raw+value+96]
mask=bytearray([1]*len(pattern))
for i in range(nrelocs):
    addr,_,kind=struct.unpack_from('<IIH',b,relocs+i*10)
    if value<=addr<value+len(pattern):
        width=8 if kind==1 else 4
        mask[addr-value:addr-value+width]=b'\0'*width
p=pefile.PE(str(dll))
text=next(s for s in p.sections if s.Name.startswith(b'.text'))
data=text.get_data();matches=[]
# Function starts are independently constrained by the linked unwind table.
for f in p.DIRECTORY_ENTRY_EXCEPTION:
    rva=f.struct.BeginAddress;off=rva-text.VirtualAddress
    if off<0 or off+len(pattern)>len(data):continue
    if all(not mask[j] or data[off+j]==v for j,v in enumerate(pattern)):matches.append(rva)
if len(matches)!=1:raise ValueError(f'Expected one linked prologue/unwind match, got {matches}')
r=dict(dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),rva=matches[0],
       symbol='D3D12CommandProcessor::IssueDraw',verified_bytes=sum(mask))
print(json.dumps(r))
