"""Stage fixed collision-only object candidates for converted Reach BSP hulls.

The source BSP retains authored rendering and detailed ray collision. These
objects supply convex Havok bodies only. Runtime acceptance is required before
enabling the matching BSP-physics suppression or deploying a converted map.
"""
import struct
from reach_fixed_hull import stage_fixed_hull
from reach_compound_hull import stage_compound_hull


def stage_hull_object(registry,hull,material):
    return _stage_physics_object(registry,stage_fixed_hull(registry.builder,hull,material))


def stage_compound_hull_object(registry,hulls,materials):
    return _stage_physics_object(registry,stage_compound_hull(registry.builder,hulls,materials))


def _stage_physics_object(registry,phmo):
    b,c=registry.builder,registry.cache
    name=r'objects\levels\dlc\sandbox\sand_wall\sand_wall'
    def donor(group,size):
        rows=[t['offset'] for i,t in c.tags.items() if t['group']==group and c.name(i)==name]
        if len(rows)!=1:raise ValueError('Fixed hull object donor missing/ambiguous')
        return bytearray(c.data[rows[0]:rows[0]+size])
    body_pointer=struct.unpack_from('>I',phmo,92)[0]
    body=b.read(body_pointer,176)
    center=struct.unpack_from('>3f',body,8);radius=struct.unpack_from('>f',body,20)[0]
    physics,physics_address=registry.newtag('phmo',phmo)
    model=donor('hlmt',392)
    if struct.unpack_from('>I',model,172)[0]!=1:
        raise ValueError('Expected single model node for fixed hull')
    # Null references retain valid group codes but never point at the wall's
    # render/collision data. Detailed ray tests remain in the source BSP.
    for offset in (0,16,32,84):struct.pack_into('>I',model,offset+12,0xffffffff)
    struct.pack_into('>I',model,60,physics)
    model[160:172]=bytes(12)  # No model collision regions without a coll tag.
    object_data=struct.pack('>hh4f',1,0,*center,radius)
    struct.pack_into('>III',model,188,1,b.alloc(object_data),0)
    model_id,model_address=registry.newtag('hlmt',model)
    obj=donor('bloc',268)
    if struct.unpack_from('>h',obj)[0]!=10:raise ValueError('Expected native crate wrapper')
    struct.pack_into('>f3f',obj,4,radius,*center)
    struct.pack_into('>I',obj,64,model_id)
    obj[236:248]=bytes(12)  # Authored collision is not a Forge-spawnable item.
    object_id,object_address=registry.newtag('bloc',obj)
    return dict(object=object_id,model=model_id,physics=physics,
                object_address=object_address,model_address=model_address,physics_address=physics_address)
