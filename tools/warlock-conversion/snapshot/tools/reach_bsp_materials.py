"""Resolve Reach collision materials to exact stock H3 material names.

Use H3's native coefficients under the stock-gameplay-asset policy. Reach may
store zero coefficients on an inherited material; do not copy those zeros into
a generated physics model. Layouts follow paired Assembly matg/sbsp schemas.
"""
import math
from string_ids import StringTable


def resolve_collision_materials(source,bsp,target,indices):
    source_strings,target_strings=StringTable(source),StringTable(target)
    sm=next(t['offset'] for t in source.tags.values() if t['group']=='matg')
    tm=next(t['offset'] for t in target.tags.values() if t['group']=='matg')
    source_globals=source.block(sm+0x48c,0x1a8)
    native={}
    for index,at in enumerate(target.block(tm+0x17c,0x170)):
        name=target_strings.text(target.u(at))
        if name in native:raise ValueError('Duplicate native material name')
        friction,restitution,density=target.unpack('3f',at+24)
        native[name]=dict(index=index,name=name,string_id=target.u(at),
                          friction=friction,restitution=restitution,density=density)
    slots=source.block(bsp['offset']+88,24)
    result={}
    for index in sorted(set(indices)):
        if not 0<=index<len(slots):raise ValueError('BSP material slot outside table')
        global_index=source.unpack('h',slots[index]+16)[0]
        if not 0<=global_index<len(source_globals):raise ValueError('Reach global material outside table')
        name=source_strings.text(source.u(source_globals[global_index]))
        if name not in native:raise ValueError(f'No exact native collision material: {name}')
        row=native[name]
        if any(not math.isfinite(row[k]) or row[k]<0 for k in ('friction','restitution','density')):
            raise ValueError('Invalid native material coefficients')
        result[index]=dict(row,source_global_index=global_index)
    return result
