"""Inventory stock shader profiles and source entry points before replacing cards."""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable

source = Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map', True)
profiles = {}
try:
    strings = StringTable(source)
    for tid in (12294, 12412, 12416, 12159, 12220, 12453, 12458, 12579, 12591):
        post, = source.block(source.tags[tid]['offset'] + 40, 140)
        template_id = source.u(post + 12) & 65535
        name = source.name(template_id)
        options = [int(x) for x in name.rsplit('\\', 1)[1].split('_') if x]
        template = source.tags[template_id]['offset']
        profile = profiles.setdefault(name, dict(options=options, materials=[], exact_stock=[], near_stock=[]))
        profile['materials'].append(dict(id=tid, name=source.name(tid), blend=source.u(post+104),
            active_entries=[i for i, p in enumerate(source.block(template+36, 2)) if source.unpack('H', p)[0] >> 10],
            parameters={kind: [strings.text(source.u(p)) for p in source.block(template+off, 4)]
                        for kind, off in [('texture',108), ('float',72), ('integer',84), ('boolean',96)]}))
finally:
    source.close()

inventory = []
for path in sorted(Path('C:/X360/ISOs/H3M/maps').glob('*.map')):
    try:
        cache = Cache(str(path))
    except Exception as exc:
        inventory.append(dict(map=path.name, error=str(exc)))
        continue
    try:
        count = 0
        for tid, tag in cache.tags.items():
            if tag['group'] != 'rmt2':
                continue
            name = cache.name(tid)
            if not name or not name.startswith('shaders\\shader_templates\\_'):
                continue
            opts = [int(x) for x in name.rsplit('\\',1)[1].split('_') if x]
            count += 1
            for profile in profiles.values():
                wanted = profile['options'][:10]
                if len(opts) != 10:
                    continue
                diffs = [i for i,(a,b) in enumerate(zip(wanted,opts)) if a != b]
                if len(diffs) <= 2:
                    key = 'exact_stock' if not diffs else 'near_stock'
                    profile[key].append(dict(map=path.name, id=tid, name=name, different_categories=diffs))
        inventory.append(dict(map=path.name, shader_templates=count))
    finally:
        cache.close()

report = dict(stock_maps=inventory, profiles=profiles,
    caveat='Exact matches compare the ten original H3 categories only; MCC distortion/soft-fade/attribute options require separate entry/parameter validation. shared.map is a resource cache, not an empty tag inventory.')
Path('work/sky-bridge/remaining-card-profile-inventory.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k:dict(exact=len(v['exact_stock']),near=len(v['near_stock']),entries=v['materials'][0]['active_entries']) for k,v in profiles.items()},indent=2))
