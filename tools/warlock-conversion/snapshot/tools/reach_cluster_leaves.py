"""Subdivide classified empty leaves while retaining every collision reference."""
import struct


def split_cluster_leaves(geometry,expanded,clusters,parent,child,axis,value):
    if axis not in (0,1,2) or not 0<=parent<255 or not 0<=child<255 or parent==child:
        raise ValueError('Invalid leaf cluster split')
    n,p=struct.unpack_from('<II',expanded)
    if len(expanded)!=8+n*8+p*16:raise ValueError('Invalid expanded collision tree')
    if p>=32768:raise ValueError('Split plane exceeds native index width')
    nodes=[v[0] for v in struct.iter_unpack('<Q',expanded[8:8+n*8])]
    planes=expanded[8+n*8:];leaves=bytes(geometry['leaves'][1])
    if len(leaves)!=len(clusters)*8:raise ValueError('Cluster classification differs from collision leaves')
    wanted={i for i,c in enumerate(clusters) if c==parent};seen=set();splits={};new_leaves=bytearray(leaves);new_clusters=bytearray(clusters)
    for i,packed in enumerate(nodes):
        back=(packed>>16)&0xffffff;front=(packed>>40)&0xffffff
        children=[]
        for original in (back,front):
            terminal=original&0x7fffff
            if original!=0xffffff and original&0x800000 and terminal in wanted:
                if terminal not in splits:
                    target=len(new_clusters)
                    if target>=0x7fffff:raise ValueError('Split leaf exceeds native index width')
                    splits[terminal]=(n+len(splits),target)
                    new_leaves.extend(leaves[terminal*8:terminal*8+8]);new_clusters.append(child)
                children.append(splits[terminal][0]);seen.add(terminal)
            else:children.append(original)
        nodes[i]=(packed&65535)|(children[0]<<16)|(children[1]<<40)
    if not seen:raise ValueError('Parent cluster has no referenced leaves')
    for original,(node,target) in splits.items():
        assert node==len(nodes)
        nodes.append(p|((0x800000|original)<<16)|((0x800000|target)<<40))
    plane=[0.,0.,0.,float(value)];plane[axis]=1.
    result=struct.pack('<II',len(nodes),p+1)+b''.join(struct.pack('<Q',v) for v in nodes)+planes+struct.pack('<4f',*plane)
    adapted=dict(geometry);adapted['leaves']=(len(new_clusters),bytes(new_leaves))
    return adapted,result,bytes(new_clusters),dict(added_nodes=len(splits),added_leaves=len(splits),
        plane_index=p,unreferenced_parent_leaves=sorted(wanted-seen),
        new_leaf_to_original={target:old for old,(_,target) in splits.items()})
