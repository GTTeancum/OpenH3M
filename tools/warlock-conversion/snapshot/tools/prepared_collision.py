"""Load and validate a polygon-preserving collision/visibility rebuild."""
import hashlib
import json
import struct
from pathlib import Path
from forge_collision_mesh import read_mesh
from rebuild_forge_collision import FORMATS, read_result
from rebuild_whole_collision import ROOT


def prepare(cache, work, scenario):
    work = Path(work).resolve()
    if not work.is_relative_to(ROOT):
        raise ValueError('Prepared collision outside repository')
    proof = json.loads((work/'collision-rebuild.json').read_text())
    visible = json.loads((work/'collision-visible.json').read_text())
    source_hash = hashlib.sha256(cache.data).hexdigest()
    rebuilt = work/'collision.output'
    if (proof['source_sha256'] != source_hash or visible['source_sha256'] != source_hash
            or proof['scenario'] != scenario
            or proof['output_sha256'] != hashlib.sha256(rebuilt.read_bytes()).hexdigest()
            or proof['surface_coverage']['missing'] or proof['surface_coverage']['added']):
        raise ValueError('Prepared collision proof mismatch')
    tag, original = read_mesh(cache, scenario)
    baseline = read_result(rebuilt)
    path = work/'collision-visible.output'
    arrays = read_result(path)
    clusters = (work/'collision-visible.clusters').read_bytes()
    if arrays[3:] != baseline[3:] or arrays[1][:len(baseline[1])] != baseline[1]:
        raise ValueError('Visibility overlay changed collision geometry/references')
    if list(map(len, arrays)) != visible['counts']:
        raise ValueError('Visibility counts differ from report')
    allowed = set(cache.data[r] for r in cache.block(tag['offset']+0x34, 1))
    if (len(clusters) != len(arrays[2]) or not set(clusters).issubset(allowed)
            or 255 in clusters or len(arrays[1]) > 32768
            or len(arrays[2]) > 65535 or len(arrays[4]) >= 32767):
        raise ValueError('Native collision/cluster limits exceeded')
    state, leaves, pending = {}, set(), [(0, False)]
    while pending:
        node, leaving = pending.pop()
        if node == 0xffffff:
            continue
        if node & 0x800000:
            index = node & 0x7fffff
            if index >= len(arrays[2]): raise ValueError('Invalid 3D leaf')
            leaves.add(index)
            continue
        if node >= len(arrays[0]): raise ValueError('Invalid 3D node')
        if leaving:
            state[node] = 2
            continue
        if state.get(node) == 2: continue
        if state.get(node) == 1: raise ValueError('3D cycle')
        packed = arrays[0][node][0]
        if (packed & 65535) >= len(arrays[1]): raise ValueError('Invalid 3D plane')
        state[node] = 1
        pending.extend(((node, True), ((packed>>16)&0xffffff, False),
                        ((packed>>40)&0xffffff, False)))
    if len(state) != len(arrays[0]) or len(leaves) != len(arrays[2]):
        raise ValueError('Unreachable prepared nodes/leaves')
    for _, _, count, start in arrays[2]:
        if start+count > len(arrays[3]): raise ValueError('Invalid leaf reference range')
    states = {}
    for plane, root in arrays[3]:
        if (plane & 32767) >= len(arrays[1]): raise ValueError('Invalid 2D reference plane')
        pending = [(root, False)]
        while pending:
            node, leaving = pending.pop()
            if node == 65535: continue
            if node & 32768:
                if (node & 32767) >= len(arrays[5]): raise ValueError('Invalid surface reference')
                continue
            if node >= len(arrays[4]): raise ValueError('Invalid 2D node')
            if leaving:
                states[node] = 2
                continue
            if states.get(node) == 2: continue
            if states.get(node) == 1: raise ValueError('2D cycle')
            states[node] = 1
            pending.extend(((node, True), (arrays[4][node][3], False), (arrays[4][node][4], False)))
    plane_ids = {struct.pack('<4f', *p): n for n,p in enumerate(arrays[1])}
    portals = {}
    for row in cache.block(tag['offset']+0x7c, 40):
        old = cache.unpack('i', row+4)[0]
        portals[old] = plane_ids[struct.pack('<4f', *original[1][old])]
    maps = dict(leaves={}, leaf_clusters=clusters, planes=portals,
                edges={n:n for n in range(len(original[6]))},
                surfaces={n:n for n in range(len(original[5]))}, preserve_surface_indices=True)
    payload = [b''.join(struct.pack('>'+fmt, *r) for r in rows)
               for fmt,rows in zip(FORMATS, arrays)]
    report = dict(visible, output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  clusters_sha256=hashlib.sha256(clusters).hexdigest(),
                  validation='indices, graph acyclicity, geometry/reference retention and portal remap')
    return payload, maps, report
