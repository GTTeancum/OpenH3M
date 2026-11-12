"""Rebuild an MCC large collision tree while retaining every authored polygon."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from cache_reader import Cache
from forge_collision_mesh import read_mesh
from rebuild_forge_collision import compiler, read_result, write_result, FORMATS

ROOT = Path(__file__).resolve().parents[4]


def prepare(cache, work):
    from forge_visibility_partition import preserve_clusters
    from forge_visibility_overlay import overlay
    work = work.resolve()
    if not work.is_relative_to(ROOT):
        raise ValueError('Output outside repository')
    proof = json.loads((work/'collision-rebuild.json').read_text())
    if proof.get('surface_coverage', {}).get('missing') or 'surface_coverage' not in proof:
        raise ValueError('Collision rebuild has not preserved reachable surface coverage')
    tree = work/'collision.output'
    if (hashlib.sha256(cache.data).hexdigest() != proof['source_sha256'] or
            hashlib.sha256(tree.read_bytes()).hexdigest() != proof['output_sha256']):
        raise ValueError('Collision rebuild source/output hash mismatch')
    tag, original = read_mesh(cache, proof['scenario'])
    arrays = read_result(tree)
    clusters = [cache.data[r] for r in cache.block(tag['offset']+0x34, 1)]
    _, _, children, _ = preserve_clusters(original[0], [False]*len(original[0]),
                                         [False]*len(original[2]), clusters)
    bounds = ([min(p[k] for p in original[7])-100 for k in range(3)],
              [max(p[k] for p in original[7])+100 for k in range(3)])
    nodes = [[v[0]&65535, v[0]>>16&0xffffff, v[0]>>40&0xffffff] for v in arrays[0]]
    before = [list(r) for r in arrays[3:]]
    nodes, arrays[1], arrays[2], leaf_clusters, details = overlay(
        nodes, arrays[1], arrays[2], original[0], original[1], children, clusters, bounds)
    arrays[0] = [(p | (a << 16) | (b << 40),) for p, a, b in nodes]
    if arrays[3:] != before:
        raise ValueError('Visibility overlay changed collision geometry')
    planes = {struct.pack('<4f', *p): n for n, p in enumerate(arrays[1])}
    portals = {}
    for row in cache.block(tag['offset']+0x7c, 40):
        old = cache.unpack('i', row+4)[0]
        plane = original[1][old]
        key = struct.pack('<4f', *plane)
        if key not in planes:
            planes[key] = len(arrays[1])
            arrays[1].append(plane)
        portals[old] = planes[key]
    if len(arrays[1]) > 32768 or len(arrays[2]) > 65535 or len(arrays[4]) >= 32767:
        raise ValueError('Overlaid collision exceeds original native limits')
    if len(leaf_clusters) != len(arrays[2]) or not set(leaf_clusters).issubset(set(clusters)):
        raise ValueError('Invalid leaf cluster assignments')
    write_result(work/'collision-visible.output', arrays)
    (work/'collision-visible.clusters').write_bytes(bytes(leaf_clusters))
    report = dict(counts=list(map(len, arrays)), visibility=details,
                  source_sha256=proof['source_sha256'], polygons_unchanged=proof['polygons_unchanged'],
                  physics='original surface and instance indices retained; integration pending')
    (work/'collision-visible.json').write_text(json.dumps(report, indent=2)+'\n')
    maps = dict(leaves={}, leaf_clusters=bytes(leaf_clusters), planes=portals,
                edges={n:n for n in range(len(original[6]))},
                surfaces={n:n for n in range(len(original[5]))})
    payloads = [b''.join(struct.pack('>'+fmt, *row) for row in rows)
                for fmt, rows in zip(FORMATS, arrays)]
    return payloads, maps, report


def build(source, scenario, work):
    work = work.resolve()
    if not work.is_relative_to(ROOT):
        raise ValueError('Output outside repository')
    work.mkdir(parents=True, exist_ok=True)
    cache = Cache(source, True)
    try:
        _, arrays = read_mesh(cache, scenario)
        planes = sorted({s[0] & 0x7fffffff for s in arrays[5]})
        mapping = {old: new for new, old in enumerate(planes)}
        if len(planes) > 32768 or len(arrays[5]) >= 32767:
            raise ValueError('Authored topology exceeds native limits')
        def narrow(index):
            if index == -1:
                return 65535
            if not 0 <= index < 65535:
                raise ValueError('Topology index outside native range')
            return index
        surface = [(mapping[s[0] & 0x7fffffff] | (32768 if s[0] < 0 else 0),
                    narrow(s[1]), *s[2:6], s[6] & 255) for s in arrays[5]]
        edges = [tuple(narrow(v) for v in row) for row in arrays[6]]
        vertices = [(*row[:3], narrow(row[3]), row[4]) for row in arrays[7]]
        input_path = work/'collision.input'
        with input_path.open('wb') as stream:
            stream.write(b'FGC1')
            for fmt, rows in zip(('4f', '2H3h2B', '6H', '3fHh'),
                                 ([arrays[1][p] for p in planes], surface, edges, vertices)):
                stream.write(struct.pack('<I', len(rows)))
                for row in rows:
                    stream.write(struct.pack('<'+fmt, *row))
        # Reuse the existing verified builder/toolchain; no per-map tool copies.
        dotnet, binary, tool, env = compiler(ROOT, ROOT/'work/forge-world', memoize_2d=True)
        output = work/'collision.output'
        with (work/'collision-builder.log').open('w') as log:
            subprocess.run([dotnet, str(binary), str(tool), str(input_path), str(output)],
                           cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=180, check=True)
        result = read_result(output)
        if len(result[4]) >= 32767:
            raise ValueError('Rebuilt 2D tree exceeds signed native index limit')
        if result[6:] != [edges, vertices] or len(result[5]) != len(surface):
            raise ValueError('Builder changed topology')
        for old, new in zip(surface, result[5]):
            if (old[1:] != new[1:] or bool(old[0] & 32768) != bool(new[0] & 32768)
                    or arrays[1][planes[old[0] & 32767]] != result[1][new[0] & 32767]):
                raise ValueError('Builder changed an authored surface')
        def reachable(tables, large):
            pending, seen, found = [r[1] for r in tables[3]], set(), set()
            while pending:
                node = pending.pop()
                if node in seen:
                    continue
                seen.add(node)
                if node == (-1 if large else 65535):
                    continue
                if (node < 0 if large else node & 32768):
                    found.add(node & (0x7fffffff if large else 32767))
                else:
                    pending.extend(tables[4][node][3:])
            return found
        old_reached, new_reached = reachable(arrays, True), reachable(result, False)
        coverage = dict(source_reachable=len(old_reached), rebuilt_reachable=len(new_reached),
                        missing=sorted(old_reached-new_reached), added=sorted(new_reached-old_reached))
        report = dict(source=str(source), scenario=scenario,
                      source_sha256=hashlib.sha256(cache.data).hexdigest(),
                      source_counts=list(map(len, arrays)), counts=list(map(len, result)),
                      polygons_unchanged=len(surface),
                      surface_coverage=coverage,
                      output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                      status='visibility and physics integration pending')
        (work/'collision-rebuild.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2), flush=True)
        if coverage['missing']:
            raise ValueError('Builder omitted authored collision surfaces; candidate rejected')
    finally:
        cache.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--scenario', required=True)
    p.add_argument('--work', type=Path, required=True)
    build(**vars(p.parse_args()))
