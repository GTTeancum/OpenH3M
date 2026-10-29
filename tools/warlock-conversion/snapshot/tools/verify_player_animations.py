"""Validate player mode animation targets, inheritance and native node maps."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from cache_reader import Cache
from string_ids import StringTable


def verify(c):
    schema = ET.parse(Path(__file__).parents[1] / 'reference/plugins/jmad.xml').getroot()
    mode_schema = next(f for f in schema if f.get('name') == 'Modes')
    strings = StringTable(c)
    results = []
    for name in ('masterchief', 'elite'):
        full = 'objects\\characters\\' + name + '\\' + name
        # The original graph is overwritten in place so existing model refs work.
        tag = next(t for n,t in c.tags.items() if t['group']=='jmad' and c.name(n)==full)
        root = tag['offset']
        inherited = c.block(root+0x80,48)
        graphs = []
        local_nodes = [c.u(r) for r in c.block(root+0x14,32)]
        for row in inherited:
            handle = c.u(row+12); t = c.tags[handle & 65535]
            assert t['salt']==handle>>16 and t['group']=='jmad'
            graphs.append(t['offset'])
            nodes = c.block(t['offset']+0x14,32)
            mapping = c.block(row+16,2)
            # Retail Elite includes an inherited graph without a node map.
            assert not mapping or len(nodes)==len(mapping)
            for a,b in zip(nodes,mapping):
                index = c.unpack('h',b)[0]
                assert index==-1 or (0<=index<len(local_nodes) and local_nodes[index]==c.u(a))
        refs = 0
        def walk(at,node):
            nonlocal refs
            for f in node:
                if 'offset' not in f.attrib: continue
                p = at+int(f.get('offset'),0)
                if f.tag.lower()=='tagblock':
                    for r in c.block(p,int(f.get('elementSize'),0)): walk(r,f)
                elif f.get('name')=='Graph Index':
                    graph, animation = c.unpack('hh',p)
                    if animation==-1: continue
                    assert graph==-1 or 0<=graph<len(graphs), (name,graph)
                    owner = root if graph==-1 else graphs[graph]
                    assert 0<=animation<c.u(owner+0x50), (name,graph,animation)
                    refs += 1
        modes = c.block(root+0x5c,40)
        ids = [c.u(r) for r in modes]
        assert ids==sorted(set(ids))
        names = [strings.text(n) for n in ids]
        assert {'shade_d','banshee_d','ghost_d','scorpion_d','warthog_d','hornet_d'} <= set(names)
        for row in modes: walk(row,mode_schema)
        results.append({'player':name,'modes':len(modes),'animation_targets':refs,'inherited_graphs':len(graphs)})
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--map',required=True)
    c=Cache(p.parse_args().map)
    try: print(json.dumps(verify(c)))
    finally: c.close()
