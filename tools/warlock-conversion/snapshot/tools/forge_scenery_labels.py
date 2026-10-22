"""Append authored English Forge names using original Halo 3 locale tables."""
import hashlib
import struct


def stage_labels(source, registry, labels):
    """labels: source string ID -> converted retail string ID."""
    b, c = registry.builder, registry.cache
    sm = next(t['offset'] for t in source.tags.values() if t['group']=='matg')
    count, size, refs, data = source.unpack('4I', sm+24)
    source_text = {}
    for j in range(count):
        sid, off = source.unpack('II', refs+j*8)
        if sid in labels:
            end = source.data.find(b'\0', data+off, data+size)
            if end < 0: raise ValueError('Unterminated source Forge label')
            value = source.data[data+off:end+1]
            if sid in source_text and source_text[sid] != value:
                raise ValueError('Ambiguous source Forge label')
            source_text[sid] = value
    if set(source_text) != set(labels):
        raise ValueError('Missing authored English Forge names')
    matg = next(t['offset'] for t in c.tags.values() if t['group']=='matg')
    unic = next(t['offset'] for i,t in c.tags.items() if t['group']=='unic' and c.name(i)==r'ui\halox\sandbox_ui\strings')
    count, size, refs, data = c.unpack('4I', matg+0x1c4)
    refs, data = (refs+c.u(0x478))&0xffffffff, (data+c.u(0x478))&0xffffffff
    index = bytearray(c.data[refs:refs+count*8]);text = bytearray(c.data[data:data+size])
    first, length = c.unpack('HH', unic+32)
    group = bytearray(index[first*8:(first+length)*8])
    for sid, target in labels.items():
        group.extend(struct.pack('>II',target,len(text)));text.extend(source_text[sid])
    index.extend(group)
    if count+len(group)//8 > 65535:raise ValueError('Native locale index overflow')
    rpos,dpos = b.append_locale(index),b.append_locale(text)
    b.put(registry.address(matg+0x1c4),'4I',len(index)//8,len(text),rpos,dpos)
    for off,payload in ((0x1d4,index),(0x1e8,text)):
        address=registry.address(matg+off)-b.base
        b.meta[address:address+20]=hashlib.sha1(payload).digest()
    b.put(registry.address(unic+32),'HH',count,len(group)//8)
    return len(labels)
