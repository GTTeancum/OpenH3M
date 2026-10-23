"""Reject cyclic or out-of-range packed object collision trees."""
import argparse
import json
from cache_reader import Cache


def verify(cache):
    trees = nodes_checked = 0
    bsp_leaves_checked = 0
    for index, tag in cache.tags.items():
        if tag['group'] == 'sbsp' and not cache.mcc:
            clusters = cache.u(tag['offset'] + 0xb4)
            for row in cache.block(tag['offset'] + 0x30, 1):
                cluster = cache.data[row]
                if cluster >= clusters:
                    raise ValueError(f'sbsp tag {index:#x}: leaf cluster {cluster} exceeds {clusters} clusters; solid regions must use solid child sentinels')
                bsp_leaves_checked += 1
        if tag['group'] != 'coll':
            continue
        for region in cache.block(tag['offset'] + 0x20, 16):
            for permutation in cache.block(region + 4, 40):
                for bsp in cache.block(permutation + 4, 100):
                    nodes = [cache.unpack('Q', row)[0]
                             for row in cache.block(bsp + 4, 8)]
                    planes, leaves = cache.u(bsp + 16), cache.u(bsp + 28)
                    state = {}
                    label = f'coll tag {index:#x}, BSP {bsp:#x}'
                    # Include disconnected nodes, since alternate roots can
                    # also be queried by collision code.
                    for root in range(len(nodes)):
                        stack = [(root, False)]
                        while stack:
                            node, leaving = stack.pop()
                            if node & 0x800000:
                                if node != 0xffffff and (node & 0x7fffff) >= leaves:
                                    raise ValueError(f'{label}: invalid leaf {node:#x}')
                                continue
                            if node >= len(nodes):
                                raise ValueError(f'{label}: invalid child {node:#x}')
                            if leaving:
                                state[node] = 2
                                continue
                            if state.get(node) == 2:
                                continue
                            if state.get(node) == 1:
                                raise ValueError(f'{label}: cycle at node {node}')
                            value = nodes[node]
                            if (value & 0xffff) >= planes:
                                raise ValueError(f'{label}: invalid plane at node {node}')
                            state[node] = 1
                            stack.extend(((node, True),
                                          ((value >> 16) & 0xffffff, False),
                                          ((value >> 40) & 0xffffff, False)))
                    trees += 1
                    nodes_checked += len(nodes)
    return {'collision_trees': trees, 'packed_nodes': nodes_checked,
            'bsp_leaves_checked': bsp_leaves_checked}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', required=True)
    parser.add_argument('--mcc', action='store_true')
    args = parser.parse_args()
    cache = Cache(args.map, args.mcc)
    try:
        print(json.dumps(verify(cache)))
    finally:
        cache.close()
