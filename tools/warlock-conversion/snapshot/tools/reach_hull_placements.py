"""Append the verified High Noon convex instances as native fixed crates.

This does not suppress source BSP physics. A complete map build must pair the
returned source-instance list with that suppression, after runtime acceptance.
"""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from reach_instance_pose import placement_angles


def append_hull_placements(builder,scenario,placements,objects):
    schema=ET.parse(Path(__file__).resolve().parents[1]/'reference/plugins/scnr.xml').getroot()
    used=set()
    for field in schema:
        if field.tag!='tagblock':continue
        uid=next((e for e in field if e.get('name')=='Unique ID'),None)
        if uid is None:continue
        n,p=struct.unpack('>II',builder.read(scenario+int(field.get('offset'),0),8))
        stride=int(field.get('elementSize'),0);offset=int(uid.get('offset'),0)
        data=builder.read(p,n*stride) if n else b''
        if len(data)!=n*stride:raise ValueError('Existing scenario object array is truncated')
        used.update(struct.unpack_from('>I',data,i*stride+offset)[0] for i in range(n))
    def current(offset,stride):
        n,p=struct.unpack('>II',builder.read(scenario+offset,8))
        data=builder.read(p,n*stride) if n else b''
        if len(data)!=n*stride:raise ValueError('Truncated existing crate data')
        return n,bytearray(data)
    count,records=current(0x5e8,176);palette_count,palette=current(0x5f4,48)
    definitions=sorted({p['definition'] for p in placements})
    if palette_count+len(definitions)>32768:raise ValueError('Crate palette exceeds signed index width')
    indices={d:palette_count+i for i,d in enumerate(definitions)}
    # Validate all source poses before mutating the builder.
    poses={}
    if len({p['index'] for p in placements})!=len(placements):raise ValueError('Duplicate hull placement')
    for p in placements:
        if not p.get('convex_child_verified'):
            raise ValueError('Hull pose/physics requires additional conversion')
        bsp=p.get('bsp_index',0)
        if not isinstance(bsp,int) or not 0<=bsp<16:raise ValueError('BSP index exceeds native mask')
        poses[p['index']]=placement_angles(p['matrix'],p['scale'])
        if p['definition'] not in objects:raise ValueError('Missing staged hull object')
    for d in definitions:
        row=bytearray(48);struct.pack_into('>4sIII',row,0,b'bloc',0,0,objects[d]['object']);palette.extend(row)
    emitted=[];next_id=0
    for p in placements:
        while next_id in used:next_id+=1
        if next_id>=0xffffffff:raise ValueError('No free scenario object ID')
        used.add(next_id)
        row=bytearray(176)
        struct.pack_into('>hhI3f3ff',row,0,indices[p['definition']],-1,256,
                         *p['matrix'][9:12],*poses[p['index']],p['scale'])
        bsp=p.get('bsp_index',0)
        struct.pack_into('>H',row,50,1<<bsp)
        # Retail 82347CA8 intersects the compiled attach mask at +0x50 with
        # active BSPs before it calls placement preparation/object creation.
        # The editor's manual selection at +0x32 alone does not admit an object.
        struct.pack_into('>H',row,80,1<<bsp)
        struct.pack_into('>IhBB',row,56,next_id,bsp,10,0)
        row[64]=2  # Manual BSP policy.
        for offset in (66,70,146):struct.pack_into('>h',row,offset,-1)
        struct.pack_into('>h',row,108,4)  # No additional AI pathfinding obstacle.
        struct.pack_into('>h',row,130,8)  # Neutral.
        row[140]=1  # Do not replace under game-type remapping.
        records.extend(row)
        emitted.append(dict(source_instance=p['index'],source_bsp=bsp,scenario_index=count+len(emitted),unique_id=next_id))
    builder.put(scenario+0x5e8,'III',count+len(placements),builder.alloc(records),0)
    builder.put(scenario+0x5f4,'III',palette_count+len(definitions),builder.alloc(palette),0)
    return dict(placements=emitted,previous_count=count,previous_palette_count=palette_count,
                source_havok_instances_to_replace=[p['index'] for p in placements])
