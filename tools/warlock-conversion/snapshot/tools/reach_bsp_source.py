"""Resolve Reach BSP/lightmap references by scenario datum and BSP index."""

def scenario_geometry_bindings(cache):
    def resolve(datum, group, optional=False):
        if datum==0xffffffff and optional:return None
        tag=cache.tags.get(datum&65535)
        if tag is None or tag['salt']!=datum>>16 or tag['group']!=group:
            raise ValueError(f'Invalid Reach {group} reference {datum:#x}')
        return dict(tag,datum=datum)
    scenarios=[t for t in cache.tags.values() if t['group']=='scnr']
    if len(scenarios)!=1:raise ValueError('Expected one Reach scenario')
    scenario=scenarios[0]['offset']
    bsps=cache.block(scenario+0x50,0xac)
    lightmap=resolve(cache.u(scenario+0x708+12),'sLdT')
    lightrows=cache.block(lightmap['offset']+4,32)
    if len(lightrows)!=len(bsps):
        raise ValueError('Reach lightmap/BSP slot counts differ')
    result=[]
    for index,(row,lightrow) in enumerate(zip(bsps,lightrows)):
        bsp=resolve(cache.u(row+12),'sbsp')
        light=resolve(cache.u(lightrow+12),'Lbsp')
        mesh_count=cache.u(light['offset']+0x7c)
        resource=cache.u(light['offset']+0x10c)
        placeholder=mesh_count==0 and resource==0xffffffff
        if not placeholder and cache.unpack('h',light['offset']+2)[0]!=index:
            raise ValueError('Reach active lighting BSP index disagrees with slot')
        # Placeholder tags have default internal index zero. Their slot still
        # belongs to this BSP; do not relabel them as BSP zero or drop the BSP.
        result.append({'bsp_index':index,'bsp':bsp,'lighting':light,
                       'lighting_placeholder':placeholder})
    return result


def convert_bsp_geometry(cache, bsp_index, shared_paths):
    """Convert the scenario-selected resource; metadata translation is separate."""
    from reach_resource import ReachResource, convert_render_resource
    from reach_lighting import resource_lighting_bindings
    rows=scenario_geometry_bindings(cache)
    if not 0<=bsp_index<len(rows):raise ValueError('Reach BSP index outside scenario')
    row=rows[bsp_index]
    if row['lighting_placeholder']:
        owner=row['bsp'];datum=cache.u(owner['offset']+0x4e0)
        bindings={};geometry=owner['offset']+0x44c
    else:
        owner=row['lighting'];datum=cache.u(owner['offset']+0x10c)
        bindings=resource_lighting_bindings(cache,owner['offset'])
        geometry=owner['offset']+0x78
    zone=next(t['offset'] for t in cache.tags.values() if t['group']=='zone')
    resources=cache.block(zone+100,64)
    index=datum&65535
    if index>=len(resources) or cache.u(resources[index]+12)!=owner['datum']:
        raise ValueError('Reach geometry resource owner mismatch')
    resource=ReachResource(cache,datum,shared_paths,{})
    converted=convert_render_resource(resource,bindings)
    from reach_bsp_collision_source import ReachBspCollisionSource
    from reach_bsp_instances import read_instances
    from reach_instance_buckets import validate_instance_buckets
    bsp_offset=row['bsp']['offset'];pages={}
    collision=ReachResource(cache,cache.u(bsp_offset+0x518),shared_paths,pages)
    definitions=ReachBspCollisionSource(collision).headers(collision.root+24,324)
    placements=ReachResource(cache,cache.u(bsp_offset+0x520),shared_paths,pages)
    instances=read_instances(placements,len(definitions))
    converted['collision_lookup']=validate_instance_buckets(cache,bsp_offset,geometry,instances)
    if not row['lighting_placeholder']:
        from reach_lighting import convert_lighting_tables
        converted['lighting_tables'] = convert_lighting_tables(
            cache, row['lighting']['offset'], converted)
    return converted,{'bsp_index':bsp_index,'bsp':row['bsp']['name'],
        'owner_group':owner['group'],'owner_datum':hex(owner['datum']),
        'resource_datum':hex(datum),'geometry_offset':geometry,
        'required_native_import_version':2,
        'lighting_placeholder':row['lighting_placeholder']}
