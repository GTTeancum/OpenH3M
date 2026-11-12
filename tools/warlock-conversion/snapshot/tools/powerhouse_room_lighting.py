"""Native baked ambient fill for the dark Powerhouse machinery room.

Only C0 changes, with a smooth spatial boundary. This does not change exposure,
geometry, directional coefficients, or exterior lightmap atlas samples.
"""
import struct
import numpy as np
from resource_reader import Resource
from reach_lighting import pack_lighting_coefficients


def weights(positions):
    low = np.array([119., 223.5, 40.5])
    high = np.array([129.5, 230., 47.])
    distance = np.minimum(positions-low, high-positions).min(axis=1)
    t = np.clip(distance, 0., 1.)
    return t*t*(3.-2.*t)


def fill_vertices(payload, weight, amount):
    if not 0 <= amount <= .5 or len(payload) != len(weight)*20:
        raise ValueError('Invalid machinery-room fill')
    result = np.frombuffer(payload, np.uint8).reshape(-1, 20).copy()
    selected = np.flatnonzero(weight > 0)
    if not amount or not len(selected):
        return payload
    signed = result.view(np.int8)
    c0 = signed[selected][:, [7, 6, 5]].astype(float)/127
    c0 *= np.exp2(signed[selected, 4].astype(float)/4)[:, None]
    c0 += (amount*weight[selected])[:, None]*np.array([1., .96, .88])
    coefficients = np.zeros((len(selected), 5, 3), np.float32)
    coefficients[:, 1] = c0
    encoded = np.frombuffer(pack_lighting_coefficients(coefficients), np.uint8).reshape(-1, 20)
    result[selected, 4:8] = encoded[:, 4:8]
    return result.tobytes()


