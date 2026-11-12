"""Register converted Reach lighting in the original H3 scenario lightmap.

Native sub_821513B8 searches 436-byte records by signed BSP index at +2.
sub_8216F8F0 rejects a missing record, and sub_822C4CA8 then returns BSP+0x2e0
instead of lightmap+0x130. Thus unlit BSPs need no synthetic lighting record.
These are observations of the original executable, not runtime patches.
"""
import struct


def install_scenario_lightmap(registry, scenario_address, bsps, bindings, probe_root):
    builder=registry.builder
    if len(probe_root)!=88 or any(probe_root[4:16]):
        raise ValueError('Expected staged root with no BSP lightmap array')
    if set(bsps)!=set(range(len(bindings))):
        raise ValueError('Incomplete scenario BSP assembly')
    if any(builder.read(scenario_address+0x6f0,16)):
        raise ValueError('Scenario lightmap reference already populated')

    def validate_tag(datum,group):
        index=datum&65535
        if index>=len(registry.tags)//8:
            raise ValueError('Lightmap dependency tag outside registry')
        native_group,salt,address=struct.unpack_from('>HHI',registry.tags,index*8)
        if salt!=datum>>16 or registry.cache.groups[native_group]!=group:
            raise ValueError('Lightmap dependency group/salt mismatch')
        return address

    records=[];active=[];unlit=[]
    for index in range(len(bindings)):
        bsp=bsps[index]
        address=validate_tag(bsp['datum'],'sbsp')
        if address!=bsp['address']:
            raise ValueError('BSP binding address mismatch')
        record=bsp['lighting']
        if record is None:
            if not bindings[index]['lighting_placeholder']:
                raise ValueError('Missing source lighting was not a placeholder')
            if builder.read(address+0x2e0,0x84)!=bsp['geometry_record'][0x130:0x1b4]:
                raise ValueError('Unlit BSP fallback geometry not installed')
            unlit.append(index)
            continue
        if bindings[index]['lighting_placeholder'] or len(record)!=436:
            raise ValueError('Unexpected native lighting record')
        if struct.unpack_from('>h',record,2)[0]!=index:
            raise ValueError('Native lightmap BSP index mismatch')
        if record[4:8]!=builder.read(address,4):
            raise ValueError('Native lightmap/BSP checksum mismatch')
        if record[0x130:0x1b4]!=builder.read(address+0x2e0,0x84):
            raise ValueError('Native lightmap/BSP geometry mismatch')
        for offset in (0xec,0xfc):
            validate_tag(struct.unpack_from('>I',record,offset)[0],'bitm')
        records.append(record);active.append(index)
    root=bytearray(probe_root)
    payload=b''.join(records)
    pointer=builder.alloc(payload) if payload else 0
    struct.pack_into('>III',root,4,len(records),pointer,0)
    datum,address=registry.newtag('sLdT',root)
    builder.put(scenario_address+0x6f0,'4sIII',b'sLdT',0,0,datum)
    if builder.read(address,88)!=root or (payload and builder.read(pointer,len(payload))!=payload):
        raise ValueError('Native scenario lightmap readback mismatch')
    if builder.read(scenario_address+0x6f0,16)!=struct.pack('>4sIII',b'sLdT',0,0,datum):
        raise ValueError('Scenario lightmap reference readback mismatch')
    return dict(datum=datum,address=address,lit_bsps=active,unlit_bsps=unlit,
        indexed_lookup=True,unlit_geometry_fallback=True,records_read_back=True,
        environment_probes_retained=True,analytical_adaptation_complete=False,
        runtime_verified=False)
