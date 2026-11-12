"""Audit lossless sharing of collision decision subtrees; never edit geometry."""
import math
import struct


def compact(nodes, roots, reverse=False):
    result, interned, mapped, visiting = [], {}, {}, set()
    def visit(index):
        if index < 0:
            return index
        if index in mapped:
            return mapped[index]
        if index in visiting or not 0 <= index < len(nodes):
            raise ValueError('Invalid/cyclic 2D collision tree')
        visiting.add(index)
        row = nodes[index]
        plane = tuple(0.0 if v == 0 else v for v in row[:3])
        if not all(math.isfinite(v) for v in plane):
            raise ValueError('Nonfinite collision plane')
        left, right = visit(row[3]), visit(row[4])
        key = struct.pack('<3f', *plane), left, right
        if reverse:
            other_plane = tuple(0.0 if v == 0 else -v for v in plane)
            other = struct.pack('<3f', *other_plane), right, left
            if other < key:
                key, plane, left, right = other, other_plane, right, left
        if key not in interned:
            interned[key] = len(result)
            result.append((*plane, left, right))
        mapped[index] = interned[key]
        visiting.remove(index)
        return mapped[index]
    new_roots = [visit(root) for root in roots]
    return result, new_roots, mapped


def classify(nodes, root, point):
    """Strict positive-side convention; expose exact-on-plane differences."""
    while root >= 0:
        x, y, d, left, right = nodes[root]
        root = right if x*point[0]+y*point[1]-d > 0 else left
    return root
