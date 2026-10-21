"""Keep source cluster classification when removing outside collision faces."""


def preserve_clusters(nodes, active_nodes, active_leaves, clusters):
    if len(clusters) != len(active_leaves):
        raise ValueError('Leaf/cluster table length mismatch')
    canonical, rewritten, children = {}, {}, {}

    def terminal(child):
        if child == -1:
            return child
        if child >= 0:
            return rewritten[child]
        index = child & 0x7fffffff
        if active_leaves[index]:
            return child
        return canonical.setdefault(clusters[index], child)

    pending = [(0, False)]
    while pending:
        index, leaving = pending.pop()
        if index in rewritten:
            continue
        if not leaving:
            pending.append((index, True))
            pending.extend((ch, False) for ch in nodes[index][1:]
                           if ch >= 0 and ch not in rewritten)
            continue
        back, front = (terminal(ch) for ch in nodes[index][1:])
        # Only subtrees containing NO retained collision may collapse. Opening
        # their discarded solid regions removes outside collision as intended;
        # every original nonsolid point keeps its original render cluster.
        if (not active_nodes[index] and back < 0 and front < 0
                and (back == front or back == -1 or front == -1)):
            rewritten[index] = front if back == -1 else back
        else:
            rewritten[index] = index
            children[index] = (back, front)
    reachable, pending = set(), [rewritten[0]]
    while pending:
        index = pending.pop()
        if index < 0 or index in reachable:
            continue
        reachable.add(index)
        pending.extend(children[index])
    aliases = {index: canonical[cluster] & 0x7fffffff
               for index, cluster in enumerate(clusters) if not active_leaves[index]}
    leaves = sorted({i for i, active in enumerate(active_leaves) if active} | set(aliases.values()))
    return sorted(reachable), leaves, children, aliases
