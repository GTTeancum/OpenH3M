"""Bind Reach root lightprobes to a shared cache allocator and string table.

Source placement IDs must be preserved by the enclosing scenario converter.
Returns staged sLdT root bytes; it does not invent a missing BSP lightmap,
resolve analytical lighting, or register a complete scenario lightmap tag.
"""
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from string_ids import StringTable
from reach_environment_probes import install_environment_probes


def stage_environment_probe_root(c, builder, target_strings, directory, manifest):
    directory=Path(directory)
    source_strings=StringTable(c)
    scenario=next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
    owners={}
    # Actual Reflection data matches the retained Reach scenario plugin here;
    # TagTool HaloReach/MCC's +32-byte root displacement reads empty blocks.
    schema=ET.parse(directory/'reach-scnr.xml').getroot()
    for kind,label in (('scenery','Scenery'),('machine','Machines')):
        field=next(f for f in schema if f.get('name')==label)
        offset=int(field.get('offset'),0);stride=int(field.get('elementSize'),0)
        for index,p in enumerate(c.block(scenario+offset,stride)):
            identifier=struct.pack('>Ihbb',*c.unpack('Ihbb',p+60))
            if identifier in owners:raise ValueError('Duplicate scenario object identifier')
            owners[identifier]=dict(kind=kind,index=index)
    resolved=[];names=[];unresolved=[];orphans=[]
    def object_id(bsp,identifier):
        if identifier not in owners:
            matches=[(key.hex(),value) for key,value in owners.items() if key[:4]==identifier[:4]]
            needle=struct.pack('<Ihbb',*struct.unpack('>Ihbb',identifier))
            occurrence=c.data.find(needle)
            single=occurrence>=0 and c.data.find(needle,occurrence+1)<0
            row=dict(bsp=bsp,identifier=identifier.hex(),same_unique_id=matches)
            if not matches and single:
                orphans.append(row)
            else:unresolved.append(row)
            return identifier  # Preserve original orphan; never invent an owner.
        resolved.append(dict(bsp=bsp,identifier=identifier.hex(),**owners[identifier]))
        return identifier
    def air_prefix(bsp,prefix):
        old=struct.unpack_from('>I',prefix,12)[0]
        new=source_strings.translate(old,target_strings)
        assert target_strings.text(new)==source_strings.text(old)
        result=bytearray(prefix);struct.pack_into('>I',result,12,new)
        mask,other=struct.unpack_from('>HH',prefix,16)
        if mask!=0xffff or other!=0 or not 0<=bsp<16:
            raise ValueError('Airprobe BSP-mask policy requires review for this source')
        # Cached local probes had the all-BSP sentinel. On moving them to the
        # root, retain their actual owning BSP. No records are deduplicated.
        struct.pack_into('>HH',result,16,1<<bsp,0)
        names.append(dict(bsp=bsp,source_id=old,native_id=new,name=source_strings.text(old),
                          native_bsp_mask=1<<bsp))
        return bytes(result)
    root=bytearray(88)
    result=install_environment_probes(root,manifest['groups'],directory,builder.alloc,
                                     air_prefix,object_id)
    if unresolved:raise ValueError('Unresolved source lightprobe owners')
    for offset,stride in ((0x28,92),(0x34,80),(0x40,44)):
        count,pointer,pad=struct.unpack_from('>III',root,offset)
        if pad or (count and len(builder.read(pointer,count*stride))!=count*stride):
            raise ValueError('Lightprobe allocation readback failed')
    staged_probe_root=bytes(root)
    result.update(source=manifest['source'],owners=resolved,airprobe_names=names,
        source_object_bindings_accounted_for=not unresolved,unresolved_owners=unresolved,
        preserved_source_orphans=orphans,
        verified_owner_count=len(resolved),airprobe_names_remapped=True,
        added_strings=len(target_strings.strings)-target_strings.original_count,
        requires_preserved_scenario_object_ids=True,
        airprobe_bsp_flags_adapted=True,scenario_placements_installed=False,
        analytical_adaptation_complete=False,runtime_verified=False)
    return staged_probe_root,result
