"""Trace the original H4 Forge marker object and its visual dependencies, read-only."""
import bisect
import json
import struct
from pathlib import Path
from Crypto.Cipher import AES

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT/'work/h4-forge-research'
data = (RESEARCH/'disc2-assets/ca_forge_ravine.map').read_bytes()
def u(at): return struct.unpack_from('>I',data,at)[0]
def decrypt(at,size,password):
    key=bytes(v^0xa5 for v in password.encode()).ljust(16,b'\0')
    return AES.new(key,AES.MODE_CBC,bytes(v^0x3c for v in key)).decrypt(data[at:at+((size+15)//16)*16])[:size]
names=decrypt((u(0x2b8)+u(0x47c))&0xffffffff,u(0x2bc),'LetsAllPlayNice!')
name_indices=(u(0x2c0)+u(0x47c))&0xffffffff
segment=(u(0x484)+u(0x49c))&0xffffffff
base=u(0x2f8)
def offset(ptr):
    at=ptr-base+segment
    if not 0<=at<len(data): raise ValueError('Tag pointer outside cache')
    return at
ng,gp,nt,tp=struct.unpack_from('>4I',data,offset(u(0x10)))
groups=[data[offset(gp)+i*16:offset(gp)+i*16+4] for i in range(ng)]
tags={}
for i in range(nt):
    group,salt,ptr=struct.unpack_from('>HHI',data,offset(tp)+i*8)
    if group==65535 or ptr in (0,0xffffffff): continue
    start=u(name_indices+i*4)
    name=names[start:names.index(b'\0',start)].decode('utf8')
    tags[i]=dict(group=groups[group].decode(),salt=salt,offset=offset(ptr),name=name)
starts=sorted({t['offset'] for t in tags.values()})
forge=tags[16655]
assert forge['group']=='forg'
marker=u(forge['offset']+0x18)&65535
marker_root=tags[marker]['offset']
attachment_count=u(marker_root+0x13c)
if not 0<=attachment_count<=16:raise ValueError('Unexpected original marker attachment count')
attachment_root=offset(u(marker_root+0x140)) if attachment_count else 0
attachments=[]
for i in range(attachment_count):
    at=attachment_root+i*0x20
    datum=u(at+12);target=tags[datum&65535]
    if data[at:at+4].decode()!=target['group']:raise ValueError('Attachment group mismatch')
    attachments.append(dict(index=datum&65535,**target,marker_id=hex(u(at+0x10)),flags=data[at+0x15]))
print('SCHEMA-VERIFIED MARKER ATTACHMENTS',json.dumps(attachments))
queue=[(marker,0)];visited=set();report=[]
queue.extend((a['index'],1) for a in attachments)
while queue:
    index,depth=queue.pop(0)
    if index in visited:continue
    visited.add(index);tag=tags[index];start=tag['offset']
    end=starts[bisect.bisect_right(starts,start)] if start<starts[-1] else len(data)
    end=min(end,start+256*1024)
    refs=[]
    for at in range(start,end-15,4):
        group=data[at:at+4]
        if group not in groups:continue
        datum=u(at+12);target=tags.get(datum&65535)
        if datum==0xffffffff or not target or target['group'].encode()!=group:continue
        refs.append(dict(at=hex(at-start),datum=hex(datum),index=datum&65535,group=target['group'],name=target['name']))
        if depth<4:queue.append((datum&65535,depth+1))
    report.append(dict(index=index,depth=depth,**tag,candidate_references=refs))
    print(index,tag['group'],tag['name'])
    for ref in refs:print(' ',ref['at'],ref['group'],ref['index'],ref['name'])
(RESEARCH/'isolated/marker-visual-dependencies.json').write_text(json.dumps(dict(
    marker_index=marker,verified_attachments=attachments,
    note='candidate_references are heuristic address-span scans; validate each against its tag schema before use',
    candidate_graph=report),indent=2)+'\n')
