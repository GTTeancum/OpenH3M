"""Keep the Sky Bridge light beam's LDR-only target and native particle bindings."""
import hashlib,json,re,struct
from pathlib import Path

def bind_ldr(materials, post, profile='particle-ldr-01'):
    directory=Path(__file__).resolve().parents[4]/'work/sky-bridge'/profile
    audit=json.loads((directory/'audit.json').read_text())
    raw=(directory/'default.bin').read_bytes();assembly=(directory/'default.asm').read_text()
    if hashlib.sha256(raw).hexdigest()!=audit['sha256'] or not audit['inputs_match'] or ('PsExportColorCount='+str(audit['color_exports'])) not in assembly:
        raise ValueError('LDR particle program changed')
    b,registry=materials.builder,materials.registry
    def address(datum):return struct.unpack_from('>I',registry.tags,(datum&65535)*8+4)[0]
    def rows(root,offset,stride):
        count,pointer=struct.unpack_from('>II',root,offset)
        return [bytes(b.read(pointer+j*stride,stride)) for j in range(count)]
    post=bytearray(post);root=bytearray(b.read(address(struct.unpack_from('>I',post,12)[0]),132));pixel=bytearray(b.read(address(struct.unpack_from('>I',root,28)[0]),32))
    programs=rows(pixel,20,80);entries=rows(pixel,4,2)
    if len(programs)!=1 or entries[0]!=b'\0\1' or any(e[1] for e in entries[1:]):raise ValueError('LDR particle donor entries changed')
    row=bytearray(programs[0]);original=[dict(name=materials.target_strings.text(struct.unpack_from('>I',r)[0]),register=struct.unpack_from('>H',r,4)[0],count=r[6],set=r[7]) for r in rows(row,40,8)]
    if any(r not in original for r in audit['registers']):raise ValueError('LDR particle fixed register mismatch')
    magic,debug_size,code_size=struct.unpack_from('>III',raw)
    if magic>>16!=0x102a or debug_size+code_size!=len(raw):raise ValueError('Invalid LDR particle binary')
    info=bytearray(40);struct.pack_into('>I',info,16,b.alloc(raw[debug_size:]));info.extend(raw[:debug_size]);row[:40]=bytes(40)
    reflection=b''.join(struct.pack('>IHBB',materials.target_strings.id_for_text(r['name']),r['register'],r['count'],r['set']) for r in audit['registers'])
    struct.pack_into('>III',row,40,len(audit['registers']),b.alloc(reflection),0);row[56:68]=bytes(12)
    struct.pack_into('>II',row,72,int(re.search(r'PsMaxReg=(\d+)',assembly).group(1))+1,b.alloc(info))
    struct.pack_into('>III',pixel,20,1,b.alloc(row),0);datum,_=registry.newtag('pixl',pixel);struct.pack_into('>I',root,28,datum)
    datum,_=registry.newtag('rmt2',root);struct.pack_into('>I',post,12,datum)
    return post
