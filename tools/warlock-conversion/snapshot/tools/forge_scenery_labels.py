"""Append authored English Forge names using original Halo 3 locale tables."""
import hashlib
import struct


def native_label_text(cache):
    """English text in the native sandbox UI, not merely string-ID names."""
    matg=next(t['offset'] for t in cache.tags.values() if t['group']=='matg')
    unic=next(t['offset'] for i,t in cache.tags.items()
              if t['group']=='unic' and cache.name(i)==r'ui\halox\sandbox_ui\strings')
    count,size,refs,data=cache.unpack('4I',matg+0x1c4)
    refs=(refs+cache.u(0x478))&0xffffffff
    data=(data+cache.u(0x478))&0xffffffff
    first,length=cache.unpack('HH',unic+32)
    if first+length>count or refs+count*8>len(cache.data):
        raise ValueError('Native Forge locale index outside bounds')
    if data+size>len(cache.data):
        raise ValueError('Native Forge locale text outside bounds')
    result={}
    for j in range(first,first+length):
        sid,offset=cache.unpack('II',refs+j*8)
        if offset>=size:raise ValueError('Native Forge label offset outside text')
        end=cache.data.find(b'\0',data+offset,data+size)
        if end<0:raise ValueError('Unterminated native Forge label')
        if end>data+offset:
            value=bytes(cache.data[data+offset:end+1])
            if sid in result and result[sid]!=value:
                raise ValueError('Conflicting native Forge label text')
            result[sid]=value
    return result


def native_label_ids(cache):
    """IDs localized by the native sandbox UI, not merely present in string_ids."""
    return set(native_label_text(cache))


def stage_labels(source, registry, labels):
    """labels: source string ID -> converted retail string ID."""
    b, c = registry.builder, registry.cache
    sm = next(t['offset'] for t in source.tags.values() if t['group']=='matg')
    count, size, refs, data = source.unpack('4I', sm+24)
    locale_offset = getattr(source, 'locale_offset', lambda value: value)
    refs, data = locale_offset(refs), locale_offset(data)
    source_text = {}
    for j in range(count):
        sid, off = source.unpack('II', refs+j*8)
        if sid in labels:
            end = source.data.find(b'\0', data+off, data+size)
            if end < 0: raise ValueError('Unterminated source Forge label')
            value = source.data[data+off:end+1]
            if value == b'\0':raise ValueError('Empty authored English Forge name')
            if sid in source_text and source_text[sid] != value:
                raise ValueError('Ambiguous source Forge label')
            source_text[sid] = value
    if set(source_text) != set(labels):
        raise ValueError('Missing authored English Forge names')
    return stage_label_text(registry,{target:source_text[sid] for sid,target in labels.items()})


def stage_label_text(registry, labels):
    """Publish one collected set of target string ID -> English UTF-8 bytes."""
    b,c=registry.builder,registry.cache
    if not labels:return 0
    for value in labels.values():
        if not value or value==b'\0' or value[-1:]!=b'\0' or b'\0' in value[:-1]:
            raise ValueError('Invalid Forge label text')
    matg = next(t['offset'] for t in c.tags.values() if t['group']=='matg')
    unic = next(t['offset'] for i,t in c.tags.items() if t['group']=='unic' and c.name(i)==r'ui\halox\sandbox_ui\strings')
    count, size, refs, data = c.unpack('4I', matg+0x1c4)
    refs, data = (refs+c.u(0x478))&0xffffffff, (data+c.u(0x478))&0xffffffff
    index = bytearray(c.data[refs:refs+count*8]);text = bytearray(c.data[data:data+size])
    first, length = c.unpack('HH', unic+32)
    group = bytearray(index[first*8:(first+length)*8])
    for target, value in labels.items():
        group.extend(struct.pack('>II',target,len(text)));text.extend(value)
    index.extend(group)
    if count+len(group)//8 > 65535:raise ValueError('Native locale index overflow')
    rpos,dpos = b.append_locale(index),b.append_locale(text)
    b.put(registry.address(matg+0x1c4),'4I',len(index)//8,len(text),rpos,dpos)
    for off,payload in ((0x1d4,index),(0x1e8,text)):
        address=registry.address(matg+off)-b.base
        b.meta[address:address+20]=hashlib.sha1(payload).digest()
    b.put(registry.address(unic+32),'HH',count,len(group)//8)
    return len(labels)
