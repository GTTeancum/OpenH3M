"""Offline Forge Gulch collision-table conversion, not a deployable map.

Produces retail-endian tables in memory and explicit old-to-new maps for the
metadata pass. Caller must also rebuild leaf clusters, seams, surface mappings,
MOPPs and containment before using these tables in a game cache.
"""
import argparse
import json
import struct
from pathlib import Path
import numpy as np
from forge_collision_mesh import read_mesh, surface_loops, positions
from forge_gulch_boundary import classify_bounds, BOUNDARY


def prepare(cache, side='gulch'):
    """Prepare the Gulch partition while retaining authored BSP seam topology."""
    tag, arrays = read_mesh(cache)
    xyz = positions(arrays)
    loops = surface_loops(arrays)
    mins = np.array([xyz[loop].min(axis=0) for loop in loops])
    maxs = np.array([xyz[loop].max(axis=0) for loop in loops])
    if side not in ('gulch', 'island'):
        raise ValueError('Unknown Forge partition')
    keep = classify_bounds(mins, maxs)[side == 'island']
    selected_count = int(keep.sum())
    seam_edges = []
    for seam in cache.block(tag['offset'] + 0x10, 40):
        for row in cache.block(seam + 16, 4):
            edge = cache.unpack('i', row)[0]
            if not 0 <= edge < len(arrays[6]):
                raise ValueError('Invalid authored seam edge')
            seam_edges.append(edge)
            for face in arrays[6][edge][4:]:
                if face >= 0:
                    keep[face] = True
    portals = [cache.unpack('i', row + 4)[0] for row in cache.block(tag['offset'] + 0x7c, 40)]
    leaf_clusters = [cache.data[row] for row in cache.block(tag['offset'] + 0x34, 1)]
    payloads, maps, report = partition(arrays, keep, portals, leaf_clusters)
    if any(edge not in maps['edges'] for edge in seam_edges):
        raise ValueError('Partition lost a shared BSP seam')
    report.update(seam_support_surfaces=int(keep.sum()) - selected_count,
                  partition_side=side,
                  authored_seam_edges_preserved=len(seam_edges))
    # The rebuild also inserts the solid, two-sided divider. It is required
    # even when the retained tree already fits the signed plane-index limit.
    from rebuild_forge_collision import rebuild
    payloads, maps, report = rebuild(cache, tag, arrays, payloads, maps, report, portals)
    return tag, payloads, maps, report


def active_tree(children, terminals):
    states, active = [0] * len(children), [False] * len(children)

    def value(child):
        if child == -1:
            return False
        table, index = (terminals, child & 0x7fffffff) if child < 0 else (active, child)
        if not 0 <= index < len(table):
            raise ValueError('Collision child outside table')
        return bool(table[index])

    for start in range(len(children)):
        stack = [(start, False)]
        while stack:
            index, leaving = stack.pop()
            if not 0 <= index < len(children):
                raise ValueError('Collision node outside table')
            if leaving:
                active[index] = any(value(child) for child in children[index])
                states[index] = 2
            elif states[index] != 2:
                if states[index] == 1:
                    raise ValueError('Cyclic collision tree')
                states[index] = 1
                stack.append((index, True))
                stack.extend((child, False) for child in children[index] if child >= 0)
    return active, value


