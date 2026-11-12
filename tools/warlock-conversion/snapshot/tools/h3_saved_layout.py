"""Original Halo 3 v12 uncompressed saved-layout BLF writer.

Layout follows Blam-Network/blf's 12070 scenario_map_variant and saved_game_files.
Retail quotas contain salted tag datums, unlike MCC v13 palette coordinates.
Keeping the uncompressed mapv also avoids re-quantizing authored geometry.
"""
import math
import struct


def chunk(signature,major,minor,body):
    return struct.pack('>4sIHH',signature,len(body)+12,major,minor)+body


def fixed(value,size,wide=False):
    data=value.encode('utf-16-be' if wide else 'utf-8')
    if len(data)>=size or '\0' in value:
        raise ValueError('Saved-layout text exceeds native capacity')
    return data+bytes(size-len(data))


def metadata(v):
    h=bytearray(0xf8)
    struct.pack_into('>Q',h,0,v['unique_id'])
    h[8:40]=fixed(v['name'],32,True)
    h[40:168]=fixed(v['description'],128)
    h[168:184]=fixed('Bungie',16)
    # Mythic XEX 0x821F9558 classifies 1..9 as game variants, 10 as
    # usermap. The external 12070 constants incorrectly duplicate CTF/Slayer.
    struct.pack_into('>i',h,184,10)
    struct.pack_into('>QQQ',h,192,0,0xe090,v['date'])
    struct.pack_into('>IiiIih',h,216,0,-1,v['map_id'],0,-1,-1)
    return bytes(h)


def map_variant(v):
    objects,quotas=v['objects'],v['quotas']
    count=v['scenario_count']+len(objects)
    if count>640 or len(quotas)>256:
        raise ValueError('Native Forge object/quota capacity exceeded')
    body=bytearray(0xe090)
    body[:0xf8]=metadata(v)
    struct.pack_into('>4HI6fIffBB2xI',body,0xf8,12,v['scenario_count'],count,
                     len(quotas),v['map_id'],*v['bounds'],0,v['maximum_budget'],
                     v['spent_budget'],0,0,v['signature_hash'])
    # Empty runtime identifiers are NONE, never valid object zero.
    for index in range(640):
        at=0x130+index*84
        struct.pack_into('>iii',body,at+4,-1,-1,-1)
        struct.pack_into('>ihbb',body,at+52,-1,-1,-1,-1)
    for index in range(v['scenario_count']):
        struct.pack_into('>H',body,0x130+index*84,0x29) # Occupied, scenario, removed.
    for index,o in enumerate(objects,v['scenario_count']):
        at=0x130+index*84
        values=o['position']+list(o['forward'])+list(o['up'])+o['boundary']
        if not all(math.isfinite(x) for x in values):
            raise ValueError('Nonfinite layout geometry')
        if not 0<=o['quota']<len(quotas):
            raise ValueError('Placement has no native quota')
        struct.pack_into('>H',body,at,3)
        struct.pack_into('>i9f',body,at+12,o['quota'],*o['position'],*o['forward'],*o['up'])
        struct.pack_into('>HBbBBBB4f',body,at+60,o['engine_flags'],o['mp_flags'],
            o['team'],o['shared_storage'],o['spawn_time'],o['object_type'],o['shape'],*o['boundary'])
    struct.pack_into('>14h',body,0xd330,*v['type_starts'])
    for index,q in enumerate(quotas):
        struct.pack_into('>IBBBBf',body,0xd34c+index*12,q['datum'],0,q['count'],
                         q['count'],q['maximum'],q['price'])
    for index in range(len(quotas),256):
        struct.pack_into('>I',body,0xd34c+index*12,0xffffffff)
    struct.pack_into('>80i',body,0xdf4c,*([-1]*80))
    return bytes(body)


def write(v):
    data=chunk(b'_blf',1,2,b'\xff\xfe'+bytes(34))
    data+=chunk(b'chdr',9,2,struct.pack('>HH',12070,0)+metadata(v))
    data+=chunk(b'mapv',12,1,bytes(4)+map_variant(v)+bytes(4))
    data+=chunk(b'_eof',1,1,struct.pack('>IB',len(data),0))
    return data
