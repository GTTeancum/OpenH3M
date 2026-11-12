"""Resolve exact stock environment dependencies before converting Reach assets.

Unresolved names remain explicit. This does not substitute silence or install
an incomplete acoustics palette, and does not interpret disputed scalar fields.
"""
import struct
from pathlib import Path
from types import SimpleNamespace
from native_assets import NativeAssets


def resolve_environment_assets(source, scenario, registry, strings, disc_maps):
    target = registry.cache
    importer = SimpleNamespace(source=source,registry=registry,builder=registry.builder,
        reference=Path(__file__).resolve().parents[1]/'reference',target_strings=strings,
        resolved={(t['group'],target.name(i)):(t['group'],(t['salt']<<16)|i)
                  for i,t in target.tags.items()},added=[])
    native = NativeAssets(importer,disc_maps)
    required = {}
    for index,at in enumerate(source.block(scenario+0x528,120)):
        for field,offset in (('reverb',4),('background',32),('weather',48),('entry',64),('exit',80)):
            datum=source.u(at+offset+12)
            if datum==0xffffffff:continue
            tag=source.tags.get(datum&65535)
            if tag is None or tag['salt']!=datum>>16:
                raise ValueError('Invalid Reach environment dependency')
            row=required.setdefault(datum,dict(group=tag['group'],name=source.name(datum&65535),uses=[]))
            row['uses'].append(dict(palette=index,field=field))
    resolved={};pending=[];evidence=[]
    for datum,row in required.items():
        key=row['group'],row['name']
        # Sound data needs its dedicated sound importer, even for exact names.
        # Reverbs have no sound resources/dependencies and relocate natively.
        if key[0]!='snde' or key not in native.paths:
            pending.append(dict(source_datum=datum,**row));continue
        group,new_datum=native.import_named(key)
        path,index=native.paths[key]
        from cache_reader import Cache
        donor=Cache(path)
        try:
            original=bytes(donor.data[donor.tags[index]['offset']:donor.tags[index]['offset']+0x48])
            address=struct.unpack_from('>I',registry.tags,(new_datum&65535)*8+4)[0]
            if registry.builder.read(address,0x48)!=original:
                raise ValueError('Exact stock reverb changed during relocation')
        finally:donor.close()
        resolved[datum]=(group,new_datum)
        evidence.append(dict(source_datum=datum,native_datum=new_datum,name=key[1],
                             donor=path.name,native_payload_unchanged=True))
    return resolved,dict(stock_reverbs=evidence,unresolved=pending,
        palette_installed=False,audio_verified=False)
