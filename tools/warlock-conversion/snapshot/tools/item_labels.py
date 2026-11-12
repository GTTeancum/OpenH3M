"""Append custom DMR labels using verified native HUD templates, English only."""
import hashlib
import struct

DMR = r'priception\objects\weapons\rifle\dmr\dmr'

def stage(importer):
    if ('weap', DMR) not in importer.resolved:
        return 0
    # A source alias resolves to the stock rifle, including its existing labels.
    stock = ('weap', r'objects\weapons\rifle\battle_rifle\battle_rifle')
    if importer.resolved[('weap', DMR)] == importer.resolved.get(stock):
        return 0
    i=importer; c=i.registry.cache; b=i.builder
    if b.locale:
        raise ValueError('Custom item labels need merging with earlier locale edits')
    matg=next(t['offset'] for t in c.tags.values() if t['group']=='matg')
    unic=next(t['offset'] for k,t in c.tags.items() if t['group']=='unic' and c.name(k)==r'ui\hud\hud_messages')
    count,size,refs,data=c.unpack('4I',matg+0x1c4)
    refs,data=(refs+c.u(0x478))&0xffffffff,(data+c.u(0x478))&0xffffffff
    index=bytearray(c.data[refs:refs+count*8]); text=bytearray(c.data[data:data+size])
    from string_ids import StringTable
    strings=StringTable(c); existing={}
    for j in range(count):
        sid,off=struct.unpack_from('>II',index,j*8)
        end=text.find(b'\0',off)
        if end<0:raise ValueError('Unterminated native HUD text')
        name=strings.text(sid)
        existing[name]=bytes(text[off:end]).decode('utf8')
    first,length=c.unpack('HH',unic+32)
    group=bytearray(index[first*8:(first+length)*8])
    labels={}
    for suffix in ('pickup','swap','picked_up','ammo_singular','ammo_plural','switch_to','swap_ai'):
        value=existing['br_'+suffix].replace('Battle Rifle','DMR').replace('\ue114','DMR')
        key='dmr_'+suffix
        sid=i.target_strings.id_for_text(key)
        group.extend(struct.pack('>II',sid,len(text)));text.extend(value.encode('utf8')+b'\0')
        labels[key]=value
    if count+len(group)//8>65535:raise ValueError('Native locale index overflow')
    index.extend(group)
    rp,dp=b.append_locale(index),b.append_locale(text)
    b.put(i.registry.address(matg+0x1c4),'4I',len(index)//8,len(text),rp,dp)
    for off,payload in ((0x1d4,index),(0x1e8,text)):
        pos=i.registry.address(matg+off)-b.base
        b.meta[pos:pos+20]=hashlib.sha1(payload).digest()
    b.put(i.registry.address(unic+32),'HH',count,len(group)//8)
    i.added.append({'group':'unic','source':'DMR English HUD labels','labels':labels,
                    'native_template':'br_*; weapon silhouette replaced with literal DMR'})
    return len(labels)
