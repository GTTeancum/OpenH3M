"""Correct only audited dangling Dune nav links and absent control padding."""
import hashlib
import struct
from source_schema import load_schema
from resource_reader import Resource

SCENARIO = r'levels\multi\dune\dune'
ROWS = {
    ('Controls', 0): (120, 'd85a2b48d785acc666db3471a0313df91f2c6f12b049295bd8ee5c59aad31ef3'),
    ('Machines', 4): (136, '05d4058b25e2810878c569fe77b1a4a6d90e354da0817c5c113bd9fe9d71049d'),
    ('Machines', 5): (136, 'a4c84aaadd3c15633df5556b6785a3a0e1a0cf6a235221bcb3c3e4155d3eb255'),
}

def validate_empty_graph(counts):
    if not counts or any(counts):
        raise ValueError('Dune pathfinding graph is present; dangling-link correction forbidden')

def validate_row(key, data):
    size, digest = ROWS[key]
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Dune placement changed; re-audit required')

def corrections(importer, schema):
    s = importer.source
    scenarios = [(s.name(k), t['offset']) for k,t in s.tags.items() if t['group']=='scnr']
    if len(scenarios)!=1 or scenarios[0][0]!=SCENARIO:
        return {}, []
    root = scenarios[0][1]
    bsps = [(s.name(k),t['offset']) for k,t in s.tags.items() if t['group']=='sbsp']
    if len(bsps)!=1 or bsps[0][0]!=SCENARIO:
        raise ValueError('Dune BSP graph changed')
    name, bsp = bsps[0]
    graph_counts = [s.u(root+offset) for offset in (0x3b4,0x3b8,0x3bc)]
    graph_counts += [s.u(bsp+offset) for offset in (0x100,0x10c)]
    resource = Resource(s,s.u(bsp+0x394))
    if len(resource.data)!=48 or resource.root!=0:
        raise ValueError('Dune BSP pathfinding resource layout changed')
    graph_counts.append(resource.unpack('I',36)[0])
    native = importer.resolved.get(('sbsp',name))
    if native is None:
        raise ValueError('Dune dangling-link audit requires converted BSP first')
    address = struct.unpack_from('>I',importer.registry.tags,(native[1]&65535)*8+4)[0]
    # Retail pathfinding root and edge blocks. No source nav graph is copied.
    graph_counts += [struct.unpack('>I',importer.builder.read(address+off,4))[0] for off in (0xf0,0xfc)]
    validate_empty_graph(graph_counts)
    result, report = {}, []
    for (block,index), (size,_) in ROWS.items():
        f = next(f for f in schema if f.get('name')==block)
        if int(f.get('elementSize'),0)!=size:
            raise ValueError('Dune placement layout changed')
        rows = s.block(root+int(f.get('offset'),0),size)
        row = rows[index]
        validate_row((block,index),bytes(s.data[row:row+size]))
        if block=='Controls':
            result[row]={'defaults':{('Custom Object Name Index',0):0,('Unknown',3):0}}
            report.append(dict(block=block,index=index,correction='Native-only Custom Object Name Index and padding=0, matching all15 native controls; placement/name retained'))
        else:
            ref = next(f for f in f if f.get('name')=='Pathfinding References')
            refs = s.block(row+int(ref.get('offset'),0),4)
            expected=(0,index-4)
            if len(refs)!=1 or s.unpack('hh',refs[0])!=expected:
                raise ValueError('Dune dangling navigation reference changed')
            result[row]={'zero_nested':{'Pathfinding References'}}
            report.append(dict(block=block,index=index,removed_invalid_link=list(expected),
                zero_graph_counts=graph_counts,correction='Only dangling pathfinding link cleared; machine, name, geometry, collision and animations retained'))
    importer.dune_empty_pathfinding_counts = tuple(graph_counts)
    return result, report
