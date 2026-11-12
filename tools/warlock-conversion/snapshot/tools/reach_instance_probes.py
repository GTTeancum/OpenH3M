"""Extract Reach instance probes with stable indices for reference conversion."""
import struct


def read_instance_probes(cache, lighting_offset, bsp_index):
    entries=cache.block(lighting_offset+0x6c,36)
    probes=[]
    for index,at in enumerate(entries):
        probes.append(dict(kind=f'bsp{bsp_index}:instance',index=index,
            source_prefix_hex='',terms=list(cache.unpack('16H',at)),
            analytical_light_index=cache.u(at+32)))
    references=[]
    for index,at in enumerate(cache.block(lighting_offset+0x60,12)):
        probe=cache.unpack('h',at+4)[0]
        if probe < -1 or probe >= len(entries):
            raise ValueError('Instance lighting references absent probe')
        references.append(dict(instance=index,probe=probe,
                               analytical_light_index=cache.u(at+8)))
    return probes,references


def pack_converted_probes(source, converted):
    """Validate bridge identity/order and preserve analytical fields separately."""
    if len(source)!=len(converted):
        raise ValueError('Probe conversion count mismatch')
    payload=bytearray()
    for original,native in zip(source,converted):
        for key in ('kind','index','source_prefix_hex','analytical_light_index'):
            if original[key]!=native[key]:
                raise ValueError('Probe conversion reordered or changed source identity')
        record=bytes.fromhex(native['native_probe_hex'])
        if len(record)!=72:
            raise ValueError('Expected original H3 72-byte light probe')
        values=struct.unpack('>36H',record)
        if any(v&0x7c00==0x7c00 for v in values):
            raise ValueError('Nonfinite native probe')
        if any(values[i] for i in (3,7,35)):
            raise ValueError('Nonempty native probe padding')
        payload.extend(record)
    return bytes(payload)
