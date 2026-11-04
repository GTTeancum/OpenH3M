"""Compare named electrical-arc material settings in source and candidate36."""
import json
from pathlib import Path
import sys

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
sys.path.insert(0, str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from string_ids import StringTable


def inspect(path, tag, mcc):
    cache = Cache(path, mcc)
    strings = StringTable(cache)
    root = cache.tags[tag]['offset']
    post, = cache.block(root+0x64, 0x8c if mcc else 0x84)
    template_tag = cache.u(post+12)&65535
    template = cache.tags[template_tag]['offset']
    names = [strings.text(cache.u(p)) for p in cache.block(template+0x48,4)]
    values = [list(cache.unpack('4f',p)) for p in cache.block(post+0x1c,16)]
    assert len(values) >= len(names)
    texture_names = [strings.text(cache.u(p)) for p in cache.block(template+0x6c,4)]
    texture_rows = cache.block(post+0x10,28 if mcc else 24)
    assert len(texture_names) == len(texture_rows)
    textures = {}
    for name, at in zip(texture_names,texture_rows):
        bitmap = cache.u(at+12)&65535
        textures[name] = {'tag':bitmap, 'name':cache.name(bitmap),
            'bitmap_index':cache.unpack('h',at+16)[0],
            'address_filter':list(cache.unpack('2B',at+18)),
            'external_transform':list(cache.unpack('Bb',at+(21 if mcc else 20)))}
    result = {'particle':cache.name(tag),'tag':tag,'flags':cache.u(root),
        'appearance_flags':cache.u(root+16),'billboard_style':cache.unpack('h',root+20)[0],
        'sequences':list(cache.unpack('3h',root+22)),
        'template':cache.name(template_tag),'template_tag':template_tag,
        'pixel_shader':cache.u(template+28)&65535,
        'vertex_shader':cache.u(template+12)&65535,
        'named_real_constants':dict(zip(names,values)),
        'unused_real_constants':values[len(names):], 'textures':textures,
        'blend_mode':cache.u(post+0x68)}
    cache.close()
    return result


source = inspect('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',4465,True)
target = inspect(REPO/'work/sky-bridge/payload-36/sky_bridge.map',10421,False)
checks = {k:source[k]==target[k] for k in ('flags','appearance_flags',
    'billboard_style','sequences','template','named_real_constants','blend_mode')}
checks['texture_fields'] = all(
    {k:v for k,v in texture.items() if k not in ('tag','name')} ==
    {k:v for k,v in target['textures'][name].items() if k not in ('tag','name')}
    for name,texture in source['textures'].items())
report = {'source':source,'target':target,'checks':checks,
    'limitations':['Imported native tags omit debug names; source/native tag identities follow the electric_02 dependency chain.',
        'Named material equality does not prove runtime particle visibility or correct shape.'],
    'credit':json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit']}
out = REPO/'work/sky-bridge/arc-probe-build/material-audit.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(checks))
assert all(checks.values())
