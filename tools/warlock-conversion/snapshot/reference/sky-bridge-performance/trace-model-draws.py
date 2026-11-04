"""Attribute custom moving-fabric/searchlight draws by index and vertex bytes.

The original BSP matcher does not cover mode resources. This read-only decoder
keeps ambiguous model identities explicit and never equates submission with
visible coverage or correct animation.
"""
import argparse
import array
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import sys
import numpy as np

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
sys.path.insert(0, str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource


def packets(path):
    with path.open('rb') as f:
        while header := f.read(8):
            assert len(header) == 8
            kind, size = struct.unpack('<II', header)
            assert size <= 1024*1024
            raw = f.read(size)
            assert len(raw) == size
            yield kind, raw


def analyze(run):
    run = run.resolve()
    run.relative_to(REPO/'work/sky-bridge')
    configuration = run/'recording-configuration.json'
    candidate = json.loads(configuration.read_text())['candidate'] if configuration.exists() else 32
    cache_path = REPO/f'work/sky-bridge/payload-{candidate}/sky_bridge.map'
    if configuration.exists():
        assert hashlib.sha256(cache_path.read_bytes()).hexdigest() == json.loads(configuration.read_text())['map_sha256']
    cache = Cache(cache_path)
    cache.shared_paths = {'maps\\shared.map': Path('C:/X360/ISOs/H3M/maps/shared.map')}
    cache.decoded_pages = {}
    report = json.loads((REPO/'work/sky-bridge/build-32.json').read_text())
    names = {int(t['datum'], 16) & 65535: t['source'] for t in report['tags'] if 'datum' in t}
    selected = {int(t['datum'], 16) & 65535: t['source'] for t in report['tags']
        if t.get('group') == 'mode' and any(s in t['source'] for s in
            ('sbr_envelope_', 'sbr_panel_fabric_', 'search_light_'))}
    meshes = []
    for tid, name in selected.items():
        tag = cache.tags[tid]
        assert tag['group'] == 'mode'
        at = tag['offset']
        materials = cache.block(at+0x48, 36)
        resource = Resource(cache, cache.u(at+0xe0))
        vertices, indices = resource.buffers('vertex'), resource.buffers('index')
        def raw(field, size):
            ptr = resource.fix[field]
            stream, offset = (ptr>>29)-2, ptr & 0x1fffffff
            assert stream in (0, 1) and offset+size <= len(resource.raw[stream])
            return resource.raw[stream][offset:offset+size]
        for mi, mesh in enumerate(cache.block(at+0x68, 76)):
            vi, ii = cache.unpack('h', mesh+24)[0], cache.unpack('h', mesh+40)[0]
            if vi < 0 or ii < 0:
                continue
            vertex, index = vertices[vi], indices[ii]
            count, fmt, stride = resource.unpack('IHH', vertex)
            vb = raw(vertex+20, count*stride)
            ib = raw(index+16, resource.unpack('I', index+4)[0])
            for pi, part in enumerate(cache.block(mesh, 16)):
                slot = cache.unpack('h', part)[0]
                start, length = cache.unpack('HH', part+4)
                target = cache.u(materials[slot]+12) & 65535
                prefix = ib[start*2:start*2+min(512, length*2)]
                assert len(prefix) == min(512, length*2)
                palette = set()
                if fmt == 3:
                    assert stride == 32
                    used_vertices = set(struct.unpack('>'+str(length)+'H', ib[start*2:(start+length)*2]))-{65535}
                    assert max(used_vertices) < count
                    # Include all four index bytes, even zero-weight entries.
                    # This is a conservative palette-integrity check, not a
                    # replacement for executing the shader's weighted skinning.
                    palette = {vb[i*stride+24+j] for i in used_vertices for j in range(4)}
                    assert max(palette) < 75
                meshes.append(dict(owner=tid, name=name, mesh=mi, part=pi,
                    material=target, material_name=names.get(target, cache.name(target)),
                    index_count=length, vertex_count=count, vertex_format=fmt,
                    vertex_stride=stride, palette_indices=sorted(palette),
                    vertex_prefix_sha256=hashlib.sha256(vb[:512]).hexdigest(),
                    index_prefix_sha256=hashlib.sha256(prefix).hexdigest()))
    cache.close()
    prefixes = defaultdict(set)
    for kind, raw in packets(run/'draws.bin'):
        if kind == 6:
            _, address, _, _ = struct.unpack('<4Q', raw)
        elif kind == 7:
            prefixes[address].add(hashlib.sha256(raw).hexdigest())
    programs = json.loads((run/'program-slice-matches.json').read_text())
    materials = {p['shader']: {m['id'] for s in p['matches'] for program in s['programs']
        for template in program['templates'] for m in template['materials']} for p in programs}
    reflected = {p['shader']: {f['name']: f for s in p['matches'] for program in s['programs']
        for f in program['reflection'] if f['register_set'] == 2} for p in programs}
    regs = array.array('I', [0])*0x5003
    groups, lookup, previous_palettes = {}, {}, {}
    calls, stops = [], []
    draws, ambiguous = 0, 0
    for kind, raw in packets(run/'draws.bin'):
        if kind == 1:
            seq, frame, ns, vs, ps, primitive, count, address, length, fmt, endian = struct.unpack('<11Q', raw)
        elif kind == 2:
            for index, value in struct.iter_unpack('<II', raw):
                regs[index] = value
        elif kind == 5:
            assert struct.unpack('<2Q', raw) == (seq, frame)
            vertex_address = regs[0x48be] & 0xfffffffc
            key = address, count, ps, vertex_address
            if key not in lookup:
                lookup[key] = [m for m in meshes if m['index_count'] == count
                    and prefixes.get(address) == {m['index_prefix_sha256']}
                    and prefixes.get(vertex_address) == {m['vertex_prefix_sha256']}
                    and m['material'] in materials.get(ps, set())]
            matched = lookup[key]
            call = dict(sequence=seq, frame=frame, vs=vs, ps=ps, index_count=count,
                candidates=[dict(owner=m['owner'], mesh=m['mesh'], part=m['part']) for m in matched],
                color_mask=regs[0x2104], mode_control=regs[0x2208],
                depth_control=regs[0x2200], surface_info=regs[0x2000])
            calls.append(call)
            if not matched:
                continue
            draws += 1
            ambiguous += len(matched) != 1
            group_key = tuple((m['owner'],m['mesh'],m['part']) for m in matched), vs, ps
            if group_key not in groups:
                groups[group_key] = dict(candidates=matched, vs=vs, ps=ps, frames=Counter(),
                    first_vertex_constants_0_255=regs[0x4000:0x4400].tobytes().hex(),
                    camera_constants=defaultdict(list), vertex_parameters={}, pixel_parameters={},
                    draw_index_format=fmt, draw_index_endian=endian, primitive=primitive,
                    vertex_lighting_constants_240_243=defaultdict(list),
                    vertex_skinning_range_sha256=defaultdict(list), bone_palette_checks=[])
            g = groups[group_key]
            assert (g['draw_index_format'], g['draw_index_endian'], g['primitive']) == (fmt, endian, primitive)
            g['frames'][frame] += 1
            g['camera_constants'][regs[0x4000:0x4020].tobytes().hex()].append(frame)
            # The captured skinned VS reads c240..243 directly, despite having
            # no named reflection fields. These values must not be omitted.
            g['vertex_lighting_constants_240_243'][regs[0x43c0:0x43d0].tobytes().hex()].append(frame)
            skinning = regs[0x4040:0x43c0].tobytes()
            g['vertex_skinning_range_sha256'][hashlib.sha256(skinning).hexdigest()].append(frame)
            if vs == 15518101065676308936:
                # Offline disassembly confirms c[16+3*index]..c[18+3*index].
                assert struct.unpack('<f', regs[0x43f4:0x43f5].tobytes())[0] == 3.0
                indices_used = sorted({i for m in matched for i in m['palette_indices']})
                palette = np.array([struct.unpack('<12f', regs[0x4040+12*i:0x404c+12*i].tobytes())
                                    for i in indices_used]).reshape(-1,3,4)
                assert np.isfinite(palette).all(), 'Non-finite referenced bone matrix'
                determinant = np.linalg.det(palette[:,:,:3])
                row = dict(frame=frame, minimum_determinant=float(determinant.min()),
                    maximum_determinant=float(determinant.max()),
                    maximum_abs_translation=float(np.abs(palette[:,:,3]).max()))
                previous = previous_palettes.get(group_key)
                if previous is not None and frame == previous[0]+1:
                    row['maximum_matrix_component_step'] = float(np.abs(palette-previous[1]).max())
                previous_palettes[group_key] = frame,palette
                g['bone_palette_checks'].append(row)
            for shader, base, field in ((vs,0x4000,'vertex_parameters'),(ps,0x4400,'pixel_parameters')):
                for name, f in reflected.get(shader, {}).items():
                    begin = base+f['register']*4
                    value = regs[begin:begin+f['count']*4].tobytes().hex()
                    g[field].setdefault(name, {}).setdefault(value, []).append(frame)
        elif kind == 9:
            stops.append(struct.unpack('<Q', raw)[0])
    result = dict(trace=str(run.relative_to(REPO)), candidate_models=selected, parts=meshes,
        attributed_draws=draws, ambiguous_draws=ambiguous, groups=list(groups.values()),
        limitations=['CPU index/vertex prefixes and exact shader material references identify submissions only.',
            'Shared mesh bytes can leave multiple model identities; these are explicitly retained.',
            'The skinning-register digest includes inactive palette slots; it does not validate individual bone transforms.',
            'Palette determinants/steps include every referenced index, even zero-weight entries; they do not execute weighted skinning or prove correct vertices/normals.',
            'Object roots and undeformed bounds do not prove visible triangle ownership.',
            'No bad-frame attribution, animation correctness or performance acceptance follows from this decoder.'])
    (run/'model-draw-analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    (run/'model-draw-calls.json').write_text(json.dumps(dict(calls=calls, stop_reasons=stops))+'\n')
    print(json.dumps(dict(attributed_draws=draws, ambiguous_draws=ambiguous,
        groups=[dict(models=[m['name'].split('\\')[-1] for m in g['candidates']],
                     vs=g['vs'], ps=g['ps'], frames=len(g['frames']), draws=sum(g['frames'].values()))
                for g in groups.values()])))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    analyze(p.parse_args().run)
