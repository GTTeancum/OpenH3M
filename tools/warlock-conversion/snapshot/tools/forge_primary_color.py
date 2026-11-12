"""Route the existing native detail-emission color register to object primary color.

H3's render-method option enum identifies change-color-primary as extern 14.
Shader instructions, textures, constant tables and entry points stay unchanged.
"""
import struct


def reroute(passes, routes, color_index):
    output_passes=bytearray();output_routes=bytearray();changes=[]
    for index,original in enumerate(passes):
        p=bytearray(original);usages=[]
        for usage in range(12):
            packed=struct.unpack_from('>H',p,usage*2)[0]
            start,count=packed&1023,packed>>10
            if start+count>len(routes):raise ValueError('Primary-color route outside table')
            usages.append(list(routes[start:start+count]))
        moved=[r for r in usages[4] if struct.unpack('>HBB',r)[1]==color_index]
        if len(moved)>1:raise ValueError('Ambiguous native emission color register')
        if moved:
            register,_,flags=struct.unpack('>HBB',moved[0])
            if any(struct.unpack('>HBB',r)[0]==register for r in usages[10]):
                raise ValueError('Emission register already has an extern binding')
            usages[4]=[r for r in usages[4] if r not in moved]
            usages[10].append(struct.pack('>HBB',register,14,flags))
            changes.append(dict(pass_index=index,register=register,flags=flags,source_index=color_index,extern=14))
        for usage,rows in enumerate(usages):
            start=len(output_routes)//4
            if start>1023 or len(rows)>63:raise ValueError('Primary-color routing exceeds native limits')
            struct.pack_into('>H',p,usage*2,start|(len(rows)<<10))
            output_routes.extend(b''.join(rows))
        output_passes.extend(p)
    if not changes:raise ValueError('Native template has no self-illumination color routes')
    return output_passes,output_routes,changes


def bind_primary_color(materials,post,names):
    b,registry=materials.builder,materials.registry
    post=bytearray(post);datum=struct.unpack_from('>I',post,12)[0]
    memo=getattr(materials,'_primary_color_templates',{})
    if datum not in memo:
        address=struct.unpack_from('>I',registry.tags,(datum&65535)*8+4)[0]
        root=bytearray(b.read(address,132))
        if struct.unpack_from('>I',root,120)[0]:raise ValueError('Unexpected native platform subtemplates')
        def rows(offset,stride):
            count,pointer=struct.unpack_from('>II',root,offset)
            return [bytes(b.read(pointer+i*stride,stride)) for i in range(count)]
        constants=names[1]
        if constants.count('self_illum_color')!=1:raise ValueError('Missing unique native emission color')
        passes,routes,changes=reroute(rows(48,28),rows(60,4),constants.index('self_illum_color'))
        for offset,stride,payload in ((48,28,passes),(60,4,routes)):
            struct.pack_into('>III',root,offset,len(payload)//stride,b.alloc(payload),0)
        new_datum,_=registry.newtag('rmt2',root)
        memo[datum]=(new_datum,changes);materials._primary_color_templates=memo
    new_datum,changes=memo[datum]
    struct.pack_into('>I',post,12,new_datum)
    return post,changes
