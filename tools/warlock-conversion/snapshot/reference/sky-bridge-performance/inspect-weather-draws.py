"""Join a native camera location to authored weather and actual shader submissions.

Requires compare-native-state.py and trace-match-program-slices.py outputs.
This records draw evidence only, not acceptance of visible rain.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ref = Path(__file__).resolve().parent
repo = ref.parents[4]
sys.path.insert(0, str(repo / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from string_ids import StringTable

spec = importlib.util.spec_from_file_location('observer', ref / 'compare-native-observer.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
args = parser.parse_args()
run = args.run.resolve()
run.relative_to(repo / 'work/sky-bridge')
snapshot = json.loads((run / 'guest-snapshot.json').read_text())
camera = observer.read_observer(snapshot)
bsp, cluster, leaf = struct.unpack('>BBH', bytes.fromhex(camera['result_location_bytes']))
assert bsp == 0
cache = Cache(repo / 'work/sky-bridge/payload-32/sky_bridge.map')
strings = StringTable(cache)
base = cache.tags[9225]['offset']
clusters = cache.block(base + 0xb4, 0xdc)
assert cluster < len(clusters)
row = clusters[cluster]
palette_index = cache.unpack('b', row + 0x19)[0]
palettes = cache.block(base + 0x84, 8)
assert 0 <= palette_index < len(palettes)
setting_index = cache.unpack('h', palettes[palette_index] + 4)[0]
settings = cache.block(cache.tags[10699]['offset'] + 0x34, 0xa4)
assert 0 <= setting_index < len(settings)
setting = settings[setting_index]
weather = cache.u(setting + 0x8c + 12)

# Resolve both rain particle tags through their actual render templates.
particles = []
for tag_id in (10702, 10704):
    post, = cache.block(cache.tags[tag_id]['offset'] + 0x64, 132)
    template = cache.u(post + 12) & 65535
    assert cache.tags[template]['group'] == 'rmt2'
    start = cache.tags[template]['offset']
    particles.append({'tag': tag_id, 'name': cache.name(tag_id),
        'template': template, 'vertex_program': cache.u(start + 12) & 65535,
        'pixel_program': cache.u(start + 28) & 65535})
pixel_tags = {p['pixel_program'] for p in particles}
vertex_tags = {p['vertex_program'] for p in particles}
assert pixel_tags == {1896} and vertex_tags == {1895}
matches = json.loads((run / 'program-slice-matches.json').read_text())
identities = {}
for item in matches:
    tags = {p['id'] for match in item['matches'] for p in match['programs']}
    if tags & (pixel_tags | vertex_tags):
        identities[item['shader']] = {'stage': item['stage'], 'possible_tags': sorted(tags),
            'matches': item['matches']}
pixel_ids = {key for key, value in identities.items() if value['stage'] == 1}
vertex_ids = {key for key, value in identities.items() if value['stage'] == 0}
frames, emitted, rain_ps, rain_vs = Counter(), Counter(), Counter(), Counter()
stops = []
rain_counts = Counter()
with (run / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        assert len(header) == 8
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        assert len(data) == size
        if kind == 1:
            draw = struct.unpack('<11Q', data)
            frames[draw[1]] += 1
        elif kind == 5:
            assert struct.unpack('<QQ', data) == draw[:2]
            emitted[draw[1]] += 1
            if draw[4] in pixel_ids:
                rain_ps[draw[1]] += 1
                rain_counts[draw[6]] += 1
            if draw[3] in vertex_ids:
                rain_vs[draw[1]] += 1
        elif kind == 9:
            stops.append(struct.unpack('<Q', data)[0])
with (run / 'draws.bin').open('rb') as stream:
    trace_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
report = {'camera': camera, 'native_location': {'bsp': bsp, 'cluster': cluster, 'leaf': leaf},
    'cluster_bounds': list(cache.unpack('6f', row)), 'atmosphere_palette_index': palette_index,
    'atmosphere_setting_index': setting_index, 'atmosphere_name': strings.text(cache.u(setting + 4)),
    'weather_datum': hex(weather), 'weather_tag': None if weather == 0xffffffff else weather & 65535,
    'rain_particles': particles, 'matching_shader_identities': identities,
    'trace': {'sha256': trace_hash, 'frames': len(frames), 'first_frame': min(frames),
        'last_frame': max(frames), 'recorded_draws': sum(frames.values()),
        'emitted_draws': sum(emitted.values()), 'stop_reasons': stops},
    'rain_pixel_shader_emitted_frames': dict(rain_ps), 'rain_vertex_shader_emitted_frames': dict(rain_vs),
    'rain_pixel_shader_draw_count': sum(rain_ps.values()), 'rain_index_counts': dict(rain_counts),
    'limitations': ['Shader byte identity and submitted draws do not establish visible particle contribution.',
        'Shared program users remain ambiguous until texture bindings and particle records are attributed.',
        'The translated outdoor view is separate from the saved human flicker view.'],
    'credit': json.loads((ref / 'sky-pixel-probe-build.json').read_text())['credit']}
cache.close()
(run / 'weather-draw-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ('native_location', 'atmosphere_name',
    'weather_tag', 'trace', 'rain_pixel_shader_draw_count', 'rain_index_counts')}))
