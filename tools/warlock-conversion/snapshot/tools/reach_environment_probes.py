"""Link converted Reach environment probes into original H3 sLdT root tables.

Source analytical selection is deliberately not encoded here: the enclosing
importer must adapt it separately. Prefix callbacks are mandatory because source
string IDs and scenario object identifiers cannot be assumed valid at destination.
"""
import hashlib
import struct
from pathlib import Path


def install_environment_probes(root, groups, directory, allocate,
                               translate_air_prefix, translate_object_id):
    if not isinstance(root, bytearray) or len(root)!=88:
        raise ValueError('Expected original H3 sLdT root')
    if any(root[0x28:0x4c]):
        raise ValueError('Environment probe fields already populated')
    directory=Path(directory)
    air=bytearray();scenery=bytearray();machines=bytearray()
    selections=[];seen=set()
    # Validate all source payloads before allocating destination metadata.
    prepared=[]
    for group in groups:
        key=(group['bsp'],group['kind'])
        if key in seen:raise ValueError('Duplicate BSP probe group')
        seen.add(key)
        kind=group['kind'];count=group['count']
        if kind not in ('air','scenery') and not kind.startswith('machine-'):
            raise ValueError('Unknown environment probe kind')
        stride=92 if kind=='air' else (80 if kind=='scenery' else 84)
        path=(directory/group['file']).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError('Probe payload must remain in its staging directory')
        data=path.read_bytes()
        if len(data)!=count*stride or len(data)!=group['bytes']:
            raise ValueError('Environment probe payload length mismatch')
        if hashlib.sha256(data).hexdigest()!=group['sha256']:
            raise ValueError('Environment probe payload hash mismatch')
        if len(group['analytical_ids'])!=count:
            raise ValueError('Analytical selection count mismatch')
        if kind.startswith('machine-'):
            header=bytes.fromhex(group['machine_header_hex'])
            if len(header)!=32:raise ValueError('Invalid machine probe header')
            identifier=translate_object_id(group['bsp'],header[:8])
            if len(identifier)!=8:raise ValueError('Expected native object identifier')
            prepared.append((kind,identifier+header[8:],data,count))
        else:
            records=bytearray()
            prefix_size=20 if kind=='air' else 8
            for i in range(count):
                record=data[i*stride:(i+1)*stride]
                callback=translate_air_prefix if kind=='air' else translate_object_id
                prefix=callback(group['bsp'],record[:prefix_size])
                if len(prefix)!=prefix_size:raise ValueError('Remapped probe prefix size mismatch')
                records.extend(prefix+record[prefix_size:])
            prepared.append((kind,b'',bytes(records),count))
        selections.append(dict(bsp=group['bsp'],kind=kind,ids=group['analytical_ids']))
    for kind,header,data,count in prepared:
        if kind=='air':air.extend(data)
        elif kind=='scenery':scenery.extend(data)
        else:
            machines.extend(header+struct.pack('>III',count,allocate(data) if data else 0,0))
    for offset,data,stride in ((0x28,air,92),(0x34,scenery,80),(0x40,machines,44)):
        struct.pack_into('>III',root,offset,len(data)//stride,allocate(data) if data else 0,0)
    return dict(air_count=len(air)//92,scenery_count=len(scenery)//80,
                machine_count=len(machines)//44,analytical_selections=selections)
