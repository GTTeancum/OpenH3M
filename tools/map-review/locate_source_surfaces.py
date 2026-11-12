"""Read source world-mesh bounds for targeted native visual review positions."""
import argparse, json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from source_schema import load_schema

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('material')
p.add_argument('output', type=Path)
a = p.parse_args()
assert a.output.resolve().is_relative_to(ROOT)
c = Cache(a.source, True)
rows = []
try:
    bsps = [t['offset'] for t in c.tags.values() if t['group'] == 'sbsp']
    lightmaps = [t['offset'] for t in c.tags.values() if t['group'] == 'Lbsp']
    assert len(bsps) == len(lightmaps) == 1, 'Multi-BSP mapping requires explicit association'
    material_field = next(x for x in load_schema(c, 'sbsp') if x.attrib.get('name') == 'Materials')
    names = [c.name(c.u(m + 12) & 65535) for m in c.block(bsps[0] + int(material_field.attrib['offset'], 0), 36)]
    root = lightmaps[0]
    instance_field = next(x for x in load_schema(c, 'sbsp') if x.attrib.get('name') == 'Instanced Geometry Instances')
    instances = c.block(bsps[0] + int(instance_field.attrib['offset'], 0), int(instance_field.attrib['elementSize'], 0))
    meshes = c.block(root + 0x134, 76)
    mesh_instances = {}
    for mesh in meshes:
        for bucket in c.block(mesh + 52, 16):
            target = c.unpack('h', bucket)[0]
            mesh_instances.setdefault(target, set()).update(c.unpack('h', at)[0] for at in c.block(bucket + 4, 2))
    r = Resource(c, c.u(root + 0x1ac))
    vertices, indices = r.buffers('vertex'), r.buffers('index')
    def raw(field, size):
        ptr = r.fix[field]
        offset = ptr & 0x1fffffff
        return r.raw[(ptr >> 29) - 2][offset:offset + size]
    for mi, mesh in enumerate(meshes):
        for pi, part in enumerate(c.block(mesh, 16)):
            slot = c.unpack('h', part)[0]
            if slot < 0 or a.material.lower() not in names[slot].lower():
                continue
            vb = vertices[c.unpack('h', mesh + 24)[0]]
            count, fmt, stride = r.unpack('IHH', vb)
            row = dict(mesh=mi, part=pi, material=names[slot], format=fmt)
            if fmt == 1:
                positions = raw(vb + 20, count * stride)
                ib = indices[c.unpack('h', mesh + 40)[0]]
                data = raw(ib + 16, r.unpack('I', ib + 4)[0])
                start, length = c.unpack('HH', part + 4)
                ids = struct.unpack_from('<' + str(length) + 'H', data, start * 2)
                xyz = [struct.unpack_from('<3f', positions, v * stride) for v in set(ids) if v != 65535]
                row.update(bounds_min=[min(v[j] for v in xyz) for j in range(3)],
                           bounds_max=[max(v[j] for v in xyz) for j in range(3)], indices=length)
            else:
                row['status'] = 'Requires instance/compression transform; not a world-space position'
                row['instances'] = []
                for index in sorted(mesh_instances.get(mi, [])):
                    assert 0 <= index < len(instances)
                    at = instances[index]
                    row['instances'].append(dict(index=index, origin=c.unpack('3f', at + 40),
                        world_sphere_center=c.unpack('3f', at + 64), world_sphere_radius=c.unpack('f', at + 76)[0]))
            rows.append(row)
finally:
    c.close()
a.output.write_text(json.dumps(dict(source=str(a.source), surfaces=rows), indent=2))
print(json.dumps(rows, indent=2))
