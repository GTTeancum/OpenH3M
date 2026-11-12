"""Read the retail marker effect through Assembly's Halo4 schemas; no cache edits."""
import contextlib
import io
import json
import struct
import xml.etree.ElementTree as ET
with contextlib.redirect_stdout(io.StringIO()):
    import audit_marker_visual as cache

def fields(schema, base, depth=0):
    result={}
    for node in schema:
        if 'offset' not in node.attrib: continue
        name=node.get('name','')
        at=base+int(node.get('offset'),16)
        key=name+'@'+node.get('offset')
        kind=node.tag.lower()
        if kind=='tagblock':
            count=cache.u(at)
            if count>1024: raise ValueError((name,'invalid block count',count))
            if count and depth<8:
                start=cache.offset(cache.u(at+4)); stride=int(node.get('elementSize'),16)
                result[key]=[fields(node,start+i*stride,depth+1) for i in range(count)]
        elif kind=='tagref':
            datum=cache.u(at+12)
            if datum!=0xffffffff:
                target=cache.tags[datum&65535]
                assert cache.data[at:at+4].decode()==target['group']
                assert datum>>16==target['salt']
                result[key]=dict(index=datum&65535,group=target['group'],name=target['name'])
        elif kind=='dataref':
            size=cache.u(at)
            if size:
                start=cache.offset(cache.u(at+12))
                result[key]=cache.data[start:start+size].hex()
        elif name!='Unknown':
            formats={'float32':'>f','rangef':'>2f','ranged':'>2f','point3':'>3f',
                'vector3':'>3f','degree':'>f','degree2':'>2f','int32':'>i',
                'uint32':'>I','datum':'>I','stringid':'>I','flags32':'>I','flags16':'>H',
                'flags8':'>B','int16':'>h','uint16':'>H','int8':'>b','uint8':'>B',
                'enum8':'>B','enum16':'>H','enum32':'>I','colorf':'>4f' if node.get('alpha')=='true' else '>3f'}
            if kind in formats:
                value=struct.unpack_from(formats[kind],cache.data,at)
                value=value[0] if len(value)==1 else value
                if kind.startswith('enum'):
                    value={'value':value,'label':next((x.get('name') for x in node if int(x.get('value'),0)==value),None)}
                result[key]=value
    return result

report={}
for index in [16657,16658,16660,7748,16659,16661,419,341]:
    tag=cache.tags[index]
    schema=ET.parse(cache.RESEARCH/('reference/Halo4-'+tag['group']+'.xml')).getroot()
    report[index]={'name':tag['name'],'fields':fields(schema,tag['offset'])}
out=cache.RESEARCH/'isolated/marker-effect-fields.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(out)
