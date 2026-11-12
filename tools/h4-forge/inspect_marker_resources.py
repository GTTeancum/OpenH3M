"""Trace retail H4 marker bitmap resource pages using the Halo4 zone layout."""
import contextlib
import io
import json
import struct
with contextlib.redirect_stdout(io.StringIO()):
    import audit_marker_visual as c

def block(at,stride):
    count=c.u(at)
    if count>65535:raise ValueError('Unexpected block count')
    start=c.offset(c.u(at+4)) if count else 0
    if start+count*stride>len(c.data):raise ValueError('Truncated block')
    return [start+i*stride for i in range(count)]
def h(at):return struct.unpack_from('>h',c.data,at)[0]

zone=next(t['offset'] for t in c.tags.values() if t['group']=='zone')
resources=block(zone+0x58,0x44)
segments=block(zone+0x4c,0x18)
pages=block(zone+0x34,0x58)
files=[c.data[a:a+256].split(b'\0')[0].decode('ascii') for a in block(zone+0x28,0x108)]
if not segments:
    layout=next(t['offset'] for t in c.tags.values() if t['group']=='play')
    segments=block(layout+0x30,0x18)
    pages=block(layout+0x18,0x58)
    files=[c.data[a:a+256].split(b'\0')[0].decode('ascii') for a in block(layout+0xc,0x108)]
report=[]
for index in [7748,16659,16661,419,341]:
    tag=c.tags[index];bitmaps=block(tag['offset']+0x7c,0x2c);hardware=block(tag['offset']+0xa8,8)
    if len(bitmaps)!=1 or len(hardware)!=1:raise ValueError('Unexpected marker bitmap count')
    datum=c.u(hardware[0]);resource=resources[datum&65535]
    if c.u(resource+12)&65535!=index:raise ValueError('Bitmap resource owner mismatch')
    if struct.unpack_from('>H',c.data,resource+0x10)[0]!=datum>>16:raise ValueError('Resource salt mismatch')
    segment_index=h(resource+0x1a)
    if not 0<=segment_index<len(segments):
        raise ValueError(dict(bitmap=index,segment=segment_index,segments=len(segments),pages=len(pages),resources=len(resources),
            layouts=[t for t in c.tags.values() if t['group']=='play']))
    segment=segments[segment_index]
    parts=[]
    for n in range(3):
        pageindex=h(segment+0xc+n*2)
        if pageindex<0:continue
        page=pages[pageindex];shared=h(page+4)
        parts.append(dict(part=n,page=pageindex,offset=c.u(segment+n*4),size_index=h(segment+0x12+n*2),
            codec=c.data[page+3],shared=files[shared] if shared>=0 else None,
            block=c.u(page+8),compressed=c.u(page+12),uncompressed=c.u(page+16),crc=hex(c.u(page+20))))
    report.append(dict(index=index,name=tag['name'],resource=hex(datum),root=hex(c.u(resource+0x1c)),parts=parts))
out=c.RESEARCH/'isolated/marker-resource-pages.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
