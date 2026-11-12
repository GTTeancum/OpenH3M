"""Translate Reach scenario cluster tables without losing default acoustics.

Layout reference: TagTool Gen4.Scenario.ScenarioClusterDataBlock (also used by
Reach), ce2dc6ac13072b160752af618ea1dc143e2727ac; native scnr.xml 0x534/0x68.
Palette ordinals stay unchanged; importing the referenced palettes is separate.
"""
import struct


def install_scenario_clusters(source, scenario, registry, target_scenario,
                              bsp_bindings, cluster_sources):
    builder = registry.builder
    if any(builder.read(target_scenario+0x534,12)):
        raise ValueError('Scenario cluster table already installed')
    rows = source.block(scenario+0x558,84)
    if len(rows)!=len(bsp_bindings) or len(rows)!=len(cluster_sources):
        raise ValueError('Scenario/BSP cluster slot counts disagree')
    def block(payload,stride):
        if len(payload)%stride:raise ValueError('Misaligned scenario cluster array')
        return struct.pack('>III',len(payload)//stride,builder.alloc(payload) if payload else 0,0)
    output=bytearray();reports=[]
    for ordinal,(at,binding,indices) in enumerate(zip(rows,bsp_bindings,cluster_sources)):
        source_bsp,native_datum,native_address=binding
        clusters=source.block(source_bsp+0x138,140)
        if set(indices)!=set(range(len(clusters))):
            raise ValueError('Scenario cluster mapping drops source clusters')
        checksum=source.u(at+16)
        if checksum not in (0,source.u(source_bsp+0x30)):
            raise ValueError('Source scenario cluster checksum mismatch')
        root=bytearray(104)
        root[:16]=struct.pack('>4sIII',b'sbsp',0,0,native_datum)
        root[52:56]=builder.read(native_address,4)
        centroids=source.block(at+20,12)
        if centroids and len(centroids)!=len(clusters):
            raise ValueError('Incomplete source cluster centroid table')
        root[56:68]=block(b''.join(struct.pack('>3f',*source.unpack('3f',centroids[i]))
                                   for i in indices) if centroids else b'',12)
        default=source.unpack('i',at+32)[0]
        effective=[]
        for source_offset,target_offset,cluster_offset in ((36,16,28),(48,80,25),(60,92,26),(72,68,None)):
            entries=source.block(at+source_offset,4)
            if len(entries)!=len(clusters):
                raise ValueError('Environment property count differs from clusters')
            payload=bytearray()
            for i in indices:
                value,pad=source.unpack('hh',entries[i])
                if pad:raise ValueError('Nonzero environment padding')
                if source_offset==36 and value==-1:value=default
                if not -1<=value<=32767:raise ValueError('Environment index outside native range')
                if cluster_offset is not None:
                    fmt='h' if cluster_offset==28 else 'b'
                    if value!=source.unpack(fmt,clusters[i]+cluster_offset)[0]:
                        raise ValueError('Scenario properties disagree with compiled cluster')
                payload.extend(struct.pack('>hh',value,0))
                if source_offset==36:effective.append(value)
            root[target_offset:target_offset+12]=block(payload,4)
        # Legacy H3 sound arrays remain empty; native acoustics table above is used.
        output.extend(root)
        reports.append(dict(bsp=ordinal,clusters=len(indices),default_acoustics=default,
            effective_acoustics=effective,centroids=len(indices) if centroids else 0,
            absent_source_centroids_preserved=not bool(centroids)))
    pointer=builder.alloc(output)
    builder.put(target_scenario+0x534,'III',len(rows),pointer,0)
    if builder.read(pointer,len(output))!=output:raise ValueError('Scenario cluster write mismatch')
    return dict(bsps=reports,palette_dependencies_installed=False,
                native_records_read_back=True,runtime_verified=False)
