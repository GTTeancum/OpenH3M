"""Powerhouse's additive two-detail dust as two native animated draws.

Source albedo = K*base.rgb*((1-base.a)*detail1 + base.a*detail2).
K is the shared DETAIL_MULTIPLIER (4.59479 in the shader reference); both native
draws apply the same factor, so it is not baked into the weighted base images.
Bake only the two static base weights; each detail keeps its authored UV motion.
No collision/vertex/index data changes. Requires split_sky_parts on its sole model.
"""
import struct
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from encode_bitmap import encode_bitmap_base
from tag_metadata import MetadataConverter
from material_animation import convert_material_animation

PREFIX = 'levels\\multi\\s3d_powerhouse\\sky_settlement\\'
NAMES = {PREFIX+'shaders\\s3d_dust_devils', PREFIX+'shaders\\s3d_valley_floor_dust'}
TEMPLATE = r'shaders\halogram_templates\_0_4_1_0_0_0_1'


def weighted_bases(i, tag):
    cache = getattr(i, 'dust_weighted_bases', {})
    if tag in cache:return cache[tag]
    source=i.materials.bitmaps
    info=source.info(tag)
    if len(info)!=1 or info[0]['format']!=16 or (info[0]['width'],info[0]['height'])!=(256,256):
        raise ValueError('Dust mask changed; re-audit required')
    data=source.pixels(tag)
    rgba=np.asarray(Image.frombytes('RGBA',(256,256),data[:65536],'bcn',3)).astype(np.float32)/255
    row=i.source.block(i.source.tags[tag]['offset']+96,56)[0]
    curve=i.source.data[row+21]
    rgb=rgba[:,:,:3]
    if curve in (1,5):rgb=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    elif curve!=3:raise ValueError('Unsupported dust mask sampling curve')
    result=[]
    for weight in (1-rgba[:,:,3:4],rgba[:,:,3:4]):
        level=rgb*weight; blocks=[]
        while True:
            encoded=np.where(level<=.0031308,level*12.92,1.055*np.maximum(level,0)**(1/2.4)-.055)
            pixels=np.full((*level.shape[:2],4),255,np.uint8)
            pixels[:,:,:3]=np.rint(np.clip(encoded,0,1)*255).astype(np.uint8)
            blocks.append(pixels[:,:,[2,1,0,3]].tobytes())
            if level.shape[0]==1:break
            level=level.reshape(level.shape[0]//2,2,level.shape[1]//2,2,3).mean(axis=(1,3))
        class Baked:
            c=i.source
            def info(self,tag):return [dict(width=256,height=256,format=11,mips=9,kind=0,curve=1)]
            def pixels(self,tag,index=0):return b''.join(blocks)
        result.append(i.materials.bitmap_resource(*encode_bitmap_base(Baked(),tag,preserve_color_mips=True)))
    cache[tag] = result
    i.dust_weighted_bases = cache
    return result


def import_dust(i, datum):
    s,b,c=i.source,i.builder,i.registry.cache
    name=s.name(datum&65535)
    if name not in NAMES:raise ValueError('Unreviewed dust material')
    root=s.tags[datum&65535]['offset'];posts=s.block(root+40,140)
    if len(posts)!=1 or s.u(root+28):raise ValueError('Dust material root changed')
    post=posts[0]
    if s.name(s.u(post+12)&65535)!=r'shaders\halogram_templates\_1_4_1_0_0_0_0_0_0':
        raise ValueError('Dust permutation changed')
    textures,names=i.materials.parameters(s,i.source_strings,post)
    expected=['base_map','detail_map','detail_map2','self_illum_color','self_illum_intensity']
    if textures!=expected[:3] or names!=expected:raise ValueError('Dust parameter layout changed')
    values=[s.unpack('4f',r) for r in s.block(post+28,16)]
    if values[0]!=(1.,1.,0.,0.) or s.u(post+40) or s.u(post+52):raise ValueError('Unexpected dust constants')
    samplers=s.block(post+16,28)
    for j,row in enumerate(samplers):
        image,address,filtering,comparison,external,transform,pad,animation,pad2=s.unpack('h4BbBhH',row+16)
        if image or comparison or external or transform!=j or pad or pad2:
            raise ValueError('Unsupported dust sampler')
    # Only detail transforms animate: a moving base mask would invalidate weights.
    for row in s.block(post+80,4):
        if s.unpack('HBB',row)[2] not in (1,2):raise ValueError('Dust animates a non-detail parameter')
    lookup={(t['group'],c.name(k)):(t['salt']<<16)|k for k,t in c.tags.items()}
    template=lookup['rmt2',TEMPLATE];definition=lookup['rmdf',r'shaders\halogram']
    masks=weighted_bases(i,s.u(samplers[0]+12)&65535)
    outputs=[]
    ss=ET.parse(i.reference/'mcc/rmhg.xml').getroot();ds=ET.parse(i.reference/'plugins/rmhg.xml').getroot()
    for layer in range(2):
        output=bytearray(132);output[:16]=b'rmt2'+bytes(8)+struct.pack('>I',template)
        tex=bytearray()
        for j,source_index in enumerate((0,layer+1)):
            row=samplers[source_index]
            bitmap=masks[layer] if j==0 else i.materials.bitmap(s.u(row+12))
            image,address,filtering,comparison,external,transform,pad,animation,pad2=s.unpack('h4BbBhH',row+16)
            tex.extend(b'bitm'+bytes(8)+struct.pack('>IhBBBbH',bitmap,0,address,filtering,0,j,0))
        struct.pack_into('>III',output,16,2,b.alloc(tex),0)
        constants=[values[0],values[layer+1],(1.,)*4,values[3],values[4],(1.,)*4,(1.,)*4,(1.,)*4]
        struct.pack_into('>III',output,28,8,b.alloc(b''.join(struct.pack('>4f',*v) for v in constants)),0)
        queries=s.unpack('III8h',post+104)
        if queries!=(1,0,0,-1,0,-1,-1,-1,-1,-1,-1):raise ValueError('Dust query flags changed')
        struct.pack_into('>III8h',output,104,*queries)
        convert_material_animation(i.materials,post,output,
            aliases={'detail_map2':'detail_map'} if layer else {},
            split_exclusions=('detail_map' if layer else 'detail_map2',))
        def reference(value):
            if value!=s.u(root+12):raise ValueError('Unexpected dust root dependency')
            return 'rmdf',definition
        conv=MetadataConverter(s,b,i.source_strings,i.target_strings,reference,
            special_block=lambda at,sf,df,path:bytes(output) if sf.get('name')=='Postprocess' else None)
        payload=bytearray(conv.convert(root,ss,ds,'rmhg:'+name))
        struct.pack_into('>III',payload,16,7,b.alloc(struct.pack('>7h',0,4,1,0,0,0,1)),0)
        owner,_=i.registry.newtag('rmhg',payload);outputs.append(owner)
    i.resolved['rmhg',name]='rmhg',outputs[0]
    if not hasattr(i,'dust_splits'):i.dust_splits={}
    i.dust_splits[outputs[0]]=outputs[1]
    i.added.append({'group':'rmhg','source':name,'two_additive_draws':[hex(x) for x in outputs],
                    'source_detail_animations_retained':True,'weighted_base_bitmaps':2,
                    'native_visuals_verified':False,'approximation':'ARGB8 mask weighting and filtering; native two-draw accumulation needs visual validation'})
    return 'rmhg',outputs[0]


def split_sky_parts(i, name, payload):
    if name!=PREFIX+'sky_settlement':return payload
    b=i.builder;payload=bytearray(payload)
    count,pointer=struct.unpack_from('>II',payload,72)
    materials=bytearray(b.read(pointer,count*36)); mapping={}
    for j in range(count):
        datum=struct.unpack_from('>I',materials,j*36+12)[0]
        if datum not in getattr(i,'dust_splits',{}):continue
        mapping[j]=len(materials)//36
        new=bytearray(materials[j*36:(j+1)*36]);struct.pack_into('>I',new,12,i.dust_splits[datum]);materials.extend(new)
    if len(mapping)!=2:raise ValueError('Expected both Powerhouse dust materials')
    struct.pack_into('>III',payload,72,len(materials)//36,b.alloc(materials),0)
    n,ptr=struct.unpack_from('>II',payload,104);meshes=bytearray(b.read(ptr,n*76));added=0
    for mi in range(n):
        pc,pp=struct.unpack_from('>II',meshes,mi*76);sc,sp=struct.unpack_from('>II',meshes,mi*76+12)
        parts=bytearray(b.read(pp,pc*16));subs=bytearray(b.read(sp,sc*8))
        for pi in range(pc):
            part=bytearray(parts[pi*16:(pi+1)*16]);material=struct.unpack_from('>h',part)[0]
            if material not in mapping:continue
            if mi!=8 or part[12:14]!=bytes((2,0)):raise ValueError('Dust mesh layout changed')
            start,length=struct.unpack_from('>hH',part,8);new_index=len(parts)//16
            struct.pack_into('>h',part,0,mapping[material]);struct.pack_into('>h',part,8,len(subs)//8)
            for si in range(start,start+length):
                sub=bytearray(subs[si*8:(si+1)*8])
                if struct.unpack_from('>h',sub,4)[0]!=pi:raise ValueError('Dust subpart owner mismatch')
                struct.pack_into('>h',sub,4,new_index);subs.extend(sub)
            parts.extend(part);added+=1
        if len(parts)>pc*16:
            struct.pack_into('>III',meshes,mi*76,len(parts)//16,b.alloc(parts),0)
            struct.pack_into('>III',meshes,mi*76+12,len(subs)//8,b.alloc(subs),0)
    if added!=2:raise ValueError('Expected exactly two additional sky draws')
    struct.pack_into('>III',payload,104,n,b.alloc(meshes),0)
    i.added.append({'group':'mode','source':name,'additional_dust_parts':added,'vertex_index_resources_unchanged':True})
    i.dust_parts_staged=True
    return payload
