"""Keep Dune's custom plasma trail with a scoped native H3 blend fallback."""
import hashlib
from dune_flare import SCENARIO, BUILD, SOURCE_SHA256
NAME = r'objects\vehicles\c_turret_ap\weapon\projectile'
TEMPLATE = r'shaders\contrail_templates\_0_1_1_0'
NOTE = ('Dune Creep plasma-turret contrail retains authored trail geometry, lifetime, color, texture and fog; '
        'native source-alpha-weighted additive replaces additive blend, so translucent portions may dim. '
        'Projectile damage/physics and weapon behavior retained; not visual equivalence.')


def matches(source, post, group, template):
    if group!='cntl' or template!=TEMPLATE or [source.name(k) for k,t in source.tags.items() if t['group']=='scnr']!=[SCENARIO]:
        return False
    for k,t in source.tags.items():
        if t['group']=='cntl' and source.name(k)==NAME:
            if any(post in source.block(row+0x158,140) for row in source.block(t['offset'],0x26c)):
                if bytes(source.data[0xa0:0xc0]).split(b'\0',1)[0]!=BUILD.encode() or hashlib.sha256(source.data).hexdigest()!=SOURCE_SHA256:
                    raise ValueError('Dune projectile source changed')
                return True
    return False


def update_root(importer, source_root, payload):
    import struct
    s,b=importer.source,importer.builder
    source_rows=s.block(source_root,0x26c)
    matched=[]
    for index,row in enumerate(source_rows):
        posts=s.block(row+0x158,140)
        if (len(posts)==1 and importer.materials.particle_aliases.get(posts[0])
                and importer.materials.particle_aliases[posts[0]][0]=='_0_8_1_0'
                and matches(s,posts[0],'cntl',s.name(s.u(posts[0]+12)&65535))):
            options=[s.unpack('h',r)[0] for r in s.block(row+0x140,2)]
            if options!=[0,1,1,0]:raise ValueError('Dune contrail source options changed')
            matched.append(index)
    if not matched:return payload
    count,pointer=struct.unpack_from('>II',payload)
    if count!=len(source_rows):raise ValueError('Dune contrail system count changed')
    for index in matched:
        n,p=struct.unpack('>II',b.read(pointer+index*0x26c+0x140,8))
        if n!=4:raise ValueError('Dune contrail native option count changed')
        b.put(p,'4h',0,8,1,0)
    return payload
