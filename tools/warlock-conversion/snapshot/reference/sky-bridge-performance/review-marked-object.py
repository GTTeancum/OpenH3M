"""Read existing native captures and draw trace at the user's marked object.

No game launch, image edits, new captures, or rendering changes. Projected
triangle hits are candidate attribution, not proof of GPU-visible ownership.
"""
import array
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import numpy as np
from PIL import Image

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
sys.path.insert(0, str(REPO / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
spec = importlib.util.spec_from_file_location('model', REF / 'trace-model-draws.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert Path.cwd().resolve() == REPO
    output = REPO / 'work/sky-bridge/marked-object-review'
    output.mkdir(exist_ok=True)
    visual = read(REF / 'candidate36-visual-review-result.json')
    box = (640, 170, 668, 194)
    regions = []
    for frame in visual['frames']:
        path = REPO / frame['path']
        assert sha(path) == frame['sha256']
        with Image.open(path) as im:
            assert im.size == (1152, 640)
            # Read pixels only. Keep original proof images unchanged.
            data = np.asarray(im)[:, :, :3]
            regions.append(data[box[1]:box[3], box[0]:box[2]].copy())
    pixels = np.stack(regions).astype(int)
    variation = pixels.max(0) - pixels.min(0)
    y, x, channel = np.unravel_index(variation.argmax(), variation.shape)
    image_review = dict(region_xyxy=box, original_images_unchanged=True,
        frames=[dict(order=i+1, path=f['path'], sha256=f['sha256'],
            mean_rgb=pixels[i].mean((0, 1)).tolist(),
            max_channel=int(pixels[i].max())) for i, f in enumerate(visual['frames'])],
        largest_channel_variation=dict(x=int(x+box[0]), y=int(y+box[1]),
            channel=int(channel), range=int(variation.max()),
            rgb_by_frame=pixels[:, y, x].tolist()),
        limitation='Region includes background and silhouette movement. Color changes do not identify the responsible draw or prove a lighting bug.')
    core = pixels[:, 5:19, 2:18]
    core_variation = core.max(0)-core.min(0)
    cy, cx, cc = np.unravel_index(core_variation.argmax(), core_variation.shape)
    image_review['object_core'] = dict(region_xyxy=[642,175,658,189],
        most_variable_pixel=[int(cx+642),int(cy+175)], channel=int(cc),
        range=int(core_variation.max()), rgb_by_frame=core[:,cy,cx].tolist(),
        fixed_point_rgb={f'{px},{py}':pixels[:,py-box[1],px-box[0]].tolist()
            for px,py in [(646,180),(650,180),(653,180),(650,184)]})

    old = Cache(REPO / 'work/sky-bridge/payload-32/sky_bridge.map')
    cache = Cache(REPO / 'work/sky-bridge/payload-36/sky_bridge.map')
    weather_tags = []
    for tid in (10699, 10701, 10702, 10703, 10704, 10705):
        chunks = []
        for c in (old, cache):
            start = c.tags[tid]['offset']
            end = min(t['offset'] for t in c.tags.values() if t['offset'] > start)
            chunks.append(bytes(c.data[start:end]))
        assert chunks[0] == chunks[1]
        weather_tags.append(dict(tag=tid, name=cache.name(tid), group=cache.tags[tid]['group'],
            bytes=len(chunks[1]), sha256=hashlib.sha256(chunks[1]).hexdigest(), unchanged=True))
    clusters = []
    for index in (23, 45):
        chunks = []
        for c in (old, cache):
            row = c.block(c.tags[9225]['offset'] + 0xb4, 0xdc)[index]
            chunks.append(bytes(c.data[row:row+0xdc]))
        assert chunks[0] == chunks[1]
        clusters.append(dict(cluster=index, unchanged=True, sha256=hashlib.sha256(chunks[1]).hexdigest()))
    old.close()

    run = REPO / 'work/sky-bridge/reproduction-47'
    config = read(run / 'recording-configuration.json')
    assert sha(REPO / 'work/sky-bridge/payload-36/sky_bridge.map') == config['map_sha256']
    materials = {p['shader']: {m['id'] for s in p['matches'] for program in s['programs']
        for t in program['templates'] for m in t['materials']}
        for p in read(run / 'program-slice-matches.json')}
    geometry = defaultdict(dict)
    for prefix in read(run / 'geometry-prefix-matches.json')['matches']:
        for g in prefix['matches']:
            if g['index_count'] * 2 == prefix['length']:
                geometry[prefix['address']][g['owner'], g['mesh'], g['part']] = g
    prefixes = defaultdict(set)
    for kind, raw in model.packets(run / 'draws.bin'):
        if kind == 6:
            _, address, _, _ = struct.unpack('<4Q', raw)
        elif kind == 7:
            prefixes[address].add(hashlib.sha256(raw).hexdigest())
    base, = cache.block(cache.tags[9894]['offset'] + 4, 436)
    meshes = cache.block(base + 0x134, 76)
    resource = Resource(cache, cache.u(base + 0x1ac))
    vertices, indices = resource.buffers('vertex'), resource.buffers('index')

    def raw_buffer(field, size):
        p = resource.fix[field]
        return resource.raw[(p >> 29)-2][(p & 0x1fffffff):(p & 0x1fffffff)+size]

    buffers = {}
    def triangle_hits(clip, ind):
        tri = clip[ind[np.all(clip[ind, 3] > 0, axis=1)]]
        if not len(tri):
            return None
        xy = (tri[:, :, :2] / tri[:, :, 3, None] * [.5, -.5] + [.5, .5]) * [1152, 640]
        intersects = (xy[:, :, 0].max(1) >= box[0]) & (xy[:, :, 0].min(1) < box[2]) & (xy[:, :, 1].max(1) >= box[1]) & (xy[:, :, 1].min(1) < box[3])
        xy, tri = xy[intersects], tri[intersects]
        if not len(xy):
            return None
        a, b, c = xy[:, 0], xy[:, 1], xy[:, 2]
        ab, ac = b-a, c-a
        det = ab[:, 0]*ac[:, 1]-ab[:, 1]*ac[:, 0]
        valid = np.abs(det) > 1e-12
        safe = np.where(valid, det, 1)
        depth = tri[:,:,2]/tri[:,:,3]
        hits = []
        sample_depths = []
        for py in range(box[1], box[3]):
            for px in range(box[0], box[2]):
                ap = [px+.5, py+.5]-a
                s = (ap[:, 0]*ac[:, 1]-ap[:, 1]*ac[:, 0])/safe
                t = (ab[:, 0]*ap[:, 1]-ab[:, 1]*ap[:, 0])/safe
                inside = valid & (s >= 0) & (t >= 0) & (s+t <= 1)
                if np.any(inside):
                    hits.append([px, py])
                    if [px,py] in [[646,180],[650,180],[651,178],[653,180],[655,183]]:
                        z=depth[:,0]*(1-s-t)+depth[:,1]*s+depth[:,2]*t
                        sample_depths.append(dict(x=px,y=py,ndc_z=z[inside].tolist()))
        if not hits:
            return None
        return dict(hit_pixels=len(hits), hit_xy_min=np.min(hits, 0).tolist(),
            hit_xy_max=np.max(hits, 0).tolist(), sample_depths=sample_depths)

    def project(g, constants):
        key = g['mesh'], g['part']
        if key not in buffers:
            mesh = meshes[g['mesh']]
            vb = vertices[cache.unpack('h', mesh+24)[0]]
            ib = indices[cache.unpack('h', mesh+40)[0]]
            count, fmt, stride = resource.unpack('IHH', vb)
            data = raw_buffer(vb+20, count*stride)
            if fmt == 2:
                xyz = np.ndarray((count, 3), dtype='>u2', buffer=data, strides=(stride, 2)).astype(float)/65535
            elif fmt == 1:
                xyz = np.ndarray((count, 3), dtype='>f4', buffer=data, strides=(stride, 4)).astype(float)
            else:
                return None
            ind = np.frombuffer(raw_buffer(ib+16, resource.unpack('I', ib+4)[0]), dtype='>u2')
            ind = ind[g['index_start']:g['index_start']+g['index_count']]
            if len(ind) % 3 or ind.max() >= count:
                return None
            buffers[key] = xyz, ind.reshape(-1, 3), fmt
        xyz, ind, fmt = buffers[key]
        if fmt == 2:
            local = xyz * constants[12, :3] + constants[13, :3]
            world = np.c_[local, np.ones(len(local))] @ constants[16:19].T
        else:
            world = xyz
        clip = np.c_[world, np.ones(len(world))] @ constants[:4].T
        return triangle_hits(clip, ind)

    regs = array.array('I', [0])*0x5003
    seen = set()
    projected = []
    first_frame = None
    for kind, data in model.packets(run / 'draws.bin'):
        if kind == 1:
            seq, frame, _, vs, ps, primitive, count, address, *_ = struct.unpack('<11Q', data)
            if first_frame is None:
                first_frame = frame
            if frame != first_frame:
                break
        elif kind == 2:
            for index, value in struct.iter_unpack('<II', data):
                regs[index] = value
        elif kind == 5:
            vertex_address = regs[0x48be] & ~3
            candidates = [g for g in geometry[address].values() if g['owner'] == 9894
                and g['index_count'] == count and g['target_material'] in materials.get(ps, set())
                and prefixes.get(vertex_address) == {g['vertex_prefix_sha256']}]
            if len(candidates) != 1 or primitive != 4:
                continue
            constants = np.frombuffer(regs[0x4000:0x4400].tobytes(), dtype='<f4').reshape(256, 4).astype(float)
            sx, ox, sy, oy = np.frombuffer(regs[0x210f:0x2113].tobytes(), dtype='<f4')
            if (sx, ox, sy, oy) != (576, 576, -320, 320):
                continue
            g = candidates[0]
            key = g['mesh'], g['part'], constants[:19].tobytes()
            if key in seen:
                continue
            seen.add(key)
            hit = project(g, constants)
            if hit:
                projected.append(dict(sequence=seq, frame=frame, vs=vs, ps=ps, geometry=g, projection=hit))
    skinned=[]
    for group in read(run/'model-draw-analysis.json')['groups']:
        if len(group['candidates']) != 1:
            continue
        g=group['candidates'][0]
        if g['vertex_format'] != 3:
            continue
        root=cache.tags[g['owner']]['offset']
        mesh=cache.block(root+0x68,76)[g['mesh']]
        r=Resource(cache,cache.u(root+0xe0))
        vb=r.buffers('vertex')[cache.unpack('h',mesh+24)[0]]
        ib=r.buffers('index')[cache.unpack('h',mesh+40)[0]]
        def raw_model(field,size):
            ptr=r.fix[field]
            return r.raw[(ptr>>29)-2][(ptr&0x1fffffff):(ptr&0x1fffffff)+size]
        count,fmt,stride=r.unpack('IHH',vb)
        assert stride==32
        data=raw_model(vb+20,count*stride)
        xyz=np.ndarray((count,3),dtype='>u2',buffer=data,strides=(stride,2)).astype(float)/65535
        bones=np.ndarray((count,4),dtype='u1',buffer=data,offset=24,strides=(stride,1))
        weights=np.ndarray((count,4),dtype='u1',buffer=data,offset=28,strides=(stride,1)).astype(float)
        assert np.all(weights.sum(1)>0)
        weights/=weights.sum(1,keepdims=True)
        part=cache.block(mesh,16)[g['part']]
        start,length=cache.unpack('HH',part+4)
        ind=np.frombuffer(raw_model(ib+16,r.unpack('I',ib+4)[0]),dtype='>u2')[start:start+length]
        if group['primitive']==6:
            ind=np.stack([ind[:-2],ind[1:-1],ind[2:]],axis=1)
            ind=ind[np.all(ind!=65535,axis=1)]
        elif group['primitive']==4:
            ind=ind.reshape(-1,3)
        else:
            continue
        constants=np.frombuffer(bytes.fromhex(group['first_vertex_constants_0_255']),dtype='<f4').reshape(256,4).astype(float)
        local=np.c_[xyz*constants[12,:3]+constants[13,:3],np.ones(count)]
        palette=constants[16:240].reshape(-1,4)[:(int(bones.max())+1)*3].reshape(-1,3,4)
        blended=np.einsum('vi,vijk->vjk',weights,palette[bones])
        world=np.einsum('vij,vj->vi',blended,local)
        clip=np.c_[world,np.ones(count)]@constants[:4].T
        hit=triangle_hits(clip,ind)
        if hit:
            skinned.append(dict(owner=g['owner'],part=g['part'],name=g['name'],vs=group['vs'],ps=group['ps'],projection=hit))
    cache.close()
    rain = read(REF / 'candidate32-outdoor-rain-result.json')
    report = dict(image_review=image_review,
        outdoor_rain=dict(authored=True, measured_outdoor_contribution=True,
            prior_runtime_candidate=32, installed_weather_tags_unchanged=weather_tags,
            native_cluster_records_unchanged=clusters, outdoor_view=rain['outdoor_view'],
            indoor_control=rain['indoor_control'],
            verdict='Outdoor rain is authored and measured in the outdoor test. Saved indoor camera disables weather particles; cards are separate. Visual outdoor density remains unverified.'),
        prior_searchlight_projection=read(REPO / 'work/sky-bridge/moving-model-audit/projected-skinned-parts.json')['parts'],
        current_region_geometry_candidates=projected,
        current_region_skinned_candidates=skinned,
        limitations=['Offline projected triangle candidates are not a GPU visibility or ownership result.',
            'The four-frame earlier trace is not synchronized with the six screenshots.',
            'No correction to the arrowed object has been made.'],
        credit=visual['credit'])
    path = output / 'review.json'
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(object_core=image_review['object_core'], weather_tags_unchanged=len(weather_tags),
        projected_candidate_count=len(projected), skinned_candidates=skinned), indent=2))


if __name__ == '__main__':
    main()
