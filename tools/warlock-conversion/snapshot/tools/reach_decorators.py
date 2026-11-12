"""MCC Reach TinyPosition decorator groups to native H3, retaining selectors.

Uses the same verified MCC group/vertex layout as bsp_metadata.decorator_group.
MCC model-start arrays accelerate draws; model selection is also encoded in each
vertex and must agree before those arrays can be omitted from native metadata.
"""
import math
import struct
from bisect import bisect_right
from collections import Counter


def palette_usage(cache, bsp, resource):
    """Resolve every live model selector before choosing a decorator donor.

    Equal tag counts do not establish compatibility: the high byte of each
    TinyPosition variant indexes a model inside the chosen decorator set.
    """
    palette = []
    for at in cache.block(bsp + 0x274, 16):
        datum = cache.u(at + 12)
        tag = cache.tags.get(datum & 65535)
        if tag is None or tag['salt'] != datum >> 16 or tag['group'] != 'dctr':
            raise ValueError('Invalid Reach decorator palette reference')
        count = cache.u(tag['offset'] + 0x4c)
        names = cache.block(tag['offset'] + 0x40, 4)
        if count > len(names):
            raise ValueError('Decorator valid model count exceeds names')
        palette.append(dict(source=cache.name(datum & 65535), datum=datum,
                            valid_models=count, selectors=Counter()))
    descriptors = resource.buffers('vertex')
    for cluster in cache.block(bsp + 0x138, 140):
        for at in cache.block(cluster + 80, 60):
            # Validate stream bounds and the source's model-start table too.
            convert_group(cache, at, resource)
            count, index, slot, offset = cache.unpack('hbBI', at)
            if not 0 <= index < len(palette):
                raise ValueError('Decorator group references absent palette entry')
            address = resource.fix[descriptors[slot] + 20]
            raw = resource.raw[{0x40000000: 0, 0x60000000: 1}[address & 0xe0000000]]
            start = (address & 0x1fffffff) + offset
            entry = palette[index]
            for i in range(count):
                selector = struct.unpack_from('<H', raw, start + i * 16 + 6)[0] >> 8
                if selector >= entry['valid_models']:
                    raise ValueError('Decorator vertex selects an absent source model')
                entry['selectors'][selector] += 1
    for entry in palette:
        entry['selectors'] = dict(sorted(entry['selectors'].items()))
        entry['placements'] = sum(entry['selectors'].values())
    return palette


def install_palette(root, usage, native_datums, registry):
    """Install already resolved native sets without silently changing selectors.

    Callers must choose/import stock equivalents or convert unique assets first.
    A donor with too few models is rejected, not modulo-remapped or clamped.
    """
    if len(root) != 0x388 or any(root[0x1bc:0x1c8]):
        raise ValueError('Expected unpopulated native BSP decorator palette')
    if len(usage) != len(native_datums):
        raise ValueError('Decorator palette resolution is incomplete')
    records = bytearray()
    builder = registry.builder
    for source, datum in zip(usage, native_datums):
        index = datum & 65535
        if index * 8 + 8 > len(registry.tags):
            raise ValueError('Native decorator datum is outside registry')
        group, salt, address = struct.unpack_from('>HHI', registry.tags, index * 8)
        if (salt != datum >> 16 or group >= len(builder.cache.groups)
                or builder.cache.groups[group] != 'dctr' or address in (0, 0xffffffff)):
            raise ValueError('Native decorator datum is not a valid decorator set')
        count = struct.unpack('>I', builder.read(address + 0x1c, 4))[0]
        if any(selector >= count for selector in source['selectors']):
            raise ValueError('Native decorator donor lacks an authored model selector: ' + source['source'])
        records.extend(struct.pack('>4sIII', b'dctr', 0, 0, datum))
    pointer = builder.alloc(records) if records else 0
    struct.pack_into('>III', root, 0x1bc, len(native_datums), pointer, 0)
    return dict(sets=len(native_datums), placements=sum(s['placements'] for s in usage),
                selectors_preserved=True, runtime_verified=False)


def convert_group(cache,at,resource,split=None):
    count,palette,slot,offset=cache.unpack('hbBI',at)
    descriptors=resource.buffers('vertex')
    if count<0 or palette<0 or slot>=len(descriptors) or offset%16:
        raise ValueError('Invalid decorator binding')
    descriptor=descriptors[slot];total,fmt,stride=resource.unpack('IHH',descriptor)
    if (fmt,stride)!=(20,16) or offset+count*16>total*16:
        raise ValueError('Decorator instances outside TinyPosition stream')
    starts=[cache.unpack('h',p)[0] for p in cache.block(at+48,2)]
    if starts!=sorted(starts) or any(v<0 or v>count for v in starts):
        raise ValueError('Invalid decorator model boundaries')
    address=resource.fix[descriptor+20]
    raw=resource.raw[{0x40000000:0,0x60000000:1}[address&0xe0000000]]
    begin=(address&0x1fffffff)+offset
    values=cache.unpack('10f',at+8)
    if not all(math.isfinite(v) for v in values) or any(v<0 for v in values[4:7]):
        raise ValueError('Invalid decorator bounds')
    sides=[]
    for i in range(count):
        xyz=struct.unpack_from('<3H',raw,begin+i*16)
        variant=struct.unpack_from('<H',raw,begin+i*16+6)[0]
        if variant>>8!=bisect_right(starts,i):
            raise ValueError('Decorator model boundaries disagree with vertex selector')
        if split is None:side=0
        else:
            axis,plane=split
            position=values[axis]+xyz[axis]/65535*values[4+axis]
            side=int(position>=plane)
        sides.append(side)
    groups=[[],[]];runs=[];i=0
    while i<count:
        end=i+1
        while end<count and sides[end]==sides[i]:end+=1
        record=struct.pack('>hbBI10f',end-i,palette,slot,offset+i*16,*values)
        groups[sides[i]].append(record)
        runs.append(dict(side=sides[i],first=i,count=end-i))
        i=end
    return [b''.join(g) for g in groups],runs
