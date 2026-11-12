"""Read/convert Reach resource-resident cluster MOPPs without guessing keys.

Cluster keys are local to Reach instance groups. Preserve them for inspection,
but do not install them as native H3 cluster collision trees: sub_820C0B00
consumes global placement indices. The conversion uses original H3 version-2
instance buckets, validated by reach_instance_buckets, instead.
"""
from collections import Counter
import struct
from forge_mopp import terminals
from reach_bsp_collision_source import ReachBspCollisionSource
from reach_physics import convert_tag_mopp


def convert_cluster_mopps(cache, bsp_offset, resource):
    reader=ReachBspCollisionSource(resource)
    headers=reader.headers(resource.root+48,96)
    bindings=[];referenced=set()
    for index,at in enumerate(cache.block(bsp_offset+0x138,140)):
        mopp=cache.unpack('h',at+0x42)[0]
        if mopp < -1 or mopp >= len(headers):
            raise ValueError('Cluster references absent resource MOPP')
        if mopp != -1:referenced.add(mopp)
        bindings.append(mopp)
    if referenced!=set(range(len(headers))):
        raise ValueError('Unreferenced cluster MOPP requires review')
    converted=[]
    for index,at in enumerate(headers):
        source=bytes(reader.block(at+80,1)[1])
        header,code=convert_tag_mopp(bytes(resource.data[at:at+96]),source)
        source_keys=Counter(k for _,_,k in terminals(source))
        if Counter(k for _,_,k in terminals(code))!=source_keys:
            raise ValueError('Cluster MOPP conversion changed local keys')
        converted.append(dict(index=index,header=header,code=code,
                              keys=sorted(source_keys),terminal_count=sum(source_keys.values())))
    return converted,bindings


def allocate_cluster_mopps(converted, allocate):
    """Allocate native64-byte headers/code; return pointers in source order."""
    result=[]
    for index,row in enumerate(converted):
        header=bytearray(row['header']);code=row['code']
        if row['index']!=index or len(header)!=64 or struct.unpack_from('>I',header,48)[0]!=len(code):
            raise ValueError('Invalid converted cluster MOPP record')
        if any(header[52:60]):raise ValueError('MOPP data already linked')
        struct.pack_into('>I',header,52,allocate(code) if code else 0)
        result.append(allocate(header))
    return result
