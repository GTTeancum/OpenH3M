"""Reject scenario placements that exceed the original H3 variant object table.

The original executable stores 640 records of 84 bytes at variant offset 304;
the per-type scenario start indices follow at 54064. This is independent of
rendering performance, file size, and the number of objects a mode activates.
"""
from pathlib import Path
from source_schema import load_schema


def inspect(cache):
    schema = load_schema(cache, 'scnr')
    root = next(t['offset'] for t in cache.tags.values() if t['group']=='scnr')
    counts = {}
    for block in schema:
        if block.tag != 'tagblock':
            continue
        names = {f.get('name') for f in block}
        if {'Unique ID','Type','Palette Index'} <= names:
            counts[block.get('name')] = cache.u(root+int(block.get('offset'),0))
    if not {'Scenery','Weapons','Equipment','Crates'} <= counts.keys():
        raise ValueError('Scenario placement schema changed; review variant budget audit')
    total = sum(counts.values())
    return {'counts':counts,'total':total,'limit':640,'conversion_ready':total<=640}


def inspect_quotas(cache):
    """Conservative native bound, including placed assets outside the palette.

    Actual native initialization omits some noneditable scenario assets. Count
    every distinct placed identity here, so a successful bound never relies on
    guessing which custom object will be editable. Runtime counts still verify
    the result. Palette entries themselves consume slots even when unused.
    """
    if cache.mcc:raise ValueError('Quota verification requires the serialized native cache')
    schema=load_schema(cache,'scnr')
    root=next(t['offset'] for t in cache.tags.values() if t['group']=='scnr')
    by_name={f.get('name'):f for f in schema}
    def rows(f):return cache.block(root+int(f.get('offset'),0),int(f.get('elementSize'),0))
    def valid(datum):
        tag=cache.tags.get(datum&65535)
        if tag is None or tag['salt']!=datum>>16:raise ValueError('Invalid Forge/placement quota identity')
        return datum
    palette=[]
    for cat in ('Vehicle','Weapon','Equipment','Scenery','Teleporter','Goal','Spawner'):
        palette.extend(valid(cache.u(p+12)) for p in rows(by_name['Map Variant '+cat+' Palette']))
    placed=set()
    for f in schema:
        if f.tag!='tagblock':continue
        fs={x.get('name'):x for x in f}
        if not {'Unique ID','Type','Palette Index'}<=fs.keys():continue
        name=f.get('name')
        pn={'Bipeds':'Biped Palette','Vehicles':'Vehicle Palette','Weapons':'Weapon Palette',
            'Equipment':'Equipment Palette','Machines':'Machine Palette','Controls':'Control Palette',
            'Crates':'Crates Palette'}.get(name,name+' Palette')
        objects=rows(f)
        if not objects:continue
        if pn not in by_name:raise ValueError('Unknown placement palette: '+name)
        definitions=rows(by_name[pn])
        for p in objects:
            index=cache.unpack('h',p+int(fs['Palette Index'].get('offset'),0))[0]
            if index==-1:continue
            if not 0<=index<len(definitions):raise ValueError('Invalid placed object palette index')
            placed.add(valid(cache.u(definitions[index]+12)))
    if 'Budget References' in by_name:
        placed.update(valid(cache.u(p+12)) for p in rows(by_name['Budget References']))
    extras=placed-set(palette)
    upper=len(palette)+len(extras)
    return dict(palette_entries=len(palette),placed_extra_identities=len(extras),
                conservative_upper_bound=upper,limit=256,conversion_ready=upper<=256,
                scope='Conservative serialized-data bound; verify actual native quota count at runtime')
