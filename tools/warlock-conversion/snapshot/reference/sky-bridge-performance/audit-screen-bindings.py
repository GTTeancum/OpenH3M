"""Join saved billboard draw fetch headers to the two repaired resource prefixes."""
import argparse
import array
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys

ref = Path(__file__).resolve().parent
repo = ref.parents[4]
sys.path.insert(0, str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('run', type=Path)
args = p.parse_args()
run = args.run.resolve()
run.relative_to(repo/'work/sky-bridge')
configuration = json.loads((run/'recording-configuration.json').read_text(encoding='utf-8-sig'))
candidate = configuration.get('candidate', 32)
path = repo/f'work/sky-bridge/payload-{candidate}/sky_bridge.map'
cache = Cache(path)
textures = []
for tag in (9767, 9772):
    row, = cache.block(cache.tags[tag]['offset']+96, 48)
    handle, = cache.block(cache.tags[tag]['offset']+140, 8)
    resource = Resource(cache, cache.u(handle))
    assert resource.fix[12] == 0x40000000
    textures.append({'tag': tag, 'dimensions': list(cache.unpack('HH', row+4)),
        'mips': cache.data[row+20]+1, 'raw_bytes': len(resource.raw[0]),
        'prefix_sha256': hashlib.sha256(resource.raw[0][:512]).hexdigest()})
cache.close()
prefixes = defaultdict(set)
with (run/'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        assert len(data) == size
        if kind == 6:
            address = struct.unpack('<4Q', data)[1]
        elif kind == 7:
            prefixes[address].add(hashlib.sha256(data).hexdigest())
regs = array.array('I', [0])*0x5003
states = Counter()
frames = defaultdict(set)
with (run/'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        if kind == 1:
            draw = struct.unpack('<11Q', data)
        elif kind == 2:
            for i, value in struct.iter_unpack('<II', data):
                regs[i] = value
        elif kind == 5:
            assert struct.unpack('<QQ', data) == draw[:2]
            for slot in range(16):
                words = tuple(regs[0x4800+6*slot:0x4806+6*slot])
                if words[0] & 3 != 2:
                    continue
                base = words[1] & 0xfffff000
                dimensions = [1+(words[2]&8191), 1+(words[2]>>13&8191)]
                matches = [t for t in textures if dimensions == t['dimensions']
                    and prefixes[base] == {t['prefix_sha256']}]
                if not matches:
                    continue
                assert len(matches) == 1
                tex = matches[0]
                max_lod = words[4]>>6&15
                packed = words[5]>>11&1
                mip_address = words[5]&0xfffff000
                assert max_lod == tex['mips']-1
                if tex['mips'] > 1:
                    assert packed
                    if mip_address:
                        assert mip_address-base == (262144 if tex['tag']==9767 else 0)
                key = (tex['tag'], draw[4], slot, words)
                states[key] += 1
                frames[tex['tag']].add(draw[1])
assert set(frames) == {9767, 9772}
result = {'candidate': candidate, 'map_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'textures': textures, 'states': [], 'frames_by_texture': {str(k): len(v) for k,v in frames.items()},
    'limitation': 'Dimensions and CPU resource prefix identify the binding; native header validation does not prove every GPU texel or visual readability.'}
for (tag, shader, slot, words), count in states.items():
    result['states'].append({'tag': tag, 'shader': shader, 'slot': slot, 'draws': count,
        'min_lod': words[4]>>2&15, 'max_lod': words[4]>>6&15,
        'packed_mips': bool(words[5]>>11&1), 'base_address': hex(words[1]&0xfffff000),
        'mip_address': hex(words[5]&0xfffff000),
        'effective_max_lod': (words[4]>>6&15) if words[5]&0xfffff000 else 0,
        'missing_mip_address': bool((words[4]>>6&15) and not (words[5]&0xfffff000)),
        'fetch_words': [hex(w) for w in words]})
result['all_declared_levels_addressable'] = not any(s['missing_mip_address'] for s in result['states'])
result['all_authored_levels_addressable'] = result['all_declared_levels_addressable'] and all(
    t['mips'] == {9767: 9, 9772: 8}[t['tag']] for t in textures)
(run/'screen-binding-analysis.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
