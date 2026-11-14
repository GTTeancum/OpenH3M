"""Publish authored Forge names and explicit reported exceptions in native locales."""
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


def source_label_text(source, labels):
    """Read only real authored English text, with no identifier-to-title fallback."""
    sm = next(t['offset'] for t in source.tags.values() if t['group']=='matg')
    count, size, refs, data = source.unpack('4I', sm+24)
    locale_offset = getattr(source, 'locale_offset', lambda value: value)
    refs, data = locale_offset(refs), locale_offset(data)
    if refs+count*8>len(source.data) or data+size>len(source.data):
        raise ValueError('Source English locale outside cache bounds')
    source_text = {}
    for j in range(count):
        sid, off = source.unpack('II', refs+j*8)
        if sid not in labels:continue
        if off>=size:raise ValueError('Source Forge label offset outside text')
        end = source.data.find(b'\0', data+off, data+size)
        if end < 0:raise ValueError('Unterminated source Forge label')
        value = bytes(source.data[data+off:end+1])
        if value == b'\0':continue
        value[:-1].decode('utf8')
        if sid in source_text and source_text[sid] != value:
            raise ValueError('Ambiguous source Forge label')
        source_text[sid] = value
    return source_text


def plan_labels(source, registry, labels):
    """Prefer existing stock UI text; resolve missing entries from authored text."""
    native=native_label_text(registry.cache)
    needed={sid:target for sid,target in labels.items() if target not in native}
    authored=source_label_text(source,needed)
    result={}
    for sid,value in authored.items():
        target=needed[sid]
        if target in result and result[target]!=value:
            raise ValueError('Source Forge labels collide after string-ID translation')
        result[target]=value
    return result, sorted(set(needed)-set(authored))


RESUSCITATION_SCENARIO = r'levels\multi\resuscitation\resuscitation'
RESUSCITATION_SOURCE_SHA256 = 'e32d9553e66ac143d42260da5bbe4296e4625ba827ee27247ba74204ec66d670'
# Explicit owner-authorized display names, not recovered authored translations.
RESUSCITATION_DERIVED_LABELS = {
    'spectre': b'Spectre\0',
    'sniper_rifle_ammo': b'Sniper Rifle Ammo\0',
    'map_credits': b'Map Credits\0',
}


def resolve_derived_labels(source, labels, missing):
    """Exact-source exception for three owner-approved, reported derived names."""
    if not missing:return {},[]
    scenarios=[source.name(k) for k,t in source.tags.items() if t['group']=='scnr']
    if scenarios != [RESUSCITATION_SCENARIO]:return {},[]
    if hashlib.sha256(source.data).hexdigest()!=RESUSCITATION_SOURCE_SHA256:
        raise ValueError('Resuscitation derived Forge label source changed')
    from string_ids import StringTable
    strings=StringTable(source);resolved={};provenance=[]
    for sid in missing:
        key=strings.text(sid)
        if key not in RESUSCITATION_DERIVED_LABELS:continue
        target=labels[sid];value=RESUSCITATION_DERIVED_LABELS[key]
        if target in resolved and resolved[target]!=value:
            raise ValueError('Derived Forge labels collide after translation')
        resolved[target]=value
        provenance.append(dict(source_string_id=sid,target_string_id=target,display_key=key,
            english=value[:-1].decode('utf8'),provenance='owner-approved derived display name; source English label absent'))
    return resolved,provenance


def stage_labels(source, registry, labels):
    """Publish complete labels; only the exact-source approved exception derives text."""
    resolved,missing=plan_labels(source,registry,labels)
    authored_count=len(resolved)
    derived,provenance=resolve_derived_labels(source,labels,missing)
    for target,value in derived.items():
        if target in resolved and resolved[target]!=value:
            raise ValueError('Derived Forge label conflicts with authored text')
        resolved[target]=value
    missing=[sid for sid in missing if labels[sid] not in derived]
    if missing:
        from string_ids import StringTable
        strings=StringTable(source)
        raise ValueError('Missing authored English Forge names: '+', '.join(strings.text(sid) for sid in missing))
    count=stage_label_text(registry,resolved)
    registry.forge_label_publication=dict(authored_labels_added=authored_count,
        derived_labels_added=len(derived),derived_labels=provenance,
        source_sha256=hashlib.sha256(source.data).hexdigest())
    return count


def stage_label_text(registry, labels):
    """Publish one collected set of target string ID -> English UTF-8 bytes."""
    b,c=registry.builder,registry.cache
    if not labels:return 0
    if b.locale:
        raise ValueError('Forge labels require merging with earlier locale edits')
    for value in labels.values():
        if not value or value==b'\0' or value[-1:]!=b'\0' or b'\0' in value[:-1]:
            raise ValueError('Invalid Forge label text')
        value[:-1].decode('utf8')
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