def partition(arrays, keep, required_planes=(), leaf_clusters=None):
    nodes, planes, leaves, refs, nodes2, surfaces, edges, vertices = arrays
    source_loops = surface_loops(arrays)
    if len(keep) != len(surfaces) or not any(keep):
        raise ValueError('Invalid/empty surface selection')
    a2, value2 = active_tree([row[3:] for row in nodes2], keep)
    ar = [value2(row[1]) for row in refs]
    al = []
    for _, _, count, first in leaves:
        if count and first + count > len(refs):
            raise ValueError('Leaf reference range exceeds table')
        al.append(any(ar[first:first + count]))
    a3, _ = active_tree([row[1:] for row in nodes], al)
    if not a3 or not a3[0]:
        raise ValueError('Selection has no original root')
    ids = lambda flags: [n for n, flag in enumerate(flags) if flag]
    selected = {'nodes': ids(a3), 'leaves': ids(al), 'nodes2': ids(a2), 'surfaces': ids(keep)}
    visibility_children, leaf_aliases = None, {}
    if leaf_clusters is not None:
        from forge_visibility_partition import preserve_clusters
        selected['nodes'], selected['leaves'], visibility_children, leaf_aliases = preserve_clusters(
            nodes, a3, al, leaf_clusters)
    selected['edges'] = [n for n, e in enumerate(edges)
                         if (e[4] >= 0 and keep[e[4]]) or (e[5] >= 0 and keep[e[5]])]
    selected['vertices'] = sorted({v for n in selected['edges'] for v in edges[n][:2]})
    maps = {name: {old: new for new, old in enumerate(order)} for name, order in selected.items()}
    # Signed 2D plane references get the lower half of the plane address space.
    ref_planes = sorted({refs[n][0] & 0x7fffffff for n in ids(ar)} |
                        {surfaces[n][0] & 0x7fffffff for n in selected['surfaces']})
    other_planes = sorted((set(required_planes) | {nodes[n][0] for n in selected['nodes']} |
                           {surfaces[n][0] & 0x7fffffff for n in selected['surfaces']}) - set(ref_planes))
    plane_map, unique, plane_rows = {}, {}, []
    for old in ref_planes + other_planes:
        if not 0 <= old < len(planes):
            raise ValueError('Plane outside table')
        key = struct.pack('<4f', *planes[old])
        if key not in unique:
            unique[key] = len(plane_rows)
            plane_rows.append(planes[old])
        plane_map[old] = unique[key]
    maps['planes'] = plane_map
    if (len(plane_rows) > 65536 or max(plane_map[n] for n in ref_planes) >= 32768
            or len(selected['surfaces']) >= 32767 or len(selected['nodes2']) >= 32767
            or len(selected['edges']) >= 65535 or len(selected['vertices']) >= 65535
            or len(selected['leaves']) >= 0x3fffff or len(selected['nodes']) >= 0x3fffff):
        raise ValueError('Partition exceeds retail indices')

    def child(old, node_map, terminal_map, bits):
        empty = (1 << bits) - 1
        if old == -1:
            return empty
        if old < 0:
            index = terminal_map.get(old & 0x7fffffff)
            return empty if index is None else index | (1 << (bits - 1))
        return node_map.get(old, empty)

    target = [[] for _ in range(8)]
    for old in selected['nodes']:
        plane, back, front = nodes[old]
        if visibility_children is not None:
            back, front = visibility_children[old]
        back = child(back, maps['nodes'], maps['leaves'], 24)
        front = child(front, maps['nodes'], maps['leaves'], 24)
        target[0].append((plane_map[plane] | (back << 16) | (front << 40),))
    target[1] = plane_rows
    # Build per-leaf ranges, not one global filter: ranges may share references.
    for old in selected['leaves']:
        flags, flags2, count, first = leaves[old]
        new_first = len(target[3])
        for index in range(first, first + count):
            if ar[index]:
                plane, node = refs[index]
                target[3].append((plane_map[plane & 0x7fffffff] | (0x8000 if plane < 0 else 0),
                                  child(node, maps['nodes2'], maps['surfaces'], 16)))
        target[2].append((flags, flags2, len(target[3]) - new_first, new_first))
    for old in selected['nodes2']:
        row = nodes2[old]
        target[4].append((*row[:3], *(child(ch, maps['nodes2'], maps['surfaces'], 16) for ch in row[3:])))
    for old in selected['surfaces']:
        plane, edge, material, breakset, breakindex, flags, best = surfaces[old]
        # Large MCC surfaces carry orientation in plane bit 31; retail H3
        # uses plane bit 15 (verified in original Sandbox/Last Resort/
        # Valhalla/Guardian). Flag 7 belongs to a later engine format.
        if flags & 128:
            raise ValueError('Ambiguous source surface orientation')
        target[5].append((plane_map[plane & 0x7fffffff] | (0x8000 if plane < 0 else 0),
                          maps['edges'][edge], material, breakset, breakindex, flags, best & 255))
    incident = {}
    for old in selected['edges']:
        start, end, forward, reverse, left, right = edges[old]
        for v in (start, end):
            incident.setdefault(v, maps['edges'][old])
        # A removed neighbouring face has no usable traversal direction.
        target[6].append((maps['vertices'][start], maps['vertices'][end],
                          maps['edges'][forward] if left in maps['surfaces'] else 65535,
                          maps['edges'][reverse] if right in maps['surfaces'] else 65535,
                          maps['surfaces'].get(left, 65535), maps['surfaces'].get(right, 65535)))
    for old in selected['vertices']:
        x, y, z, edge, sink = vertices[old]
        target[7].append((x, y, z, maps['edges'].get(edge, incident[old]), sink))
    formats = ('Q', '4f', 'BBHI', '2H', '3f2H', '2H3h2B', '6H', '3fHh')
    payloads = [b''.join(struct.pack('>' + fmt, *row) for row in rows)
                for fmt, rows in zip(formats, target)]
    # Read the actual serialized tables back and verify every retained polygon
    # still has the exact authored vertex cycle, material and orientation.
    decoded = [list(struct.iter_unpack('>' + fmt, payload)) for fmt, payload in zip(formats, payloads)]
    # Compare spatial queries through the independently decoded packed tree.
    # This detects reversed child fields, wrong endian packing and leaf remaps.
    xyz = positions(arrays)
    rng = np.random.default_rng(20261021)
    probes = rng.uniform(xyz.min(axis=0), xyz.max(axis=0), (2048, 3))
    opened_solid_queries = 0
    empty_leaf_indices = {maps['leaves'][old] for old in leaf_aliases.values()}
    for point in probes:
        original = 0
        while original >= 0:
            plane, back, front = nodes[original]
            normal = planes[plane]
            original = front if sum(point[k] * normal[k] for k in range(3)) >= normal[3] else back
        old_leaf = original & 0x7fffffff
        expected = maps['leaves'].get(leaf_aliases.get(old_leaf, old_leaf)) if original != -1 else None
        actual = 0
        while not actual & 0x800000:
            packed = decoded[0][actual][0]
            normal = decoded[1][packed & 65535]
            front = sum(point[k] * normal[k] for k in range(3)) >= normal[3]
            actual = (packed >> (40 if front else 16)) & 0xffffff
        actual = None if actual == 0xffffff else actual & 0x7fffff
        if original == -1 and actual in empty_leaf_indices:
            opened_solid_queries += 1
        elif actual != expected:
            raise ValueError('Packed tree changed spatial leaf classification')
    for old, new in maps['surfaces'].items():
        s = decoded[5][new]
        first = edge = s[1]
        loop, seen = [], set()
        while edge not in seen:
            seen.add(edge)
            if not 0 <= edge < len(decoded[6]):
                raise ValueError('Serialized surface has dangling edge')
            e = decoded[6][edge]
            if e[4] == new:
                loop.append(e[0]); edge = e[2]
            elif e[5] == new:
                loop.append(e[1]); edge = e[3]
            else:
                raise ValueError('Serialized edge ownership mismatch')
        expected = [maps['vertices'][v] for v in source_loops[old]]
        if edge != first or loop != expected:
            raise ValueError('Serialized polygon changed')
        source_surface = surfaces[old]
        if (s[2:5] != source_surface[2:5] or bool(s[0] & 0x8000) != (source_surface[0] < 0)
                or decoded[1][s[0] & 0x7fff] != planes[source_surface[0] & 0x7fffffff]):
            raise ValueError('Serialized surface material or plane changed')
    return payloads, maps, {
        'counts': dict(zip(('nodes3d', 'planes', 'leaves', 'references2d', 'nodes2d',
                           'surfaces', 'edges', 'vertices'), map(len, decoded))),
        'raw_bytes': sum(map(len, payloads)),
        'surface_loops_roundtrip_verified': len(maps['surfaces']),
        'spatial_queries_roundtrip_verified': len(probes),
        'empty_visibility_leaves': len(empty_leaf_indices),
        'original_leaf_cluster_assignments_preserved': len(leaves) if leaf_clusters is not None else None,
        'discarded_solid_probe_regions_opened': opened_solid_queries,
        'negative_surface_planes_translated': sum(surfaces[n][0] < 0 for n in maps['surfaces']),
        'status': 'Offline table prototype; NOT map-ready',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    report = a.report.resolve()
    if not report.is_relative_to(Path(__file__).resolve().parents[4]):
        raise ValueError('Report must remain in repository')
    from cache_reader import Cache
    c = Cache(a.source, True)
    try:
        tag, _, maps, result = prepare(c)
        portals = [c.unpack('i', row + 4)[0] for row in c.block(tag['offset'] + 0x7c, 40)]
        if any(plane < 0 for plane in portals):
            raise ValueError('Unexpected portal plane sentinel')
        result['portal_planes_retained'] = len(set(portals))
        # Record coupled metadata so integration cannot mistake these tables
        # for a stand-alone, deployable collision-resource replacement.
        from resource_reader import Resource
        sidecar = Resource(c, c.u(tag['offset'] + 0x394))
        result['metadata_dependencies'] = {
            'source_leaf_cluster_bytes': c.u(tag['offset'] + 0x34),
            'target_leaf_cluster_bytes': len(maps.get('leaf_clusters', maps['leaves'])),
            'source_surface_mapping_rows': sidecar.unpack('I', 0)[0],
            'source_triangle_mapping_rows': sidecar.unpack('I', 12)[0],
            'source_edge_seam_rows': sidecar.unpack('I', 24)[0],
            'instances_retained_for_visuals': c.u(tag['offset'] + 0x1c0),
            'seam_edges_removed_by_cut': [sum(c.unpack('i', e)[0] not in maps['edges']
                                               for e in c.block(seam + 16, 4))
                                          for seam in c.block(tag['offset'] + 0x10, 40)],
        }
        result['boundary_xy'] = BOUNDARY
        result['remaining'] = ['Remap metadata leaf clusters, surface/triangle mappings and seams',
                               'Audit/rebuild physics MOPP keys and instance collision',
                               'Add player, vehicle and Forge-camera containment',
                               'Build map, validate memory and inspect native gameplay']
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    finally:
        c.close()


if __name__ == '__main__':
    main()
