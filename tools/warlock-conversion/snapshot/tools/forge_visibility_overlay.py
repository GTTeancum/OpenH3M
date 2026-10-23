"""Exact convex-cell clipping for overlaying authored visibility on a rebuilt BSP."""
import numpy as np
from scipy.spatial import ConvexHull, QhullError


def hull(points):
    points=np.unique(np.asarray(points,dtype=np.float64),axis=0)
    if len(points)<4:return None
    try:h=ConvexHull(points)
    except QhullError:return None
    indices=h.vertices;remap={old:new for new,old in enumerate(indices)}
    edges=set()
    for tri in h.simplices:
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            edges.add(tuple(sorted((remap[a],remap[b]))))
    return points[indices],np.asarray(sorted(edges),dtype=np.int32)


def split(cell,plane):
    vertices,edges=cell;plane=np.asarray(plane);dist=vertices@plane[:3]-plane[3]
    # Ignore zero-volume intersections; float64 arithmetic keeps the split much
    # tighter than the engine's float32 position resolution at these coordinates.
    if dist.min()>=-1e-9:return None,cell
    if dist.max()<=1e-9:return cell,None
    cross=edges[(dist[edges[:,0]]<0)!=(dist[edges[:,1]]<0)]
    a,b=cross[:,0],cross[:,1];t=dist[a]/(dist[a]-dist[b]);points=vertices[a]+(vertices[b]-vertices[a])*t[:,None]
    back=hull(np.concatenate((vertices[dist<=0],points)))
    front=hull(np.concatenate((vertices[dist>=0],points)))
    return back,front


def overlay(nodes,planes,leaves,cluster_nodes,cluster_planes,cluster_children,source_clusters,bounds):
    """Intersect each rebuilt empty cell with the source's cluster-only tree.

    Existing collision surfaces, leaf reference lists, and solid terminals stay
    untouched. New leaves share the original reference ranges, adding only the
    render-cluster distinction. No approximation of the retained polygons.
    """
    from itertools import product
    box=hull(list(product(*zip(*bounds))))
    plane_ids={tuple(v):i for i,v in enumerate(planes)}
    output_nodes=[list(v) for v in nodes];output_leaves=[];clusters=[]
    visits=0;empty_cells=0
    def leaf(old,cluster):
        n=len(output_leaves);output_leaves.append(leaves[old]);clusters.append(cluster);return 0x800000|n
    def visibility(old,n,cell):
        nonlocal visits
        while n>=0:
            visits+=1
            p=cluster_planes[cluster_nodes[n][0]];back,front=split(cell,p);children=cluster_children[n]
            if back is None:n=children[1];cell=front;continue
            if front is None:n=children[0];cell=back;continue
            left=visibility(old,children[0],back);right=visibility(old,children[1],front)
            # Collapse identical references/cluster, even if produced through
            # different authored cuts. Dead temporary leaves are compacted later.
            if left == right:return left
            if left != 0xffffff and right != 0xffffff and left&right&0x800000 and clusters[left&0x7fffff]==clusters[right&0x7fffff]:return left
            pi=plane_ids.get(tuple(p))
            if pi is None:pi=len(planes);plane_ids[tuple(p)]=pi;planes.append(tuple(p))
            index=len(output_nodes);output_nodes.append([pi,left,right]);return index
        # Original solid cells have no render cluster. Never turn them into a
        # nonsolid leaf carrying 255: retail visibility/seam traversal uses the
        # leaf's byte as an actual cluster index. All 26 stock BSPs have only
        # valid cluster bytes; solidity is represented by this child sentinel.
        if n == -1:return 0xffffff
        cluster = source_clusters[n&0x7fffffff]
        if cluster == 255:raise ValueError('Authored nonsolid leaf has no render cluster')
        return leaf(old,cluster)
    def collision(n,cell):
        nonlocal empty_cells
        if n==0xffffff:return n
        if cell is None:
            empty_cells+=1
            # This branch has no volume inside the full authored world bounds.
            # It cannot be occupied in the bounded map; retain a nonsolid marker.
            return 0xffffff
        if n&0x800000:return visibility(n&0x7fffff,0,cell)
        p,a,b=nodes[n];back,front=split(cell,planes[p]);output_nodes[n][1]=collision(a,back);output_nodes[n][2]=collision(b,front);return n
    root=collision(0,box)
    # Compact reachable nodes/leaves after equal-cluster collapse.
    ns=set();ls=set();pending=[root]
    while pending:
        n=pending.pop()
        if n==0xffffff:continue
        if n&0x800000:ls.add(n&0x7fffff);continue
        if n in ns:continue
        ns.add(n);pending.extend(output_nodes[n][1:])
    ns=sorted(ns);ls=sorted(ls);nm={old:new for new,old in enumerate(ns)};lm={old:new for new,old in enumerate(ls)}
    def remap(n):return n if n==0xffffff else (0x800000|lm[n&0x7fffff] if n&0x800000 else nm[n])
    assert nm[root]==0
    return [[output_nodes[n][0],remap(output_nodes[n][1]),remap(output_nodes[n][2])] for n in ns],planes,[output_leaves[n] for n in ls],bytes(clusters[n] for n in ls),{'visibility_cell_visits':visits,'out_of_bounds_cells':empty_cells,'nodes':len(ns),'leaves':len(ls),'planes':len(planes)}