def apply(cache, bsp, lighting, source, converted, amount):
    if not amount:
        return None
    scenarios = [cache.name(k) for k,t in cache.tags.items() if t['group']=='scnr']
    if not cache.mcc or scenarios != [r'levels\multi\s3d_powerhouse\s3d_powerhouse']:
        raise ValueError('Room lighting is restricted to Powerhouse')
    collision = Resource(cache, cache.u(bsp+0x38c))
    definitions = collision.fix[collision.root+28] & 0x1fffffff
    meshes = cache.block(bsp+0x2f4, 76)
    compressions = cache.block(bsp+0x300, 44)
    pervertex = cache.block(lighting+0x100, 16)
    bindings = cache.block(lighting+0x118, 8)
    instances = cache.block(bsp+0x1c0, 120)
    if len(bindings) != len(instances):
        raise ValueError('Instance lighting count mismatch')
    buffers = source.buffers('vertex')
    selected, owners, atlas = {}, {}, []
    atlas_geometry = []
    texcoords = cache.block(lighting+0x1a0, 16)

    def positions(mesh_index, compression=-1, instance=None):
        mesh = meshes[mesh_index]
        vi = cache.unpack('h', mesh+24)[0]
        if vi == -1:
            if cache.u(mesh):
                raise ValueError('Unbound room mesh has render parts')
            return np.empty((0, 3))
        vb = buffers[vi]
        n, fmt, stride = source.unpack('IHH', vb)
        p = source.fix[vb+20]
        raw = memoryview(source.raw[{0x40000000:0, 0x60000000:1}[p&0xe0000000]])[p&0x1fffffff:]
        if fmt == 1:
            xyz = np.ndarray((n,3), '<f4', raw, strides=(stride,4)).astype(float)
        elif fmt == 2 and compression >= 0:
            bounds = np.array(cache.unpack('6f', compressions[compression]+4)).reshape(3,2)
            xyz = np.ndarray((n,3), '<u2', raw, strides=(stride,2))/65535
            xyz = xyz*(bounds[:,1]-bounds[:,0])+bounds[:,0]
        else:
            raise ValueError('Unexpected room geometry format')
        if instance is not None:
            xyz = xyz@np.array(cache.unpack('9f', instance+4)).reshape(3,3)*cache.unpack('f', instance)[0]
            xyz += cache.unpack('3f', instance+40)
        return xyz

    def bind(row, xyz, owner, mesh_index, texcoord_vi=None):
        weight = weights(xyz)
        block = cache.unpack('h', row+2)[0]
        if block < 0:
            if np.any(weight):
                atlas.append(owner)
            if len(xyz) and cache.unpack('h', row)[0] >= 0:
                if cache.unpack('h', row)[0] != 0:
                    raise ValueError('Additional room atlas requires explicit mapping')
                mesh = meshes[mesh_index]
                if texcoord_vi is None:
                    candidates = [v for v in cache.unpack('8h', mesh+24)
                                  if v >= 0 and source.unpack('H', buffers[v]+4)[0] == 4]
                    if len(candidates) != 1:
                        raise ValueError('Ambiguous cluster lightmap texcoords')
                    texcoord_vi = candidates[0]
                vb = buffers[texcoord_vi]
                if source.unpack('IHH', vb) != (len(xyz), 4, 4):
                    raise ValueError('Room atlas texcoord count/layout mismatch')
                p = source.fix[vb+20]
                data = memoryview(source.raw[{0x40000000:0,0x60000000:1}[p&0xe0000000]])[p&0x1fffffff:]
                uv = np.frombuffer(data[:len(xyz)*4], '<u2').reshape(-1,2)/65535.
                ib = source.buffers('index')[cache.unpack('h', mesh+40)[0]]
                p = source.fix[ib+16]
                data = memoryview(source.raw[{0x40000000:0,0x60000000:1}[p&0xe0000000]])[p&0x1fffffff:]
                indices = np.frombuffer(data[:source.unpack('I', ib+4)[0]], '<u2')
                triangles = []
                for part in cache.block(mesh,16):
                    start,count = cache.unpack('2H',part+4)
                    seq = indices[start:start+count]
                    if not count:
                        continue
                    primitive = cache.data[mesh+48]
                    if primitive == 3:
                        triangles.append(seq.reshape(-1,3))
                    elif primitive == 5 and count >= 3:
                        triangles.append(np.lib.stride_tricks.sliding_window_view(seq,3))
                    else:
                        raise ValueError('Unsupported room atlas primitive')
                if triangles:
                    atlas_geometry.append((xyz, uv, np.concatenate(triangles), owner))
            return
        vi = cache.u(pervertex[block]+12)
        n, fmt, stride = source.unpack('IHH', buffers[vi])
        if n != len(weight) or fmt != 6:
            raise ValueError('Room geometry/light vertices do not correspond')
        if vi in selected and not np.array_equal(selected[vi], weight):
            raise ValueError('Lighting buffer shared across different room weights')
        selected[vi] = weight
        owners.setdefault(vi, []).append(owner)

    for index, (at, row) in enumerate(zip(instances, bindings)):
        definition = cache.unpack('h', at+52)[0]
        mesh, compression = collision.unpack('hh', definitions+definition*196+188)
        if mesh >= 0:
            ti = cache.unpack('h',at+56)[0]
            vi = cache.unpack('h',texcoords[ti]+12)[0] if ti >= 0 else None
            bind(row, positions(mesh, compression, at), f'instance:{index}', mesh, vi)
    clusters = cache.block(bsp+0xc4, 280)
    cluster_lighting = cache.block(lighting+0x10c, 4)
    if len(clusters) != len(cluster_lighting):
        raise ValueError('Cluster lighting count mismatch')
    for index, (at, row) in enumerate(zip(clusters, cluster_lighting)):
        mesh = cache.unpack('h', at+0xd8)[0]
        if mesh >= 0:
            bind(row, positions(mesh), f'cluster:{index}', mesh)
    control, fixes = converted['control'], dict(converted['fixups'])
    table = fixes[28]&0x1fffffff
    raw = bytearray(converted['raw'])
    changed = []
    for vi, weight in selected.items():
        if not np.any(weight):
            continue
        descriptor = fixes[table+vi*12]&0x1fffffff
        n, fmt, stride = struct.unpack_from('>IHH', control, descriptor)
        if (n, fmt, stride) != (len(weight), 6, 20):
            raise ValueError('Converted room lighting layout changed')
        offset = fixes[descriptor+20]&0x1fffffff
        raw[offset:offset+n*20] = fill_vertices(bytes(raw[offset:offset+n*20]), weight, amount)
        changed.append(dict(buffer=vi, owners=owners[vi], vertices=int(np.count_nonzero(weight))))
    converted['raw'] = bytes(raw)
    if not hasattr(cache, 'powerhouse_room_atlas_geometry'):
        cache.powerhouse_room_atlas_geometry = {}
    cache.powerhouse_room_atlas_geometry[lighting] = atlas_geometry
    return dict(amount=amount, bounds=[[119.,223.5,40.5],[129.5,230.,47.]],
                fade_distance=1., buffers=changed, atlas_owners_for_separate_bake=atlas)
