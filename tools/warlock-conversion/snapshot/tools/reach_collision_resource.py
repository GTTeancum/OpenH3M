"""Assemble H3 collision resources and return explicit external physics obligations.

Only the reviewed Reach collision layout is accepted. The returned resource is
not a complete BSP: convex instances require native fixed wrappers, and the BSP
placement/physics resource still has to be converted and linked by the caller.
"""
import math
import struct
from reach_collision_sections import CollisionSections


def assemble_collision_resource(source,main_tree,instance_trees,spheres,
                                resolution_scales,convex_definitions,rebuilt_mopps=None,render_trees=None,main_geometry=None):
    arena=CollisionSections(source)
    reader=arena.reader
    if source.unpack('I',source.root+12)[0]:
        raise ValueError('Large Reach collision BSP requires explicit conversion')
    main=reader.headers(source.root,108)
    if len(main)!=1:raise ValueError('Expected one verified main collision tree')
    instances=reader.headers(source.root+24,324)
    expected=set(range(len(instances)))
    if set(spheres)!=expected or set(resolution_scales)!=expected:
        raise ValueError('Missing/extra native instance bounds or resolution scales')
    root=arena.allocate(bytes(32),True)
    main_at=arena.block(root,len(main),bytes(96*len(main)),96,True)
    arena.geometry(main[0],main_tree,main_at,geometry_override=main_geometry)
    instance_at=arena.block(root+12,len(instances),bytes(184*len(instances)),184,True)
    hulls=[];source_flags={};rebuilt_mopps=rebuilt_mopps or {};used_mopps=set()
    render_trees=render_trees or {};used_render_trees=set()
    for index,src in enumerate(instances):
        dst=instance_at+index*184
        sphere=spheres[index];scale=resolution_scales[index]
        if len(sphere)!=4 or not all(math.isfinite(v) for v in (*sphere,scale)) or sphere[3]<0 or scale<0:
            raise ValueError('Invalid native definition bound/resolution')
        flags=source.unpack('I',src+4)[0]
        # Preserve these source compiler flags in the obligation report; H3 has
        # no corresponding definition field. Runtime physics comes from the
        # separately converted instance resource, never from guessed flag bits.
        # Reflection additionally carries the diagnostic MiscoloredBsp bit and
        # definitions without SurfaceToTriangleRemapped. None of these flags
        # replaces serialized collision or the external physics obligation.
        if flags not in (4,5,6,16,18,20,21,22):raise ValueError('Unreviewed Reach definition flags')
        source_flags[index]=flags
        struct.pack_into('>I4f',arena.control,dst,source.unpack('I',src)[0],*sphere)
        arena.geometry(src+8,instance_trees.get(index),dst+20)
        if any(count for count,_ in reader.geometry(src+116).values()):
            raise ValueError('Nonempty secondary Reach geometry requires conversion')
        render=reader.headers(src+224,108)
        render_at=arena.block(dst+116,len(render),bytes(len(render)*96),96,True)
        for ordinal,geometry in enumerate(render):
            key=(index,ordinal)
            arena.geometry(geometry,render_trees.get(key),render_at+ordinal*96)
            if key in render_trees:used_render_trees.add(key)
        # BreakableSurfaceBits is an array of 32-bit bitvectors in both games.
        count,bits=reader.block(src+248,4)
        native_bits=b''.join(struct.pack('>I',v) for (v,) in struct.iter_unpack('<I',bits))
        arena.block(dst+140,count,native_bits,4)
        if index in rebuilt_mopps:
            if reader.headers(src+236,96) or not flags&16:
                raise ValueError('Rebuilt MOPP would replace existing/unreviewed source physics')
            arena.generated_mopp(rebuilt_mopps[index],dst+128,reader.geometry(src+8)['surfaces'][0])
            used_mopps.add(index)
        else:
            arena.mopps(src+236,dst+128)
        arena.mappings(src+296,src+308,dst+152)
        struct.pack_into('>hhf',arena.control,dst+176,*source.unpack('hh',src+320),scale)
        count,headers=reader.block(src+260,160)
        vectors=reader.block(src+272,48)[1];planes=reader.block(src+284,16)[1]
        if count:
            if index not in convex_definitions:raise ValueError('Convex definition has no external physics handoff')
            hulls.append(dict(definition=index,headers=bytes(headers),vectors=bytes(vectors),planes=bytes(planes)))
        elif vectors or planes:raise ValueError('Unowned convex payload')
    if {h['definition'] for h in hulls}!=set(convex_definitions):
        raise ValueError('Convex handoff set differs from source')
    if used_mopps!=set(rebuilt_mopps):raise ValueError('Rebuilt MOPP definition outside resource')
    if used_render_trees!=set(render_trees):raise ValueError('Expanded render tree outside resource')
    arena.validate()
    resource=dict(control=bytes(arena.control),raw=bytes(arena.raw),root=root,
                  fixups=arena.fixups,interops=[])
    return resource,dict(convex_hulls=hulls,source_definition_flags=source_flags,rebuilt_mopp_definitions=sorted(used_mopps),
                         requires_instance_physics_integration=True)
