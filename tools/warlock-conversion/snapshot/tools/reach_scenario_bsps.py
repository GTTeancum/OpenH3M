"""Stage original-H3 scenario BSP references with explicit remaining semantics.

Offsets: retained H3 scnr.xml and Reach scnr.xml; flag names checked against
TagTool Scenario.StructureBspBlock, ce2dc6ac. This is an offline assembly step,
not a claim that Reach-only structure-lighting/design semantics are complete.
"""
import struct


def install_scenario_bsps(source, source_root, registry, scenario, bsps, cubemaps):
    b=registry.builder
    rows=source.block(source_root+0x50,0xac)
    if set(bsps)!=set(range(len(rows))):
        raise ValueError('Scenario BSP ordinal coverage differs')
    if any(b.read(scenario+0x14,12)):
        raise ValueError('Scenario BSP table already installed')
    def reference(group,datum):
        if datum==0xffffffff:return bytes.fromhex('ffffffff0000000000000000ffffffff')
        index=datum&65535
        if index>=len(registry.tags)//8:raise ValueError('BSP dependency outside registry')
        gi,salt,address=struct.unpack_from('>HHI',registry.tags,index*8)
        if salt!=datum>>16 or registry.cache.groups[gi]!=group:
            raise ValueError('BSP dependency salt/group mismatch')
        return struct.pack('>4sIII',group.encode('ascii'),0,0,datum)
    flag_mapping={0:0,3:2,4:3,5:4,6:5,7:6,8:7,9:10,10:11}
    reach_only={1:'per_vertex_only_lightmap',2:'never_lightmap',11:'shared_bsp',
                12:'dont_use_extra_lighting_bsps_for_cubemaps',13:'custom_gravity_scale'}
    # Authoring resolution hints, not bitmap dimensions or allocation sizes.
    source_sizes=(32,64,128,256,512,768,1024,1280,1536,1792)
    native_sizes=(1024,768,512,1536,256,384,2048,3072,4096)
    payload=bytearray();report=[]
    for index,at in enumerate(rows):
        record=bytearray(108)
        row=dict(index=index,pending=[])
        record[:16]=reference('sbsp',bsps[index]['datum'])
        for off in (16,32,72,88):record[off:off+16]=reference('',0xffffffff)
        for off in (16,48):
            if source.u(at+off+12)!=0xffffffff:
                raise ValueError('Local Reach BSP/lighting requires explicit conversion')
        lighting=source.u(at+32+12)
        if lighting!=0xffffffff:
            tag=source.tags[lighting&65535]
            if tag['salt']!=lighting>>16 or tag['group']!='stli':
                raise ValueError('Invalid source structure-lighting dependency')
            row['pending'].append(dict(field='structure_lighting',datum=lighting,name=tag['name']))
        size=source.u(at+64)
        if size>=len(source_sizes):raise ValueError('Unknown source size class')
        native_size=min((x for x in native_sizes if x>=source_sizes[size]),default=max(native_sizes))
        struct.pack_into('>I3f',record,48,native_sizes.index(native_size),*source.unpack('3f',at+68))
        flags,sky,start,end=source.unpack('HhHH',at+80)
        if flags & ~0x3fff:raise ValueError('Unknown Reach BSP flags')
        native_flags=sum(1<<target for bit,target in flag_mapping.items() if flags&(1<<bit))
        struct.pack_into('>HhHH',record,64,native_flags,sky,start,end)
        for bit,name in reach_only.items():
            if flags&(1<<bit):row['pending'].append(dict(field='flag',name=name))
        if source.u(at+104+12)!=0xffffffff:
            raise ValueError('Wind dependency requires explicit native binding')
        source_cube=source.u(at+88+12)
        if source_cube!=0xffffffff:
            if index not in cubemaps:raise ValueError('Missing source BSP cubemap conversion')
            record[72:88]=reference('bitm',cubemaps[index])
        elif index in cubemaps:raise ValueError('Unexpected native cubemap')
        clones=source.u(at+120)
        if clones>>len(rows):raise ValueError('Clone mask outside BSP table')
        struct.pack_into('>I',record,104,clones)
        row.update(source_flags=flags,native_flags=native_flags,source_size_hint=source_sizes[size],
                   native_size_hint=native_size,default_sky=sky,cubemap=cubemaps.get(index),
                   lighting_settings=source.data[at+124:at+172].hex())
        payload.extend(record);report.append(row)
    address=b.alloc(payload)
    b.put(scenario+0x14,'III',len(rows),address,0)
    if b.read(address,len(payload))!=payload:raise ValueError('BSP table readback mismatch')
    if b.read(scenario+0x14,12)!=struct.pack('>III',len(rows),address,0):
        raise ValueError('Scenario BSP table pointer mismatch')
    return dict(records=report,records_read_back=True,complete=False,
                structure_designs_pending=True,runtime_verified=False)
